import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.workspace import workspace_manager
from backend.app.policy.rules import check_path_security
from backend.app.policy.manifests import get_manifest

@pytest.fixture
def client():
    return TestClient(app)

def test_workspace_info_default():
    info = workspace_manager.get_workspace_info()
    assert info["is_valid"] is True
    assert "name" in info
    assert "path" in info
    assert isinstance(info["files"], list)
    assert info["file_count"] >= 1

def test_workspace_containment():
    # Inside workspace
    assert workspace_manager.is_inside_workspace("README.md") is True
    assert workspace_manager.is_inside_workspace("/workspace/README.md") is True

    # Escaping outside workspace
    assert workspace_manager.is_inside_workspace("/etc/passwd") is False
    assert workspace_manager.is_inside_workspace("/var/run/docker.sock") is False
    assert workspace_manager.is_inside_workspace("../../../Windows/System32/cmd.exe") is False
    assert workspace_manager.is_inside_workspace("C:/Windows/System32/cmd.exe") is False

def test_policy_enforces_workspace_containment():
    manifest = get_manifest("default-task")

    # Allowed inside workspace
    allowed, rule_id, reason = check_path_security("README.md", "read", manifest)
    assert allowed is True
    assert rule_id == "FS-PASS"

    # Blocked outside workspace
    allowed_esc, rule_id_esc, reason_esc = check_path_security("/etc/shadow", "read", manifest)
    assert allowed_esc is False
    assert rule_id_esc in ("FS-001", "HT-001")

def test_api_workspace_endpoints(client):
    # GET /api/workspace
    res = client.get("/api/workspace")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert "name" in data

    # POST /api/workspace with non-existent path
    err_res = client.post("/api/workspace", json={"path": "D:/invalid_non_existent_folder_9999"})
    assert err_res.status_code == 400

    # GET /api/workspace/browse
    browse_res = client.get("/api/workspace/browse")
    assert browse_res.status_code == 200
    browse_data = browse_res.json()
    assert "current_path" in browse_data
    assert "directories" in browse_data
