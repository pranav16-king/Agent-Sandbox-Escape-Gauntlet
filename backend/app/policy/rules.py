import os
import re
import shlex
import posixpath
from urllib.parse import urlparse
from typing import Tuple, Optional

from ..config import settings
from ..models import TaskManifest, DecisionType
from ..workspace import workspace_manager

# Metacharacters for shell chaining / command substitution (forbidden / escalated)
METACHAR_PATTERNS = [
    (r";", "Command chaining with ';' is forbidden"),
    (r"&&", "Command chaining with '&&' is forbidden"),
    (r"\|\|", "Command chaining with '||' is forbidden"),
    (r"`", "Backtick command substitution is forbidden"),
    (r"\$\(", "Subshell command expansion '$()' is forbidden"),
    (r"<\(", "Process substitution '<()' is forbidden"),
    (r">\s*\(", "Process substitution '>()' is forbidden"),
]

# Explicitly banned binaries and administrative commands
BANNED_BINARIES = {
    "sudo", "su", "mount", "umount", "chmod", "chown", "chattr",
    "nc", "netcat", "ncat", "socat", "dd", "mkfs", "reboot", "shutdown",
    "useradd", "groupadd", "usermod", "groupmod", "userdel", "groupdel",
    "ptrace", "keyctl", "insmod", "rmmod", "modprobe", "iptables", "nft"
}

# Protected system paths that must never be targeted by any shell argument
PROTECTED_SYSTEM_PATHS = [
    "/proc",
    "/sys",
    "/var/run/docker.sock",
    "/var/run",
    "/etc/shadow",
    "/etc/passwd",
    "/etc/sudoers",
    "/dev",
    "/root",
]

# Read-only approved command executables (ALLOW tier inside workspace)
READONLY_COMMANDS = {
    "ls", "dir", "cat", "head", "tail", "grep", "rg", "find",
    "pwd", "whoami", "id", "echo", "printf", "diff", "wc", "stat",
    "tree", "sort", "uniq", "pytest"
}

# Allowed tools/interpreters requiring inspection of arguments/subcommands
ALLOWED_EXECUTABLES = READONLY_COMMANDS | {
    "python", "python3", "node", "git", "pip", "npm",
    "touch", "mkdir", "cp", "mv", "rm"
}

# Modifying/write shell commands (ASK tier)
WRITE_COMMANDS = {
    "touch", "mkdir", "cp", "mv", "rm"
}

def normalize_path(raw_path: str) -> str:
    """
    Normalizes a path to a canonical POSIX path.
    """
    clean_path = raw_path.replace("\\", "/").strip()
    clean_path = posixpath.normpath(clean_path)
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    return clean_path

def canonicalize_and_verify_path(path_str: str, cwd: Optional[str] = None) -> Tuple[bool, str, str]:
    """
    Canonicalizes every path argument using os.path.realpath(os.path.join(cwd, arg))
    and verifies strict containment inside /workspace or the active project root.
    """
    host_root = os.path.realpath(str(workspace_manager.current_path))
    clean_cwd = cwd or host_root

    # 1. Honeytoken Tripwire Check
    norm = normalize_path(path_str)
    for ht in settings.HONEYTOKEN_PATHS:
        ht_norm = normalize_path(ht)
        if (norm == ht_norm or norm.endswith(ht_norm) or 
            ".aws/credentials" in norm or ".ssh/id_rsa" in norm or "fake_aws" in norm):
            return False, "HT-001", f"Access to honeytoken tripwire '{path_str}' triggered high-severity alert"

    # 2. Path traversal sequence check
    path_parts = path_str.replace("\\", "/").split("/")
    if ".." in path_parts:
        return False, "FS-002", f"Path traversal sequence '..' detected in '{path_str}'"

    # 3. Resolve realpath & workspace containment check (FS-001)
    if path_str.startswith("/workspace"):
        rel_sub = path_str[len("/workspace"):].lstrip("/\\")
        resolved = os.path.realpath(os.path.join(host_root, rel_sub))
    elif os.path.isabs(path_str):
        resolved = os.path.realpath(path_str)
    else:
        resolved = os.path.realpath(os.path.join(clean_cwd, path_str))

    is_inside_host = (resolved == host_root or resolved.startswith(host_root + os.sep))
    is_virtual_ws = (norm == "/workspace" or norm.startswith("/workspace/"))

    if not (is_inside_host or is_virtual_ws):
        ws_name = workspace_manager.current_path.name or "workspace"
        return False, "FS-001", f"Path '{path_str}' resolves outside /workspace boundary ({ws_name})"

    # 4. Protected system directory check within workspace (ESC-001)
    for sp in PROTECTED_SYSTEM_PATHS:
        if norm == sp or norm.startswith(sp + "/") or path_str.startswith(sp):
            return False, "ESC-001", f"Targeting protected system path '{path_str}' is strictly forbidden (outside /workspace boundary)"

    return True, "FS-PASS", "Path permitted within workspace"

def check_path_security(raw_path: str, op: str, manifest: TaskManifest) -> Tuple[bool, str, str]:
    """
    Verifies that file access respects project workspace boundaries, honeytokens, and task manifests.
    Returns:
        (allowed, rule_id, reason)
    """
    allowed, rule_id, reason = canonicalize_and_verify_path(raw_path)
    if not allowed:
        return False, rule_id, reason

    norm = normalize_path(raw_path)

    # Canonicalize project workspace file to /workspace/<rel> for manifest evaluation
    if not norm.startswith("/workspace") and workspace_manager.is_inside_workspace(raw_path):
        resolved_file = workspace_manager.resolve_workspace_file(raw_path)
        if resolved_file:
            try:
                rel_sub = resolved_file.relative_to(workspace_manager.current_path).as_posix()
                norm = f"/workspace/{rel_sub}" if rel_sub != "." else "/workspace"
            except Exception:
                pass

    # Task Manifest Path Scoping
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

def check_command_security(cmd: str) -> Tuple[DecisionType, str, str]:
    """
    Inspects shell command using allowlist-first security:
    1. Reject forbidden metacharacters (;, &&, ||, backticks, $(), <())
    2. Tokenize via shlex.split
    3. Check binary against allowlist & banned lists
    4. Canonicalize every path argument requiring resolution strictly inside /workspace
    5. Categorize into tiers: ALLOW (read-only), ASK (writes, installs, pipes), DENY (banned)
    Returns:
        (decision: DecisionType, rule_id: str, reason: str)
    """
    stripped_cmd = cmd.strip()
    if not stripped_cmd:
        return DecisionType.BLOCK, "CMD-001", "Empty shell command"

    # 1. Regex signature check against banned patterns (fork bombs, dev tcp, etc.)
    for pattern in settings.BANNED_COMMAND_PATTERNS:
        if re.search(pattern, stripped_cmd, re.IGNORECASE):
            return DecisionType.BLOCK, "CMD-001", f"Command matched forbidden security pattern: '{pattern}'"

    # 2. Reverse shell / raw network socket signatures
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
            return DecisionType.BLOCK, "CMD-002", f"Reverse shell / arbitrary code execution pattern detected: '{pattern}'"

    # 3. Metacharacter validation: reject chaining/substitution
    for pattern, desc in METACHAR_PATTERNS:
        if re.search(pattern, stripped_cmd):
            return DecisionType.BLOCK, "CMD-001", desc

    # 4. Tokenize command with shlex.split
    try:
        tokens = shlex.split(stripped_cmd)
    except ValueError as e:
        return DecisionType.BLOCK, "CMD-001", f"Command failed tokenization (unbalanced quotes or syntax): {str(e)}"

    if not tokens:
        return DecisionType.BLOCK, "CMD-001", "No command tokens found"

    # Check for pipes or file output redirections (| , >, >>) -> Escalate to ASK tier
    has_pipe_or_redirect = ("|" in tokens or ">" in tokens or ">>" in tokens or 
                            "|" in stripped_cmd or ">" in stripped_cmd)

    exe_raw = tokens[0]
    exe = posixpath.basename(exe_raw.replace("\\", "/")).lower()

    # 5. Check against banned binaries
    if exe in BANNED_BINARIES or any(t.lower() in BANNED_BINARIES for t in tokens):
        return DecisionType.BLOCK, "CMD-001", f"Command executable or token '{exe}' is strictly banned"

    # 6. Check against allowed executables
    if exe not in ALLOWED_EXECUTABLES:
        return DecisionType.BLOCK, "CMD-001", f"Command '{exe}' is not in approved allowlist"

    # 7. Sensitive system path check
    for target in PROTECTED_SYSTEM_PATHS:
        if any(target in t for t in tokens):
            return DecisionType.BLOCK, "CMD-003", f"Command targets protected system path: '{target}'"

    # 8. Canonicalize every path argument with os.path.realpath
    host_root = os.path.realpath(str(workspace_manager.current_path))
    for arg in tokens[1:]:
        # Skip flags and common subcommands
        if arg.startswith("-") or arg in ("status", "diff", "log", "show", "branch", "install", "list", "-m", "-v"):
            continue

        # Check if argument resembles a path or file
        if "/" in arg or "\\" in arg or arg.endswith((".py", ".txt", ".json", ".csv", ".md", ".sh", ".js")):
            valid, rule_id, reason = canonicalize_and_verify_path(arg, cwd=host_root)
            if not valid:
                return DecisionType.BLOCK, rule_id, reason

    # 9. Tier categorization:
    # Pipes/redirects -> ASK tier
    if has_pipe_or_redirect:
        return DecisionType.ASK, "CMD-ASK", "Command uses pipe or redirection; escalating to HITL approval"

    # Modifying commands -> ASK tier
    if exe in WRITE_COMMANDS:
        return DecisionType.ASK, "CMD-ASK", f"Command '{exe}' modifies workspace files; escalating to HITL approval"

    # Package installs -> ASK tier
    if exe in ("pip", "npm") and any(sub in tokens[1:] for sub in ("install", "uninstall", "update", "i")):
        return DecisionType.ASK, "CMD-ASK", f"Package manager '{exe}' installation command requires approval"

    # Git operations: status/diff/log -> ALLOW; commit/push/checkout -> ASK
    if exe == "git":
        subcmds = [t for t in tokens[1:] if not t.startswith("-")]
        if subcmds and subcmds[0] not in ("status", "diff", "log", "show", "branch"):
            return DecisionType.ASK, "CMD-ASK", f"Git operation 'git {subcmds[0]}' requires operator approval"

    return DecisionType.ALLOW, "CMD-PASS", "Command approved by allowlist-first policy"

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
        task_domains = set(manifest.domains)
    else:
        task_domains = allowed_domains

    domain_allowed = any(
        host == allowed or host.endswith("." + allowed)
        for allowed in task_domains
    )

    if not domain_allowed:
        return False, "NET-004", f"Domain '{host}' is not in the approved network allowlist for task '{manifest.task_id}'"

    return True, "NET-PASS", f"Domain '{host}' approved by egress policy"
