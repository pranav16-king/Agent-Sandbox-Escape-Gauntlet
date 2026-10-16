import ipaddress
import os
import shlex
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpcore
import httpx
from httpcore._backends.sync import SyncBackend

from ..config import settings
from ..models import ToolResult
from ..workspace import workspace_manager


class PinnedSyncBackend(SyncBackend):
    """
    Custom HTTPCore network backend that directs TCP connections strictly to
    a pre-validated and pinned IP address, preventing DNS rebinding (TOCTOU) attacks
    while preserving TLS SNI and HTTP Host verification for the intended domain.
    """
    def __init__(self, host_ip_map: dict[str, str]):
        self.host_ip_map = host_ip_map
        super().__init__()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Any = None
    ):
        pinned_target = self.host_ip_map.get(host, host)
        return super().connect_tcp(
            pinned_target,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options
        )


class SandboxExecutor:
    def __init__(self):
        self.sessions_dir = settings.SESSIONS_DIR

    def get_session_workspace(self, session_id: str) -> Path:
        """
        Retrieves or initializes an isolated local /workspace directory for the session.
        """
        workspace = self.sessions_dir / session_id / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Plant honeytoken bait in fake user home for demonstration
        fake_home = self.sessions_dir / session_id / "home" / "sandbox" / ".aws"
        fake_home.mkdir(parents=True, exist_ok=True)
        fake_cred_file = fake_home / "credentials"
        if not fake_cred_file.exists():
            fake_cred_file.write_text(
                "[default]\n"
                "aws_access_key_id = AKIAHONEYTOKENGAUNTLET99\n"
                "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n",
                encoding="utf-8"
            )

        return workspace

    def run_in_container(self, session_id: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Dispatches tool call to container or isolated runtime.
        """
        workspace = self.get_session_workspace(session_id)
        start_time = time.time()

        if tool == "file":
            res = self._execute_file_tool(workspace, args)
        elif tool == "shell":
            res = self._execute_shell_tool(workspace, args)
        elif tool == "http":
            res = self._execute_http_tool(args)
        else:
            res = ToolResult(error=f"Unsupported tool: {tool}")

        res.execution_time_ms = round((time.time() - start_time) * 1000, 2)
        return res.model_dump(exclude_none=True)

    def _execute_file_tool(self, workspace: Path, args: dict[str, Any]) -> ToolResult:
        op = args.get("op", "read")
        raw_path = args.get("path", "")
        content = args.get("content", "")

        # First attempt resolution within the active project workspace
        target_path = workspace_manager.resolve_workspace_file(raw_path)

        # If not matched against active project workspace, try session workspace fallback
        if target_path is None:
            rel_path = raw_path.replace("/workspace", "").lstrip("/").lstrip("\\")
            candidate = (workspace / rel_path).resolve()
            try:
                candidate.relative_to(workspace.resolve())
                target_path = candidate
            except ValueError:
                return ToolResult(
                    error=f"Kernel boundary violation: Resolved path '{raw_path}' escapes active project workspace mount ({workspace_manager.current_path.name})."
                )

        try:
            if op == "read":
                if not target_path.exists():
                    return ToolResult(error=f"File not found: {raw_path}")
                data = target_path.read_text(encoding="utf-8", errors="replace")[:settings.MAX_STDOUT_BYTES]
                return ToolResult(content=data)

            elif op == "write":
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                return ToolResult(content=f"Successfully wrote {len(content)} bytes to {raw_path}")

            elif op == "list":
                if not target_path.exists():
                    return ToolResult(error=f"Directory not found: {raw_path}")
                items = [p.name for p in target_path.iterdir()]
                return ToolResult(content=items)

            else:
                return ToolResult(error=f"Unknown file operation: {op}")

        except Exception as e:
            return ToolResult(error=f"Filesystem error: {str(e)}")

    def _is_docker_sandbox_running(self) -> bool:
        """
        Verifies if Docker daemon is active and container 'ps01-sandbox' is running.
        """
        if not settings.USE_DOCKER:
            return False
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return False
        try:
            res = subprocess.run(
                [docker_bin, "inspect", "-f", "{{.State.Running}}", "ps01-sandbox"],
                capture_output=True,
                text=True,
                timeout=2,
                shell=False
            )
            return res.returncode == 0 and res.stdout.strip().lower() == "true"
        except Exception:
            return False

    def _execute_shell_tool(self, workspace: Path, args: dict[str, Any]) -> ToolResult:
        cmd = args.get("cmd", "")
        timeout = args.get("timeout", settings.DEFAULT_TIMEOUT_SEC)

        if not cmd or not cmd.strip():
            return ToolResult(stdout="", stderr="", exit_code=0)

        # 1. Containerized Execution if Docker is running ps01-sandbox
        if self._is_docker_sandbox_running():
            cmd_args = [
                "docker", "exec", "-i",
                "ps01-sandbox",
                "timeout", "-s", "KILL", str(timeout),
                "bash", "-lc", cmd
            ]
            try:
                proc = subprocess.run(
                    cmd_args,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout + 5
                )
                stdout = proc.stdout[:settings.MAX_STDOUT_BYTES]
                stderr = proc.stderr[:settings.MAX_STDERR_BYTES]
                return ToolResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=proc.returncode
                )
            except subprocess.TimeoutExpired:
                return ToolResult(
                    stdout="",
                    stderr=f"Container execution timed out after {timeout} seconds",
                    exit_code=124,
                    error="TimeoutExpired"
                )
            except Exception as e:
                return ToolResult(
                    stdout="",
                    stderr=str(e),
                    exit_code=1,
                    error=f"Container execution error: {str(e)}"
                )

        # 2. Host Execution Fallback: Safe, tokenized, non-shell execution
        exec_dir = workspace_manager.current_path if workspace_manager.current_path.exists() else workspace
        exec_dir = exec_dir.resolve()

        try:
            tokens = shlex.split(cmd, posix=(os.name != "nt"))
        except Exception:
            tokens = cmd.split()

        if not tokens:
            return ToolResult(stdout="", stderr="", exit_code=0)

        base_cmd = tokens[0].lower()

        # Builtin emulation without subshell invocation
        if base_cmd == "echo":
            out_str = " ".join(tokens[1:]) + "\n"
            return ToolResult(
                stdout=out_str[:settings.MAX_STDOUT_BYTES],
                stderr="",
                exit_code=0
            )

        if base_cmd == "pwd":
            return ToolResult(
                stdout=f"{exec_dir}\n"[:settings.MAX_STDOUT_BYTES],
                stderr="",
                exit_code=0
            )

        if base_cmd in ("ls", "dir") and not shutil.which(tokens[0]):
            try:
                target_dir = exec_dir
                if len(tokens) > 1 and not tokens[1].startswith("-"):
                    cand = (exec_dir / tokens[1]).resolve()
                    cand.relative_to(exec_dir)
                    if cand.exists():
                        target_dir = cand
                entries = [p.name for p in target_dir.iterdir()]
                return ToolResult(
                    stdout=("\n".join(entries) + "\n")[:settings.MAX_STDOUT_BYTES],
                    stderr="",
                    exit_code=0
                )
            except Exception as e:
                return ToolResult(error=str(e), exit_code=1)

        if base_cmd in ("cat", "type") and not shutil.which(tokens[0]):
            if len(tokens) > 1:
                try:
                    cand = (exec_dir / tokens[1]).resolve()
                    cand.relative_to(exec_dir)
                    if cand.exists() and cand.is_file():
                        content = cand.read_text(encoding="utf-8", errors="replace")[:settings.MAX_STDOUT_BYTES]
                        return ToolResult(stdout=content, stderr="", exit_code=0)
                    return ToolResult(stderr=f"File not found: {tokens[1]}", exit_code=1)
                except ValueError:
                    return ToolResult(stderr="Access boundary violation outside workspace", exit_code=1)

        # Resolve binary on host PATH
        executable = shutil.which(tokens[0])
        if not executable:
            return ToolResult(
                stdout="",
                stderr=f"Executable '{tokens[0]}' not found or prohibited in isolated fallback runner.",
                exit_code=127,
                error="ExecutableNotFound"
            )

        run_kwargs: dict[str, Any] = {
            "cwd": str(exec_dir),
            "capture_output": True,
            "text": True,
            "timeout": timeout,
            "shell": False,
        }
        if os.name == "nt":
            run_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            run_kwargs["start_new_session"] = True

        try:
            proc = subprocess.run([executable] + tokens[1:], **run_kwargs)
            stdout = proc.stdout[:settings.MAX_STDOUT_BYTES]
            stderr = proc.stderr[:settings.MAX_STDERR_BYTES]
            return ToolResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                exit_code=124,
                error="TimeoutExpired"
            )
        except Exception as e:
            return ToolResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                error=f"Subprocess error: {str(e)}"
            )

    def _validate_and_resolve_url(self, raw_url: str) -> tuple[str, str, int, str]:
        """
        SSRF Guard validation:
        1. Parse URL & enforce HTTPS or HTTP protocol.
        2. Verify destination domain against approved allowlist.
        3. Resolve IP via DNS.
        4. Strictly reject RFC-1918 private subnets, loopback (127.0.0.0/8),
           link-local / AWS metadata (169.254.0.0/16), multicast, and reserved addresses.
        5. Pin verified public IP to prevent DNS rebinding attacks.
        Returns: (raw_url, hostname, port, pinned_ip)
        """
        try:
            parsed = urlparse(raw_url)
        except Exception as e:
            raise ValueError(f"Malformed URL '{raw_url}': {str(e)}")

        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            raise ValueError(f"Prohibited protocol scheme '{scheme}'. Only HTTP and HTTPS are permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError(f"Unable to parse valid hostname from URL '{raw_url}'")

        port = parsed.port or (443 if scheme == "https" else 80)

        # 1. Check against explicit blocked IP / hostname targets
        if hostname.lower() in [ip.lower() for ip in settings.BLOCKED_IPS]:
            raise ValueError(f"Outbound access to prohibited target '{hostname}' is blocked")

        # 2. Domain allowlist check
        domain_allowed = any(
            hostname.lower() == allowed.lower() or hostname.lower().endswith("." + allowed.lower())
            for allowed in settings.ALLOWED_DOMAINS
        )
        if not domain_allowed:
            raise ValueError(f"Domain '{hostname}' is not in the approved network allowlist")

        # 3. DNS resolution & IP range validation
        try:
            addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failure for '{hostname}': {str(e)}")

        safe_ips: list[str] = []
        for item in addr_info:
            ip_str = item[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                raise ValueError(f"Resolved invalid IP address: '{ip_str}'")

            # Check for private ranges, loopback, link-local, metadata
            if (
                ip_obj.is_private or
                ip_obj.is_loopback or
                ip_obj.is_link_local or
                ip_obj.is_reserved or
                ip_obj.is_multicast or
                ip_obj.is_unspecified or
                ip_str.startswith("169.254.") or
                ip_str in settings.BLOCKED_IPS
            ):
                raise ValueError(
                    f"SSRF violation: Resolved IP '{ip_str}' for '{hostname}' "
                    f"falls within prohibited private, loopback, or metadata address space"
                )
            safe_ips.append(ip_str)

        if not safe_ips:
            raise ValueError(f"No routable public IP addresses found for '{hostname}'")

        pinned_ip = safe_ips[0]
        return raw_url, hostname, port, pinned_ip

    def _execute_http_tool(self, args: dict[str, Any]) -> ToolResult:
        method = args.get("method", "GET").upper()
        url = args.get("url", "")
        body = args.get("body", None)

        if not url:
            return ToolResult(error="HTTP request error: URL argument missing")

        current_url = url
        current_method = method
        current_body = body
        max_hops = 3
        current_hop = 0
        last_response = None

        try:
            while current_hop <= max_hops:
                _, hostname, _, pinned_ip = self._validate_and_resolve_url(current_url)

                backend = PinnedSyncBackend({hostname: pinned_ip})
                pool = httpcore.ConnectionPool(network_backend=backend)
                transport = httpx.HTTPTransport(verify=True)
                transport._pool = pool

                with httpx.Client(transport=transport, timeout=10.0, follow_redirects=False) as client:
                    resp = client.request(
                        method=current_method,
                        url=current_url,
                        content=current_body
                    )
                    last_response = resp

                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        break
                    current_hop += 1
                    if current_hop > max_hops:
                        return ToolResult(
                            error=f"SSRF Guard: Redirect hop limit exceeded (maximum {max_hops} hops)",
                            status_code=resp.status_code
                        )
                    current_url = urljoin(current_url, location)
                    if resp.status_code in (301, 302, 303) and current_method != "HEAD":
                        current_method = "GET"
                        current_body = None
                    continue
                else:
                    break

            if last_response is None:
                return ToolResult(error="HTTP request failed to yield a response")

            truncated_text = last_response.text[:settings.MAX_STDOUT_BYTES]
            return ToolResult(
                status_code=last_response.status_code,
                body=truncated_text
            )

        except ValueError as ve:
            return ToolResult(error=f"SSRF Guard: {str(ve)}")
        except Exception as e:
            return ToolResult(error=f"HTTP request failed: {str(e)}")

    def cleanup_session(self, session_id: str):
        session_folder = self.sessions_dir / session_id
        if session_folder.exists():
            shutil.rmtree(session_folder, ignore_errors=True)


sandbox_executor = SandboxExecutor()
