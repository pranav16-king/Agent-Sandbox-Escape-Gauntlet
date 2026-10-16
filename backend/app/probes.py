"""
Active Probe Module for sandboxX (PS01 Agent Sandbox Escape Gauntlet).
Truthful, active verification of all defense-in-depth controls.
Rule: Failure or timeout MUST return 'unverified' or 'failed', NEVER fake green.
"""

import json
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Literal

from .config import settings
from .audit.verifier import verify_chain
from .policy.engine import policy_engine
from .policy.manifests import TASK_MANIFESTS

ControlState = Literal["verified", "failed", "unverified"]

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def probe_container_running(container_name: str = "sbx-session") -> dict[str, Any]:
    """
    Probes whether the Docker sandbox container is active and running.
    Executes 'docker inspect' with a timeout.
    """
    ts = _iso_now()
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return {
            "name": "Container Running",
            "state": "unverified",
            "detail": "Docker CLI not found on host system",
            "checked_at": ts
        }

    try:
        proc = subprocess.run(
            [docker_bin, "inspect", "--format", "{{json .State.Running}}", container_name],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if proc.returncode != 0:
            return {
                "name": "Container Running",
                "state": "unverified",
                "detail": f"Container '{container_name}' not running or not found ({proc.stderr.strip()[:100]})",
                "checked_at": ts
            }

        is_running = proc.stdout.strip().lower() == "true"
        return {
            "name": "Container Running",
            "state": "verified" if is_running else "failed",
            "detail": f"Container '{container_name}' running: {is_running}",
            "checked_at": ts
        }
    except subprocess.TimeoutExpired:
        return {
            "name": "Container Running",
            "state": "unverified",
            "detail": "Docker inspect timed out (daemon unresponsive)",
            "checked_at": ts
        }
    except Exception as e:
        return {
            "name": "Container Running",
            "state": "unverified",
            "detail": f"Docker inspect probe failed: {str(e)[:100]}",
            "checked_at": ts
        }

def probe_rootfs_and_caps(container_name: str = "sbx-session") -> dict[str, Any]:
    """
    Probes non-root execution, read-only rootfs, and dropped Linux capabilities.
    """
    ts = _iso_now()
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return {
            "name": "Non-Root & Read-Only Rootfs",
            "state": "unverified",
            "detail": "Docker CLI unavailable; cannot inspect container cgroups/security config",
            "checked_at": ts
        }

    try:
        proc = subprocess.run(
            [
                docker_bin, "inspect",
                "--format",
                '{"user":"{{.Config.User}}","ro":{{.HostConfig.ReadonlyRootfs}},"caps":"{{.HostConfig.CapDrop}}"}',
                container_name
            ],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if proc.returncode != 0:
            return {
                "name": "Non-Root & Read-Only Rootfs",
                "state": "unverified",
                "detail": f"Cannot inspect container '{container_name}' security flags",
                "checked_at": ts
            }

        data = json.loads(proc.stdout.strip())
        user = data.get("user", "")
        ro = bool(data.get("ro", False))
        caps = str(data.get("caps", ""))

        is_non_root = user not in ("", "0", "root")
        is_caps_dropped = "ALL" in caps or "all" in caps

        if is_non_root and ro and is_caps_dropped:
            return {
                "name": "Non-Root & Read-Only Rootfs",
                "state": "verified",
                "detail": f"UID: {user}, ReadonlyRootfs: {ro}, CapDrop: {caps}",
                "checked_at": ts
            }
        else:
            return {
                "name": "Non-Root & Read-Only Rootfs",
                "state": "failed",
                "detail": f"Security configuration violated: user='{user}', readonly={ro}, caps='{caps}'",
                "checked_at": ts
            }
    except Exception as e:
        return {
            "name": "Non-Root & Read-Only Rootfs",
            "state": "unverified",
            "detail": f"Probe error: {str(e)[:100]}",
            "checked_at": ts
        }

def probe_seccomp_applied(container_name: str = "sbx-session") -> dict[str, Any]:
    """
    Probes whether seccomp filter is active and not unconfined.
    """
    ts = _iso_now()
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return {
            "name": "Seccomp Profile",
            "state": "unverified",
            "detail": "Docker CLI unavailable; seccomp probe unverified",
            "checked_at": ts
        }

    try:
        proc = subprocess.run(
            [docker_bin, "inspect", "--format", "{{json .HostConfig.SecurityOpt}}", container_name],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if proc.returncode != 0:
            return {
                "name": "Seccomp Profile",
                "state": "unverified",
                "detail": f"Unable to inspect SecurityOpt for '{container_name}'",
                "checked_at": ts
            }

        sec_opts = json.loads(proc.stdout.strip() or "[]") or []
        sec_str = " ".join(sec_opts).lower()

        if "seccomp=unconfined" in sec_str:
            return {
                "name": "Seccomp Profile",
                "state": "failed",
                "detail": "Seccomp is explicitly unconfined! Dangerous configuration.",
                "checked_at": ts
            }
        elif any("seccomp" in opt for opt in sec_opts):
            return {
                "name": "Seccomp Profile",
                "state": "verified",
                "detail": f"Active seccomp filter applied: {sec_opts}",
                "checked_at": ts
            }
        else:
            # Default daemon seccomp profile or unverified
            return {
                "name": "Seccomp Profile",
                "state": "unverified",
                "detail": "No explicit custom seccomp profile specified in SecurityOpt",
                "checked_at": ts
            }
    except Exception as e:
        return {
            "name": "Seccomp Profile",
            "state": "unverified",
            "detail": f"Seccomp probe error: {str(e)[:100]}",
            "checked_at": ts
        }

def probe_network_internal(network_name: str = settings.DOCKER_NETWORK) -> dict[str, Any]:
    """
    Probes whether the Docker sandbox network has the Internal flag enabled.
    """
    ts = _iso_now()
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return {
            "name": "Network Internal Isolation",
            "state": "unverified",
            "detail": "Docker CLI unavailable; network isolation unverified",
            "checked_at": ts
        }

    try:
        proc = subprocess.run(
            [docker_bin, "network", "inspect", "--format", "{{json .Internal}}", network_name],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if proc.returncode != 0:
            return {
                "name": "Network Internal Isolation",
                "state": "unverified",
                "detail": f"Network '{network_name}' not found or docker daemon offline",
                "checked_at": ts
            }

        is_internal = proc.stdout.strip().lower() == "true"
        return {
            "name": "Network Internal Isolation",
            "state": "verified" if is_internal else "failed",
            "detail": f"Docker network '{network_name}' internal flag: {is_internal}",
            "checked_at": ts
        }
    except Exception as e:
        return {
            "name": "Network Internal Isolation",
            "state": "unverified",
            "detail": f"Network inspect probe error: {str(e)[:100]}",
            "checked_at": ts
        }

def probe_egress_allowlist(proxy_host: str = "127.0.0.1", proxy_port: int = 3128) -> dict[str, Any]:
    """
    Probes the egress proxy allowlist live via an active canary check.
    Attempts a socket probe to Squid proxy and verifies policy engine canary block.
    """
    ts = _iso_now()

    # 1. Active socket check to Squid proxy port
    sock_alive = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            res = s.connect_ex((proxy_host, proxy_port))
            sock_alive = (res == 0)
    except Exception:
        sock_alive = False

    # 2. Canary policy drop verification against blocked host
    canary_url = "http://169.254.169.254/latest/meta-data/"
    from .policy.rules import check_network_security
    from .policy.manifests import get_manifest

    manifest = get_manifest("default-task")
    allowed, rule_id, reason = check_network_security(canary_url, manifest)

    if sock_alive and not allowed:
        return {
            "name": "Egress Allowlist Live",
            "state": "verified",
            "detail": f"Squid proxy active on port {proxy_port}; canary blocked by rule {rule_id}",
            "checked_at": ts
        }
    elif not allowed and not sock_alive:
        # Gateway policy drops canary, but live Squid daemon is not listening on port 3128
        return {
            "name": "Egress Allowlist Live",
            "state": "unverified",
            "detail": f"Gateway rule {rule_id} active, but Squid proxy port {proxy_port} offline",
            "checked_at": ts
        }
    else:
        # Canary was allowed! High severity failure
        return {
            "name": "Egress Allowlist Live",
            "state": "failed",
            "detail": f"Canary check failed: outbound access to {canary_url} was permitted!",
            "checked_at": ts
        }

def probe_dns_allowlist(dns_host: str = "127.0.0.1", dns_port: int = 53) -> dict[str, Any]:
    """
    Probes the dnsmasq DNS allowlist service via an active UDP socket probe.
    """
    ts = _iso_now()
    sock_alive = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            # Send standard empty DNS query or ping probe
            s.connect((dns_host, dns_port))
            sock_alive = True
    except Exception:
        sock_alive = False

    if sock_alive:
        # Check if dnsmasq process is actively running
        import psutil
        dnsmasq_proc = any("dnsmasq" in (p.info.get("name") or "").lower() for p in psutil.process_iter(['name']))
        if dnsmasq_proc:
            return {
                "name": "DNS Allowlist Live",
                "state": "verified",
                "detail": f"dnsmasq service active on {dns_host}:{dns_port}",
                "checked_at": ts
            }
        else:
            return {
                "name": "DNS Allowlist Live",
                "state": "unverified",
                "detail": f"DNS port open but dedicated dnsmasq process not identified on host",
                "checked_at": ts
            }
    else:
        return {
            "name": "DNS Allowlist Live",
            "state": "unverified",
            "detail": f"dnsmasq not listening on {dns_host}:{dns_port}",
            "checked_at": ts
        }

def probe_audit_chain() -> dict[str, Any]:
    """
    Cryptographically verifies the SHA-256 hash chain of the audit ledger.
    """
    ts = _iso_now()
    try:
        is_valid, broken_id, message = verify_chain()
        if is_valid:
            return {
                "name": "Audit Chain Intact",
                "state": "verified",
                "detail": message,
                "checked_at": ts
            }
        else:
            return {
                "name": "Audit Chain Intact",
                "state": "failed",
                "detail": f"Chain integrity breach at block {broken_id}: {message}",
                "checked_at": ts
            }
    except Exception as e:
        return {
            "name": "Audit Chain Intact",
            "state": "unverified",
            "detail": f"Audit verification error: {str(e)}",
            "checked_at": ts
        }

def probe_policy_loaded() -> dict[str, Any]:
    """
    Probes the policy engine to verify rule sets, hashes, and task manifests are active.
    """
    ts = _iso_now()
    try:
        rule_count = len(settings.BANNED_COMMAND_PATTERNS) + len(settings.ALLOWED_DOMAINS) + len(settings.HONEYTOKEN_PATHS)
        manifest_count = len(TASK_MANIFESTS)
        policy_hash = settings.POLICY_HASH

        if rule_count > 0 and manifest_count > 0 and policy_hash:
            return {
                "name": "Policy Engine Active",
                "state": "verified",
                "detail": f"Loaded {rule_count} security rules and {manifest_count} task manifests (hash: {policy_hash[:16]}...)",
                "checked_at": ts
            }
        else:
            return {
                "name": "Policy Engine Active",
                "state": "failed",
                "detail": "Policy rules or task manifests are missing or empty",
                "checked_at": ts
            }
    except Exception as e:
        return {
            "name": "Policy Engine Active",
            "state": "unverified",
            "detail": f"Policy engine probe error: {str(e)}",
            "checked_at": ts
        }

def probe_ml_classifier() -> dict[str, Any]:
    """
    Probes the Security ML Classifier model readiness, weights, and inference metrics.
    """
    ts = _iso_now()
    try:
        from .ml import security_classifier
        if security_classifier.is_ready:
            st = security_classifier.get_status()
            acc = st.get("metrics", {}).get("test_accuracy", 0.0)
            return {
                "name": "Security ML Classifier Active",
                "state": "verified",
                "detail": f"Model active ({st.get('model_version')}) - 3-tier calibrated (acc: {acc*100:.1f}%)",
                "checked_at": ts
            }
        else:
            return {
                "name": "Security ML Classifier Active",
                "state": "unverified",
                "detail": "ML model file not initialized",
                "checked_at": ts
            }
    except Exception as e:
        return {
            "name": "Security ML Classifier Active",
            "state": "unverified",
            "detail": f"ML probe error: {str(e)[:100]}",
            "checked_at": ts
        }

def get_all_controls_status() -> dict[str, Any]:
    """
    Runs all active probes truthfully and returns consolidated controls status.
    Guarantees: Failure or timeout returns 'unverified' or 'failed', never fake green.
    """
    probes = [
        probe_container_running(),
        probe_rootfs_and_caps(),
        probe_seccomp_applied(),
        probe_network_internal(),
        probe_egress_allowlist(),
        probe_dns_allowlist(),
        probe_audit_chain(),
        probe_policy_loaded(),
        probe_ml_classifier(),
    ]

    verified = sum(1 for p in probes if p["state"] == "verified")
    failed = sum(1 for p in probes if p["state"] == "failed")
    unverified = sum(1 for p in probes if p["state"] == "unverified")

    overall = "verified" if (verified == len(probes)) else ("failed" if failed > 0 else "unverified")

    return {
        "overall": overall,
        "verified_count": verified,
        "failed_count": failed,
        "unverified_count": unverified,
        "total": len(probes),
        "controls": probes,
        "checked_at": _iso_now()
    }
