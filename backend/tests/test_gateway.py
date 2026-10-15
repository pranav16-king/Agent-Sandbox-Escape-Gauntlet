from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_unauthorized_tool_call_without_token():
    payload = {
        "agent_id": "test-agent",
        "task_id": "default-task",
        "tool": "file",
        "args": {"op": "read", "path": "/workspace/test.txt"}
    }
    response = client.post("/v1/tool", json=payload)
    assert response.status_code == 401

def test_allowed_file_write_and_read():
    token = settings.AGENT_AUTH_TOKEN
    headers = {"X-Agent-Token": token}

    # 1. Write file
    write_payload = {
        "agent_id": "integration-agent",
        "task_id": "default-task",
        "tool": "file",
        "args": {
            "op": "write",
            "path": "/workspace/hello.txt",
            "content": "Hello Sandbox World!"
        }
    }
    write_resp = client.post("/v1/tool", json=write_payload, headers=headers)
    assert write_resp.status_code == 200
    write_data = write_resp.json()
    assert write_data["decision"] == "allow"
    assert write_data["audit_id"] > 0

    # 2. Read file back
    read_payload = {
        "agent_id": "integration-agent",
        "task_id": "default-task",
        "tool": "file",
        "args": {
            "op": "read",
            "path": "/workspace/hello.txt"
        }
    }
    read_resp = client.post("/v1/tool", json=read_payload, headers=headers)
    assert read_resp.status_code == 200
    read_data = read_resp.json()
    assert read_data["decision"] == "allow"
    assert "Hello Sandbox World!" in read_data["result"]["content"]
    assert "<untrusted_content" in read_data["result"]["content"]

def test_blocked_path_traversal_tool_call():
    token = settings.AGENT_AUTH_TOKEN
    headers = {"X-Agent-Token": token}

    payload = {
        "agent_id": "attacker-agent",
        "task_id": "default-task",
        "tool": "file",
        "args": {
            "op": "read",
            "path": "/workspace/../../etc/passwd"
        }
    }
    response = client.post("/v1/tool", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "block"
    assert data["result"] is None
    assert "outside /workspace" in data["reason"] or "traversal" in data["reason"]

def test_audit_verify_endpoint():
    response = client.get("/v1/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["chain_valid"] is True
