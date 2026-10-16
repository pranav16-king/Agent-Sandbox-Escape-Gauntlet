import os
import re
import posixpath
from urllib.parse import urlparse
from typing import Tuple

from ..config import settings
from ..models import TaskManifest

def normalize_path(raw_path: str) -> str:
    """
    Normalizes a path to a canonical POSIX path.
    """
    clean_path = raw_path.replace("\\", "/").strip()
    # Normalize relative segments
    clean_path = posixpath.normpath(clean_path)
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    return clean_path

def check_path_security(raw_path: str, op: str, manifest: TaskManifest) -> Tuple[bool, str, str]:
    """
    Verifies that file access respects /workspace boundaries, honeytokens, and task manifests.
    Returns:
        (allowed, rule_id, reason)
    """
    norm = normalize_path(raw_path)

    # 1. Honeytoken Tripwire Check (HT-001)
    for ht in settings.HONEYTOKEN_PATHS:
        ht_norm = normalize_path(ht)
        if norm == ht_norm or norm.endswith(ht_norm) or ".aws/credentials" in norm or ".ssh/id_rsa" in norm:
            return False, "HT-001", f"Access to honeytoken tripwire '{raw_path}' triggered high-severity alert"

    # 2. Strict /workspace boundary containment (FS-001)
    if not (norm == "/workspace" or norm.startswith("/workspace/")):
        return False, "FS-001", f"Path '{raw_path}' resolves outside /workspace boundary"

    # 3. Path traversal detection (FS-002)
    if ".." in raw_path.split("/") or ".." in raw_path.split("\\"):
        return False, "FS-002", f"Path traversal sequence '..' detected in '{raw_path}'"

    # 4. Task Manifest Path Scoping (FS-003)
    if op in ("read", "list"):
        if manifest.paths_read:
            matched = any(
                norm == normalize_path(p) or norm.startswith(normalize_path(p) + "/")
                for p in manifest.paths_read
            )
            if not matched:
                return False, "FS-003", f"Read path '{raw_path}' not permitted under task '{manifest.task_id}' manifest"
    elif op == "write":
        if manifest.paths_write:
            matched = any(
                norm == normalize_path(p) or norm.startswith(normalize_path(p) + "/")
                for p in manifest.paths_write
            )
            if not matched:
                return False, "FS-003", f"Write path '{raw_path}' not permitted under task '{manifest.task_id}' manifest"

    return True, "FS-PASS", "Path permitted within /workspace"

def check_command_security(cmd: str) -> Tuple[bool, str, str]:
    """
    Inspects shell command for dangerous binaries, reverse shells, fork bombs, and bypasses.
    Returns:
        (allowed, rule_id, reason)
    """
    stripped_cmd = cmd.strip()

    # 1. Check for banned binaries and regex signatures (CMD-001)
    for pattern in settings.BANNED_COMMAND_PATTERNS:
        if re.search(pattern, stripped_cmd, re.IGNORECASE):
            return False, "CMD-001", f"Command matched forbidden security pattern: '{pattern}'"

    # 2. Reverse shell / raw network socket signatures (CMD-002)
    reverse_shell_indicators = [
        r"/bin/(ba)?sh\s+-i",
        r"bash\s+-[ic]\s+.*>&",
        r"exec\s+\d+<>/dev/tcp",
        r"socket\.socket\(",
        r"subprocess\.Popen\(",
        r"pty\.spawn\(",
    ]
    for pattern in reverse_shell_indicators:
        if re.search(pattern, stripped_cmd, re.IGNORECASE):
            return False, "CMD-002", f"Reverse shell / arbitrary code execution pattern detected: '{pattern}'"

    # 3. Sensitive file inspection commands (CMD-003)
    sensitive_targets = [
        r"/etc/shadow",
        r"/etc/passwd",
        r"/proc/1/environ",
        r"/proc/self/environ",
        r"~?/\.aws",
        r"~?/\.ssh",
        r"~?/\.bashrc",
        r"/etc/crontab",
    ]
    for target in sensitive_targets:
        if re.search(target, stripped_cmd, re.IGNORECASE):
            return False, "CMD-003", f"Command targets protected system path: '{target}'"

    return True, "CMD-PASS", "Command passed static inspection"

def check_network_security(url: str, manifest: TaskManifest) -> Tuple[bool, str, str]:
    """
    Inspects destination URL against allowlist, private IPs, and metadata endpoints.
    Returns:
        (allowed, rule_id, reason)
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, "NET-001", f"Malformed URL '{url}': {str(e)}"

    host = parsed.hostname or parsed.netloc.split(":")[0]
    if not host:
        return False, "NET-002", f"Unable to parse hostname from URL '{url}'"

    # 1. Block Cloud Metadata IP & Private IPs (NET-003)
    if host in settings.BLOCKED_IPS:
        return False, "NET-003", f"Outbound access to private/metadata IP '{host}' is strictly forbidden"

    if host.startswith("169.254.") or host.startswith("127.") or host.startswith("10.") or host.startswith("192.168."):
        return False, "NET-003", f"Outbound access to internal IP subnet '{host}' is blocked"

    # 2. Domain Allowlist Check (NET-004)
    allowed_domains = set(settings.ALLOWED_DOMAINS)
    if manifest.domains:
        # If task has specific domain list, intersect or prioritize it
        task_domains = set(manifest.domains)
    else:
        task_domains = allowed_domains

    # Check exact host or parent domain
    domain_allowed = any(
        host == allowed or host.endswith("." + allowed)
        for allowed in task_domains
    )

    if not domain_allowed:
        return False, "NET-004", f"Domain '{host}' is not in the approved network allowlist for task '{manifest.task_id}'"

    return True, "NET-PASS", f"Domain '{host}' approved by egress policy"
