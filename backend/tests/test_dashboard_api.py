import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

@pytest.fixture
def client():
    return TestClient(app)

def test_get_dashboard_snapshot(client):
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    assert "recent_logs" in data
    assert "resources" in data
    assert "chain" in data
    assert "system" in data
    assert "scenarios" in data
    assert data["system"]["sandbox"] == "on"

def test_get_scenarios(client):
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8
    attack_ids = [s["id"] for s in data if s["kind"] == "attack"]
    assert "atk-passwd" in attack_ids
    assert "atk-revshell" in attack_ids

def test_api_run_attack_scenario_blocked(client):
    response = client.post("/api/scenarios/atk-passwd/run")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["decision"] == "block"

def test_api_run_normal_task_allowed(client):
    response = client.post("/api/scenarios/norm-git/run")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["decision"] == "allow"

def test_api_audit_verify(client):
    response = client.post("/api/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert "ok" in data
    assert "head_hash" in data

def test_api_policy(client):
    response = client.get("/api/policy")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert "egress_domains" in data
    assert "api.openai.com" in data["egress_domains"]

def test_api_audit_clear(client):
    response = client.post("/api/audit/clear")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True

    # Verify snapshot shows 0 logs and 0 entries in chain
    snapshot = client.get("/api/snapshot").json()
    assert snapshot["counts"]["total"] == 0
    assert len(snapshot["recent_logs"]) == 0
    assert snapshot["chain"]["entries"] == 0

def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_post_audit(client):
    payload = {
        "session": "test-session",
        "task": "probe",
        "source": "automated-probe",
        "tool": "file",
        "args": {"path": "test.txt"},
        "decision": "allow",
        "reason": "Test audit probe"
    }
    response = client.post("/api/audit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["entry"]["session"] == "test-session"

