import os
import json
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.models import ToolCall, ToolType, DecisionType
from backend.app.gateway import sandbox_gateway
from backend.app.policy.engine import policy_engine
from backend.app.policy.rules import check_command_security, canonicalize_and_verify_path
from backend.app.audit.ledger import AuditLedger, audit_ledger
from backend.app.audit.chain import canonical_json_dumps, compute_entry_hash, verify_audit_chain
from backend.app.inspector.taint import TaintTracker, taint_tracker

@pytest.fixture
def client():
    return TestClient(app)

# ------------------------------------------------------------------------------
# WP1 Tests: Safe HITL Approvals & Token Protection
# ------------------------------------------------------------------------------

def test_hitl_approval_endpoint_requires_auth(client):
    """Approval endpoints must return 401 Unauthorized without valid Bearer token."""
    payload = {
        "approval_id": "appr-fake-1",
        "decision": "allow",
        "approver": "admin"
    }
    # No header
    resp = client.post("/api/policy/approve", json=payload)
    assert resp.status_code == 401

    # Invalid token
    resp_bad = client.post(
        "/api/policy/approve",
        json=payload,
        headers={"Authorization": "Bearer bad-token-123"}
    )
    assert resp_bad.status_code == 401

@pytest.mark.anyio
async def test_hitl_approval_binding_and_one_time_use(client):
    """Approvals are bound to exact tool call args_sha256, one-time use, and recorded in audit ledger."""
    # Initiate an ASK call via gateway or simulate pending approval
    call = ToolCall(
        agent_id="test-hitl-agent",
        task_id="default-task",
        tool=ToolType.SHELL,
        args={"cmd": "touch /workspace/newfile.txt"}
    )

    # In policy engine, touch escalates to ASK tier
    dec, reason, rule_id, score = policy_engine.evaluate(call)
    assert dec == DecisionType.ASK

    # Register in gateway
    audit_entry = audit_ledger.append(
        session="test-hitl-agent",
        task="default-task",
        source="gateway",
        tool=call.tool.value,
        args=call.args,
        decision=dec.value,
        reason=reason,
        rule_id=rule_id,
        score=score
    )

    # Launch approval in background
    import asyncio
    asyncio.create_task(
        sandbox_gateway._await_human_approval(
            audit_id=audit_entry.id,
            session="test-hitl-agent",
            tool=call.tool.value,
            args=call.args,
            reason=reason,
            risk_score=score,
            timeout_sec=60.0
        )
    )

    # Give loop a tick to register ask
    await asyncio.sleep(0.05)

    pending_asks = sandbox_gateway.get_pending_asks()
    matching_ask = next((a for a in pending_asks if a["audit_id"] == audit_entry.id), None)
    assert matching_ask is not None
    approval_id = matching_ask["approval_id"]
    args_sha256 = matching_ask["args_sha256"]

    # 1. Attempt approval with wrong args_sha256: must be rejected with 400
    mismatch_resp = client.post(
        "/api/policy/approve",
        json={
            "approval_id": approval_id,
            "args_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "decision": "allow",
            "approver": "sec-ops"
        },
        headers={"Authorization": f"Bearer {settings.APPROVER_TOKEN}"}
    )
    assert mismatch_resp.status_code == 400
    assert "mismatch" in mismatch_resp.json()["detail"].lower()

    # 2. Valid approval with matching args_sha256: succeeds
    valid_resp = client.post(
        "/api/policy/approve",
        json={
            "approval_id": approval_id,
            "args_sha256": args_sha256,
            "decision": "allow",
            "approver": "sec-ops"
        },
        headers={"Authorization": f"Bearer {settings.APPROVER_TOKEN}"}
    )
    assert valid_resp.status_code == 200
    assert valid_resp.json()["ok"] is True
    assert valid_resp.json()["approved_by"] == "sec-ops"

    # 3. Replay attempt: must be rejected with 409 Conflict (one-time use)
    replay_resp = client.post(
        "/api/policy/approve",
        json={
            "approval_id": approval_id,
            "args_sha256": args_sha256,
            "decision": "allow",
            "approver": "sec-ops"
        },
        headers={"Authorization": f"Bearer {settings.APPROVER_TOKEN}"}
    )
    assert replay_resp.status_code == 409

    # 4. Verify approver was recorded in the immutable audit ledger
    latest_entries = audit_ledger.get_entries(limit=5)
    approver_entry = next((e for e in latest_entries if e.source == "hitl_approver"), None)
    assert approver_entry is not None
    assert "sec-ops" in approver_entry.reason

# ------------------------------------------------------------------------------
# WP4 Tests: Allowlist-First Policy & SQLite Persistent Taint Tracking
# ------------------------------------------------------------------------------

def test_shell_metacharacters_denied():
    """Shell commands containing chaining or command substitution metacharacters are rejected."""
    bad_cmds = [
        "ls -la; rm -rf /",
        "cat file.txt && whoami",
        "git status || echo fail",
        "echo `whoami`",
        "echo $(cat /etc/passwd)",
        "diff <(ls) <(ls -a)",
    ]
    for cmd in bad_cmds:
        decision, rule_id, reason = check_command_security(cmd)
        assert decision == DecisionType.BLOCK
        assert "CMD-001" in rule_id

def test_shell_path_canonicalization_escapes():
    """Shell commands with path arguments resolving outside /workspace are blocked."""
    escape_cmds = [
        "cat /etc/passwd",
        "tail /var/run/docker.sock",
        "ls /workspace/../../etc",
    ]
    for cmd in escape_cmds:
        decision, rule_id, reason = check_command_security(cmd)
        assert decision == DecisionType.BLOCK
        assert ("FS-001" in rule_id or "FS-002" in rule_id or "ESC-001" in rule_id or "CMD-003" in rule_id)

def test_sqlite_persistent_taint_escalates_side_effects(tmp_path: Path):
    """Session taint persists in SQLite and escalates side-effect calls to ASK."""
    db_file = tmp_path / "taint_test.db"
    tracker = TaintTracker(db_path=db_file)

    session_id = "taint-agent-01"
    assert tracker.is_session_tainted(session_id) is False

    # Mark untrusted context
    tracker.mark_untrusted_context(session_id, "Injected untrusted HTML content")
    assert tracker.is_session_tainted(session_id) is True

    # Re-instantiate tracker to prove persistence from SQLite
    tracker2 = TaintTracker(db_path=db_file)
    assert tracker2.is_session_tainted(session_id) is True

    # Taint the active global tracker for policy evaluation
    taint_tracker.mark_untrusted_context(session_id, "External untrusted ingest")

    # Read call (safe read)
    read_call = ToolCall(
        agent_id=session_id,
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/workspace/notes.txt"}
    )
    # Side-effect write call: must escalate from ALLOW to ASK
    write_call = ToolCall(
        agent_id=session_id,
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "write", "path": "/workspace/out.txt", "content": "data"}
    )
    dec_write, reason_write, rule_write, _ = policy_engine.evaluate(write_call)
    assert dec_write == DecisionType.ASK
    assert rule_write == "TAINT-ASK"

    # Reset session cleans up
    taint_tracker.reset_session(session_id)
    assert taint_tracker.is_session_tainted(session_id) is False

# ------------------------------------------------------------------------------
# WP6 Tests: Canonical JSON, HMAC-SHA256 & SQLite Triggers
# ------------------------------------------------------------------------------

def test_canonical_json_serialization():
    """Keys must be alphabetically sorted with compact separators and no whitespace variance."""
    obj = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
    canonical = canonical_json_dumps(obj)
    assert canonical == '{"a":2,"m":{"a":4,"b":3},"z":1}'

def test_api_audit_verify_recomputes_chain(client):
    """Endpoint /api/audit/verify recomputes chain and returns {ok, checked, first_bad_seq}."""
    resp = client.post("/api/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "ok" in data
    assert "checked" in data
    assert "first_bad_seq" in data
    assert data["ok"] is True
    assert data["first_bad_seq"] is None
