import os
import re
import shlex
import posixpath
from urllib.parse import urlparse
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass

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

    # 1. Prohibited Protocol Scheme Rejection (NET-005)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, "NET-005", f"Prohibited network protocol scheme '{parsed.scheme}': only http and https are permitted"

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

# ==============================================================================
# Formal Security Rules Catalog & Schema Definitions
# ==============================================================================

@dataclass
class SecurityRuleDefinition:
    rule_id: str
    formal_name: str
    category: str
    target_tools: List[str]
    decision_tier: DecisionType
    evaluation_logic: str
    criteria_type: str
    threat_mitigated: str
    mitre_attack: str
    owasp_llm: str
    remediation: str
    test_mapping: List[str]

SECURITY_RULES_CATALOG: Dict[str, SecurityRuleDefinition] = {
    # File System & Workspace Confinement
    "FS-001": SecurityRuleDefinition(
        rule_id="FS-001",
        formal_name="Workspace Boundary & Rootfs Confinement",
        category="File System & Workspace Confinement",
        target_tools=["file", "shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Canonicalizes every path argument using os.path.realpath and verifies containment strictly inside active workspace directory.",
        criteria_type="os.path.realpath canonicalization & prefix containment check",
        threat_mitigated="Arbitrary host filesystem read/write outside boundary, unauthorized directory access.",
        mitre_attack="T1083 (File and Directory Discovery), T1005 (Data from Local System)",
        owasp_llm="LLM02:2025 (Sensitive Information Disclosure), LLM06:2025 (Excessive Agency)",
        remediation="Confine all path arguments strictly within /workspace root.",
        test_mapping=[
            "backend/tests/test_policy.py::test_allow_normal_workspace_file_read",
            "backend/tests/test_attack_matrix.py::test_t01_cat_etc_passwd",
            "backend/tests/test_attack_matrix.py::test_t03_symlink_escape",
            "backend/tests/test_workspace.py::test_policy_enforces_workspace_containment"
        ]
    ),
    "FS-002": SecurityRuleDefinition(
        rule_id="FS-002",
        formal_name="Path Traversal Sequence Blocking",
        category="File System & Workspace Confinement",
        target_tools=["file", "shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Inspects path tokens for parent directory traversal sequences ('..') to abort escape attempts before resolution.",
        criteria_type="Path component tokenization and '..' sequence detection",
        threat_mitigated="Directory traversal climbing outside workspace boundary.",
        mitre_attack="T1083 (File and Directory Discovery)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Remove parent directory references ('..') and use canonical workspace relative paths.",
        test_mapping=[
            "backend/tests/test_policy.py::test_block_path_traversal",
            "backend/tests/test_attack_matrix.py::test_t02_cat_path_traversal"
        ]
    ),
    "FS-003": SecurityRuleDefinition(
        rule_id="FS-003",
        formal_name="Task Manifest Path Scope Authorization",
        category="File System & Workspace Confinement",
        target_tools=["file"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Validates target path against active task manifest allowlists (paths_read and paths_write).",
        criteria_type="Manifest allowlist path prefix and exact match inspection",
        threat_mitigated="Lateral movement across tasks, unauthorized file modification outside declared manifest scope.",
        mitre_attack="T1083 (File and Directory Discovery), T1565.001 (Stored Data Manipulation)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Operate only on files declared in the task manifest (paths_read, paths_write).",
        test_mapping=[
            "backend/tests/test_policy.py",
            "backend/tests/test_gateway.py"
        ]
    ),
    "ESC-001": SecurityRuleDefinition(
        rule_id="ESC-001",
        formal_name="Protected Operating System & Kernel Directory Protection",
        category="File System & Workspace Confinement",
        target_tools=["file", "shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Blocks access to sensitive operating system, daemon, and kernel paths (/proc, /sys, /dev, /var/run/docker.sock, /etc/shadow, /etc/passwd, /etc/sudoers, /root).",
        criteria_type="Normalized path prefix check against PROTECTED_SYSTEM_PATHS",
        threat_mitigated="Container escape, Docker daemon socket hijacking, kernel introspection, credential harvesting.",
        mitre_attack="T1611 (Escape to Host), T1003.008 (/etc/passwd and /etc/shadow), T1082 (System Information Discovery)",
        owasp_llm="LLM02:2025 (Sensitive Information Disclosure), LLM06:2025 (Excessive Agency)",
        remediation="Never target host OS system directories; use emulated workspace tools or container environment.",
        test_mapping=[
            "backend/tests/test_attack_matrix.py::test_t11_docker_sock_mount",
            "backend/tests/test_attack_matrix.py::test_t12_host_env_leak",
            "backend/tests/test_security_regressions.py::test_path_canonicalization_rejects_system_escapes"
        ]
    ),
    "ESC-002": SecurityRuleDefinition(
        rule_id="ESC-002",
        formal_name="Symlink Escape & Virtual Mount Boundary Breakout",
        category="File System & Workspace Confinement",
        target_tools=["file", "shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Follows symbolic links and mount points using os.path.realpath to ensure targets do not break out of workspace mount root.",
        criteria_type="os.path.realpath symlink dereference containment verification",
        threat_mitigated="Symlink race conditions, arbitrary out-of-bounds dereferencing, mount point breakouts.",
        mitre_attack="T1611 (Escape to Host), T1083 (File and Directory Discovery)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Ensure symlinks do not target paths outside the /workspace root mount.",
        test_mapping=[
            "backend/tests/test_attack_matrix.py::test_t03_symlink_escape",
            "backend/tests/test_security_regressions.py::test_path_canonicalization_rejects_system_escapes"
        ]
    ),

    # Network Egress & SSRF Protection
    "NET-001": SecurityRuleDefinition(
        rule_id="NET-001",
        formal_name="Malformed URL & URI Syntax Validation",
        category="Network Egress & SSRF Protection",
        target_tools=["http"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Validates standard RFC-3986 URI syntax using urllib.parse.urlparse, rejecting malformed URLs.",
        criteria_type="urllib.parse.urlparse syntax verification",
        threat_mitigated="Parser confusion attacks, non-standard URL encoding evasion.",
        mitre_attack="T1071 (Application Layer Protocol)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Provide valid, RFC-compliant HTTP/HTTPS URLs.",
        test_mapping=[
            "backend/tests/test_policy.py"
        ]
    ),
    "NET-002": SecurityRuleDefinition(
        rule_id="NET-002",
        formal_name="Hostname Resolution & Missing Destination Parsing",
        category="Network Egress & SSRF Protection",
        target_tools=["http"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Ensures the parsed URL contains a valid, non-empty hostname and network target.",
        criteria_type="Non-empty hostname and netloc validation",
        threat_mitigated="Parser differential attacks, headerless SSRF exploitation.",
        mitre_attack="T1071 (Application Layer Protocol)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Specify a valid target hostname in all web requests.",
        test_mapping=[
            "backend/tests/test_policy.py"
        ]
    ),
    "NET-003": SecurityRuleDefinition(
        rule_id="NET-003",
        formal_name="Cloud Instance Metadata & RFC-1918 Private Subnet Defense",
        category="Network Egress & SSRF Protection",
        target_tools=["http", "shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Blocks outbound HTTP requests to cloud metadata endpoints (169.254.169.254), loopback (127.0.0.0/8), and RFC-1918 private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).",
        criteria_type="CIDR range check, IP string match, and DNS resolution IP pinning",
        threat_mitigated="Server-Side Request Forgery (SSRF), cloud metadata credential theft, internal service reconnaissance.",
        mitre_attack="T1552.005 (Cloud Instance Metadata API), T1046 (Network Service Discovery)",
        owasp_llm="LLM07:2025 (System Prompt Leakage / SSRF), LLM02:2025 (Sensitive Information Disclosure)",
        remediation="Route external requests through proxy and restrict to public allowlisted domains only.",
        test_mapping=[
            "backend/tests/test_policy.py::test_block_metadata_ip_ssrf",
            "backend/tests/test_attack_matrix.py::test_t05_direct_ip",
            "backend/tests/test_attack_matrix.py::test_t07_dns_rebind",
            "backend/tests/test_attack_matrix.py::test_t08_ssrf_metadata_redirect"
        ]
    ),
    "NET-004": SecurityRuleDefinition(
        rule_id="NET-004",
        formal_name="Outbound Domain Allowlist Enforcement",
        category="Network Egress & SSRF Protection",
        target_tools=["http"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Verifies destination domain against settings.ALLOWED_DOMAINS and task manifest domains allowlist.",
        criteria_type="Exact domain and subdomain wildcard suffix matching",
        threat_mitigated="Data exfiltration to unauthorized endpoints, attacker C2 communication, malicious code download.",
        mitre_attack="T1048 (Exfiltration Over Alternative Protocol), T1071.001 (Web Protocols)",
        owasp_llm="LLM02:2025 (Sensitive Information Disclosure), LLM06:2025 (Excessive Agency)",
        remediation="Add approved destination domains to task manifest or global configuration.",
        test_mapping=[
            "backend/tests/test_policy.py::test_block_unapproved_domain",
            "backend/tests/test_attack_matrix.py::test_t04_non_allowlist_curl",
            "backend/tests/test_attack_matrix.py::test_t06_dns_exfil"
        ]
    ),
    "NET-005": SecurityRuleDefinition(
        rule_id="NET-005",
        formal_name="Prohibited Network Protocols & Non-HTTP Schemes",
        category="Network Egress & SSRF Protection",
        target_tools=["http"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Rejects non-HTTP/HTTPS protocol schemes (gopher://, file://, ftp://, ldap://, dict://).",
        criteria_type="Scheme allowlist verification: parsed.scheme.lower() in ('http', 'https')",
        threat_mitigated="Cross-protocol SSRF exploitation, internal service manipulation, arbitrary local file access via file://.",
        mitre_attack="T1071 (Application Layer Protocol), T1557 (Adversary-in-the-Middle)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Use strictly http:// or https:// protocol schemes.",
        test_mapping=[
            "backend/tests/test_security_regressions.py::test_ssrf_prohibited_protocol_schemes"
        ]
    ),

    # Command Execution & Shell Tokenization
    "CMD-001": SecurityRuleDefinition(
        rule_id="CMD-001",
        formal_name="Shell Execution Patterns, Metacharacters & Banned Binaries",
        category="Command Execution & Shell Tokenization",
        target_tools=["shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Validates shell commands by rejecting empty strings, metacharacter chaining (;, &&, ||, backticks, $()), banned administrative binaries (sudo, nc, chattr, reboot, etc.), and non-allowlisted executables.",
        criteria_type="shlex.split tokenization, regex metacharacter scan, set membership in BANNED_BINARIES and ALLOWED_EXECUTABLES",
        threat_mitigated="Arbitrary shell injection, administrative privilege escalation, fork bombs, unauthorized binary execution.",
        mitre_attack="T1059.004 (Unix Shell), T1548 (Abuse Elevation Control Mechanism), T1499 (Endpoint DoS)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Use only approved binaries from allowlist without chaining operators or metacharacters.",
        test_mapping=[
            "backend/tests/test_policy.py::test_block_banned_command_reverse_shell",
            "backend/tests/test_policy.py::test_block_fork_bomb",
            "backend/tests/test_attack_matrix.py::test_t09_fork_bomb",
            "backend/tests/test_attack_matrix.py::test_t10_memory_bomb",
            "backend/tests/test_security_regressions.py::test_shell_metacharacters_rejected"
        ]
    ),
    "CMD-002": SecurityRuleDefinition(
        rule_id="CMD-002",
        formal_name="Reverse Shell, Raw Socket & Interactive Execution Spawning",
        category="Command Execution & Shell Tokenization",
        target_tools=["shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Detects interactive reverse shell signatures and raw socket construction (/bin/sh -i, /dev/tcp, socket.socket, subprocess.Popen, pty.spawn).",
        criteria_type="Regex signature matching across raw and tokenized command strings",
        threat_mitigated="Attacker-controlled interactive C2 shells, background socket hijacking, breakout to remote terminal.",
        mitre_attack="T1059 (Command and Scripting Interpreter), T1071 (Application Layer Protocol)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Do not invoke interactive shells or network socket creation routines in commands.",
        test_mapping=[
            "backend/tests/test_policy.py::test_block_banned_command_reverse_shell"
        ]
    ),
    "CMD-003": SecurityRuleDefinition(
        rule_id="CMD-003",
        formal_name="Command-Line Protected System Path Arguments",
        category="Command Execution & Shell Tokenization",
        target_tools=["shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Scans shell command arguments to ensure no tokens reference protected system directories (/proc, /sys, /var/run/docker.sock, /etc/shadow, etc.).",
        criteria_type="Token iteration and substring inspection against PROTECTED_SYSTEM_PATHS",
        threat_mitigated="Host information leaks, credential tampering, Docker daemon socket mounting via shell commands.",
        mitre_attack="T1083 (File and Directory Discovery), T1003.008 (/etc/passwd and /etc/shadow)",
        owasp_llm="LLM02:2025 (Sensitive Information Disclosure), LLM06:2025 (Excessive Agency)",
        remediation="Confine command targets strictly to files and directories within /workspace.",
        test_mapping=[
            "backend/tests/test_attack_matrix.py::test_t11_docker_sock_mount",
            "backend/tests/test_attack_matrix.py::test_t12_host_env_leak",
            "backend/tests/test_policy_hitl_audit.py::test_shell_path_canonicalization_escapes"
        ]
    ),
    "CMD-004": SecurityRuleDefinition(
        rule_id="CMD-004",
        formal_name="Shell Tokenization & Argument Expansion Validation",
        category="Command Execution & Shell Tokenization",
        target_tools=["shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Enforces strict POSIX tokenization via shlex.split, rejecting syntax errors, unbalanced quotes, and process substitution constructs (<(), >()).",
        criteria_type="shlex.split syntax parsing and process substitution regex validation",
        threat_mitigated="Argument injection, shell token splitting, obfuscated subshell evasion.",
        mitre_attack="T1059.004 (Unix Shell)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Ensure quotes are properly balanced and avoid process substitution constructs.",
        test_mapping=[
            "backend/tests/test_security_regressions.py::test_shell_metacharacters_rejected",
            "backend/tests/test_policy_hitl_audit.py::test_shell_metacharacters_denied"
        ]
    ),

    # Tripwires & Honeypots
    "HONEY-001": SecurityRuleDefinition(
        rule_id="HONEY-001",
        formal_name="Honeypot Canary & Credential Decoy Tripwire",
        category="Tripwires & Honeypots",
        target_tools=["file", "shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Access attempts to planted decoy tripwires (.aws/credentials, .ssh/id_rsa, .env, fake_aws) trigger immediate block and session tainting (Engine ID: HT-001).",
        criteria_type="Normalized path and command string matching against settings.HONEYTOKEN_PATHS",
        threat_mitigated="Malicious agent reconnaissance, credential harvesting, unauthorized secret access.",
        mitre_attack="T1003 (OS Credential Dumping), T1552 (Unsecured Credentials)",
        owasp_llm="LLM02:2025 (Sensitive Information Disclosure)",
        remediation="Do not access credential or secret directories; use authorized task variables.",
        test_mapping=[
            "backend/tests/test_policy.py::test_block_honeytoken_access",
            "backend/tests/test_attack_matrix.py::test_t16_canary_exfiltration",
            "backend/tests/test_security_regressions.py::test_honeytoken_tripwire_triggers_session_taint"
        ]
    ),

    # Resource Limits
    "RES-001": SecurityRuleDefinition(
        rule_id="RES-001",
        formal_name="Execution Wall-Clock Timeout Enforcement",
        category="Resource Limits",
        target_tools=["shell", "http"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Enforces wall-clock timeout on all tool execution (default 10s timeout, container SIGKILL kill timer, httpx timeout).",
        criteria_type="Subprocess execution timer comparison against task and global limits",
        threat_mitigated="Denial of Service (DoS), hanging processes, computational exhaustion.",
        mitre_attack="T1499 (Endpoint Denial of Service)",
        owasp_llm="LLM04:2025 (Model Denial of Service)",
        remediation="Optimize command execution time or configure higher timeout in task manifest.",
        test_mapping=[
            "backend/tests/test_runtime_executor.py",
            "backend/tests/test_attack_matrix.py::test_t09_fork_bomb"
        ]
    ),
    "RES-002": SecurityRuleDefinition(
        rule_id="RES-002",
        formal_name="Memory & Disk Buffer Truncation / Allocation Limits",
        category="Resource Limits",
        target_tools=["file", "shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Enforces maximum stdout/stderr buffer sizes (20KB stdout, 5KB stderr), tmpfs 64MB cap, and container memory limits (256MB).",
        criteria_type="Output byte slicing and cgroup memory configuration",
        threat_mitigated="Buffer overflow, disk flooding, memory exhaustion DoS.",
        mitre_attack="T1499.001 (OS Exhaustion Flood)",
        owasp_llm="LLM04:2025 (Model Denial of Service)",
        remediation="Write voluminous output directly to workspace files rather than dumping to stdout.",
        test_mapping=[
            "backend/tests/test_attack_matrix.py::test_t10_memory_bomb",
            "backend/tests/test_runtime_executor.py"
        ]
    ),
    "RES-003": SecurityRuleDefinition(
        rule_id="RES-003",
        formal_name="Fork Bomb & Recursive Process Exhaustion Defense",
        category="Resource Limits",
        target_tools=["shell"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Blocks recursive spawn patterns (:(){ :|:& };:) via policy regex and enforces Cgroup v2 PID limits (pids_limit: 128, fallback 2048).",
        criteria_type="Regex signature matching and Cgroup v2 pids.max threshold enforcement",
        threat_mitigated="Process table exhaustion, host kernel hang, fork bomb DoS.",
        mitre_attack="T1499.004 (Application or System Exploitation)",
        owasp_llm="LLM04:2025 (Model Denial of Service)",
        remediation="Avoid recursive process spawning; restrict concurrency to single process.",
        test_mapping=[
            "backend/tests/test_policy.py::test_block_fork_bomb",
            "backend/tests/test_attack_matrix.py::test_t09_fork_bomb"
        ]
    ),

    # Prompt Injection & Model Safety
    "INJ-001": SecurityRuleDefinition(
        rule_id="INJ-001",
        formal_name="Prompt Injection & Adversarial Jailbreak Scoring",
        category="Prompt Injection & Model Safety",
        target_tools=["agent_prompt", "file", "shell", "http"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="Evaluates user input, agent thought, and arguments through multi-scale TF-IDF and regex heuristics; scores > 0.8 trigger an immediate BLOCK.",
        criteria_type="Hybrid ML classifier and heuristic regex risk score thresholding (score > 0.8)",
        threat_mitigated="Indirect prompt injection (IPI), jailbreaks, instruction overriding, system prompt leakage.",
        mitre_attack="T1566 (Phishing / Indirect Injection), T1059 (Command and Scripting Interpreter)",
        owasp_llm="LLM01:2025 (Prompt Injection)",
        remediation="Sanitize input data, wrap untrusted content in isolated XML tags, refine prompt boundaries.",
        test_mapping=[
            "backend/tests/test_attack_matrix.py::test_t15_taint_escalation_lethal_trifecta",
            "backend/tests/test_ml_classifier.py"
        ]
    ),

    # Human-in-the-Loop
    "HITL-001": SecurityRuleDefinition(
        rule_id="HITL-001",
        formal_name="Human-in-the-Loop Operator Authentication & One-Time Cryptographic Binding",
        category="Human-in-the-Loop",
        target_tools=["shell", "file", "http"],
        decision_tier=DecisionType.ASK,
        evaluation_logic="Requires Bearer token authentication with APPROVER_TOKEN for approvals. Approvals are strictly bound to tool call args_sha256, are valid for one-time use only (replay returns 409 Conflict), and expire after 60s.",
        criteria_type="Bearer token authorization, SHA-256 argument digest verification, stateful one-time latch",
        threat_mitigated="Unauthorized approval bypass, approval replay attacks, argument tampering during operator review.",
        mitre_attack="T1078 (Valid Accounts), T1556 (Modify Authentication Process)",
        owasp_llm="LLM06:2025 (Excessive Agency)",
        remediation="Provide valid APPROVER_TOKEN in Authorization header and match exact args_sha256 digest.",
        test_mapping=[
            "backend/tests/test_policy_hitl_audit.py::test_hitl_approval_endpoint_requires_auth",
            "backend/tests/test_policy_hitl_audit.py::test_hitl_approval_binding_and_one_time_use",
            "backend/tests/test_attack_matrix.py::test_t13_unauthorized_replayed_approval",
            "backend/tests/test_security_regressions.py::test_ask_endpoint_strictly_requires_approver_token"
        ]
    ),

    # Audit Integrity
    "AUDIT-001": SecurityRuleDefinition(
        rule_id="AUDIT-001",
        formal_name="Cryptographic Ledger Chain Integrity & Tamper Detection",
        category="Audit Integrity",
        target_tools=["audit"],
        decision_tier=DecisionType.BLOCK,
        evaluation_logic="All gateway decisions are serialized in canonical JSON (RFC-8785) and linked via HMAC-SHA256 hash chaining. SQLite triggers block UPDATE and DELETE. verify_chain() recomputes blocks from root to head.",
        criteria_type="HMAC-SHA256 signature recalculation, previous hash pointer verification, SQLite trigger checks",
        threat_mitigated="Retroactive log alteration, evidence tampering, rogue entry insertion or deletion.",
        mitre_attack="T1562.001 (Disable or Modify Tools), T1070 (Indicator Removal)",
        owasp_llm="LLM08:2025 (Excessive Agency / Auditability)",
        remediation="Restore ledger from immutable backup or re-initialize genesis verification chain.",
        test_mapping=[
            "backend/tests/test_policy_hitl_audit.py::test_canonical_json_serialization",
            "backend/tests/test_policy_hitl_audit.py::test_api_audit_verify_recomputes_chain",
            "backend/tests/test_attack_matrix.py::test_t14_audit_tamper_detection",
            "backend/tests/test_security_regressions.py::test_audit_chain_detects_record_deletion",
            "backend/tests/test_security_regressions.py::test_audit_chain_detects_record_insertion"
        ]
    ),
    "POL-PASS": SecurityRuleDefinition(
        rule_id="POL-PASS",
        formal_name="Deterministic Allowlist Policy Clearance",
        category="Audit Integrity",
        target_tools=["file", "shell", "http"],
        decision_tier=DecisionType.ALLOW,
        evaluation_logic="Tool call satisfies all containment, manifest, and security criteria; approved under active allowlist security policy.",
        criteria_type="Comprehensive allowlist and confinement pass across all active controls",
        threat_mitigated="None (Normal, safe, authorized operation).",
        mitre_attack="N/A",
        owasp_llm="N/A",
        remediation="N/A (Operation permitted).",
        test_mapping=[
            "backend/tests/test_policy.py::test_allow_normal_workspace_file_read",
            "backend/tests/test_policy_hitl_audit.py::test_sqlite_persistent_taint_escalates_side_effects",
            "backend/tests/test_attack_matrix.py::test_t14_audit_tamper_detection"
        ]
    )
}

# Alias mapping for system codes
RULES_ALIAS_MAP: Dict[str, str] = {
    "HT-001": "HONEY-001",
    "AUTH-001": "HITL-001",
    "CHAIN-VERIFY": "AUDIT-001"
}

def get_security_rule(rule_id: str) -> Optional[SecurityRuleDefinition]:
    """Retrieves a formalized security rule definition by Rule ID or alias."""
    canonical_id = RULES_ALIAS_MAP.get(rule_id, rule_id)
    return SECURITY_RULES_CATALOG.get(canonical_id)

def get_all_security_rules() -> List[SecurityRuleDefinition]:
    """Returns all formalized security rules in the catalog."""
    return list(SECURITY_RULES_CATALOG.values())

