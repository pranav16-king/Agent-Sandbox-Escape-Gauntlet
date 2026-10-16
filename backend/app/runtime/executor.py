import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional
import httpx

from ..config import settings
from ..models import ToolResult
from ..workspace import workspace_manager

class SandboxExecutor:
    def __init__(self):
        self.sessions_dir = settings.SESSIONS_DIR

    def get_session_workspace(self, session_id: str) -> Path:
        """
        Retrieves or initializes an isolated local /workspace directory for the session.
        """
        workspace = self.sessions_dir / session_id / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Plant honeytoken bait in fake user home for demonstration
        fake_home = self.sessions_dir / session_id / "home" / "sandbox" / ".aws"
        fake_home.mkdir(parents=True, exist_ok=True)
        fake_cred_file = fake_home / "credentials"
        if not fake_cred_file.exists():
            fake_cred_file.write_text(
                "[default]\n"
                "aws_access_key_id = AKIAHONEYTOKENGAUNTLET99\n"
                "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n",
                encoding="utf-8"
            )

        return workspace

    def run_in_container(self, session_id: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Dispatches tool call to container or isolated runtime.
        """
        workspace = self.get_session_workspace(session_id)
        start_time = time.time()

        if tool == "file":
            res = self._execute_file_tool(workspace, args)
        elif tool == "shell":
            res = self._execute_shell_tool(workspace, args)
        elif tool == "http":
            res = self._execute_http_tool(args)
        else:
            res = ToolResult(error=f"Unsupported tool: {tool}")

        res.execution_time_ms = round((time.time() - start_time) * 1000, 2)
        return res.model_dump(exclude_none=True)

    def _execute_file_tool(self, workspace: Path, args: dict[str, Any]) -> ToolResult:
        op = args.get("op", "read")
        raw_path = args.get("path", "")
        content = args.get("content", "")

        # First attempt resolution within the active project workspace
        target_path = workspace_manager.resolve_workspace_file(raw_path)

        # If not matched against active project workspace, try session workspace fallback
        if target_path is None:
            rel_path = raw_path.replace("/workspace", "").lstrip("/").lstrip("\\")
            candidate = (workspace / rel_path).resolve()
            try:
                candidate.relative_to(workspace.resolve())
                target_path = candidate
            except ValueError:
                return ToolResult(
                    error=f"Kernel boundary violation: Resolved path '{raw_path}' escapes active project workspace mount ({workspace_manager.current_path.name})."
                )

        try:
            if op == "read":
                if not target_path.exists():
                    return ToolResult(error=f"File not found: {raw_path}")
                data = target_path.read_text(encoding="utf-8", errors="replace")
                return ToolResult(content=data)

            elif op == "write":
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                return ToolResult(content=f"Successfully wrote {len(content)} bytes to {raw_path}")

            elif op == "list":
                if not target_path.exists():
                    return ToolResult(error=f"Directory not found: {raw_path}")
                items = [p.name for p in target_path.iterdir()]
                return ToolResult(content=items)

            else:
                return ToolResult(error=f"Unknown file operation: {op}")

        except Exception as e:
            return ToolResult(error=f"Filesystem error: {str(e)}")

    def _execute_shell_tool(self, workspace: Path, args: dict[str, Any]) -> ToolResult:
        cmd = args.get("cmd", "")
        timeout = args.get("timeout", settings.DEFAULT_TIMEOUT_SEC)

        # Execute subprocess strictly within active project workspace directory
        exec_dir = workspace_manager.current_path if workspace_manager.current_path.exists() else workspace

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(exec_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            stdout = proc.stdout[:settings.MAX_STDOUT_BYTES]
            stderr = proc.stderr[:settings.MAX_STDERR_BYTES]

            return ToolResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                exit_code=124,
                error="TimeoutExpired"
            )
        except Exception as e:
            return ToolResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                error=f"Subprocess error: {str(e)}"
            )

    def _execute_http_tool(self, args: dict[str, Any]) -> ToolResult:
        method = args.get("method", "GET").upper()
        url = args.get("url", "")
        body = args.get("body", None)

        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.request(method=method, url=url, content=body)
                truncated_text = resp.text[:settings.MAX_STDOUT_BYTES]
                return ToolResult(
                    status_code=resp.status_code,
                    body=truncated_text
                )
        except Exception as e:
            return ToolResult(
                error=f"HTTP request failed: {str(e)}"
            )

    def cleanup_session(self, session_id: str):
        session_folder = self.sessions_dir / session_id
        if session_folder.exists():
            shutil.rmtree(session_folder, ignore_errors=True)

sandbox_executor = SandboxExecutor()
