import pytest
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

from backend.app.runtime.executor import sandbox_executor, PinnedSyncBackend
from backend.app.config import settings
from backend.app.models import ToolResult


def test_shell_tool_safe_builtin_echo(tmp_path):
    res = sandbox_executor._execute_shell_tool(tmp_path, {"cmd": "echo 'Hello Sandbox'", "timeout": 5})
    assert isinstance(res, ToolResult)
    assert res.exit_code == 0
    assert "Hello Sandbox" in (res.stdout or "")


def test_shell_tool_safe_builtin_pwd(tmp_path):
    res = sandbox_executor._execute_shell_tool(tmp_path, {"cmd": "pwd", "timeout": 5})
    assert isinstance(res, ToolResult)
    assert res.exit_code == 0
    assert len(res.stdout or "") > 0


def test_shell_tool_missing_executable(tmp_path):
    res = sandbox_executor._execute_shell_tool(tmp_path, {"cmd": "non_existent_binary_xyz_9999", "timeout": 5})
    assert isinstance(res, ToolResult)
    assert res.exit_code == 127
    assert "ExecutableNotFound" in (res.error or "")


def test_shell_tool_timeout(tmp_path):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 10", timeout=1)):
        res = sandbox_executor._execute_shell_tool(tmp_path, {"cmd": "python -c 'import time; time.sleep(10)'", "timeout": 1})
        assert res.exit_code == 124
        assert res.error == "TimeoutExpired"


def test_shell_tool_docker_container_invocation(tmp_path):
    with patch.object(sandbox_executor, "_is_docker_sandbox_running", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Container execution ok"
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            res = sandbox_executor._execute_shell_tool(tmp_path, {"cmd": "uname -a", "timeout": 10})
            assert res.exit_code == 0
            assert "Container execution ok" in res.stdout

            # Verify docker exec call format and shell=False
            mock_run.assert_called_once()
            call_args, call_kwargs = mock_run.call_args
            assert call_kwargs.get("shell") is False
            expected_prefix = ["docker", "exec", "-i", "ps01-sandbox", "timeout", "-s", "KILL", "10", "bash", "-lc", "uname -a"]
            assert call_args[0] == expected_prefix


def test_shell_tool_truncates_output(tmp_path):
    giant_output = "A" * (settings.MAX_STDOUT_BYTES + 5000)
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = giant_output
        mock_proc.stderr = "B" * (settings.MAX_STDERR_BYTES + 2000)
        mock_run.return_value = mock_proc

        res = sandbox_executor._execute_shell_tool(tmp_path, {"cmd": "python -c 'print(1)'", "timeout": 5})
        assert len(res.stdout) == settings.MAX_STDOUT_BYTES
        assert len(res.stderr) == settings.MAX_STDERR_BYTES


def test_ssrf_rejects_disallowed_domain():
    res = sandbox_executor._execute_http_tool({"method": "GET", "url": "https://evil-attacker.com/leak"})
    assert res.status_code is None
    assert "SSRF Guard" in (res.error or "")
    assert "approved network allowlist" in (res.error or "")


def test_ssrf_rejects_cloud_metadata_ip():
    res = sandbox_executor._execute_http_tool({"method": "GET", "url": "http://169.254.169.254/latest/meta-data/"})
    assert res.status_code is None
    assert "SSRF Guard" in (res.error or "")


def test_ssrf_rejects_private_ips():
    for target in ["http://127.0.0.1:8000", "http://10.0.0.1:80", "http://192.168.1.50"]:
        res = sandbox_executor._execute_http_tool({"method": "GET", "url": target})
        assert res.status_code is None
        assert "SSRF Guard" in (res.error or "")


def test_ssrf_rejects_non_http_schemes():
    for target in ["file:///etc/passwd", "gopher://127.0.0.1:70", "ftp://pypi.org"]:
        res = sandbox_executor._execute_http_tool({"method": "GET", "url": target})
        assert res.status_code is None
        assert "SSRF Guard" in (res.error or "")


def test_ssrf_redirect_limit_exceeded():
    # Mock redirect responses looping > 3 hops
    with patch.object(sandbox_executor, "_validate_and_resolve_url", return_value=("https://pypi.org/loop", "pypi.org", 443, "151.101.0.223")):
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.headers = {"Location": "https://pypi.org/loop"}

        with patch("httpx.Client.request", return_value=mock_resp):
            res = sandbox_executor._execute_http_tool({"method": "GET", "url": "https://pypi.org/loop"})
            assert "Redirect hop limit exceeded" in (res.error or "")


def test_pinned_sync_backend_routing():
    backend = PinnedSyncBackend({"example.com": "93.184.216.34"})
    with patch("httpcore._backends.sync.SyncBackend.connect_tcp") as mock_connect:
        backend.connect_tcp("example.com", 443)
        mock_connect.assert_called_once_with(
            "93.184.216.34", 443, timeout=None, local_address=None, socket_options=None
        )
