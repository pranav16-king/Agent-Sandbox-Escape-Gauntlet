from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

class ToolType(str, Enum):
    SHELL = "shell"
    FILE = "file"
    HTTP = "http"

class DecisionType(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    ASK = "ask"

class ShellArgs(BaseModel):
    cmd: str
    timeout: Optional[int] = 10

class FileArgs(BaseModel):
    op: str = Field(description="read | write | list")
    path: str
    content: Optional[str] = None

class HttpArgs(BaseModel):
    method: str = "GET"
    url: str
    body: Optional[str] = None

class ToolCall(BaseModel):
    agent_id: str = Field(default="agent-default", description="Identifier of the calling agent")
    task_id: str = Field(default="default-task", description="Identifier of the current task manifest")
    tool: ToolType = Field(description="shell | file | http")
    args: dict[str, Any] = Field(description="Tool arguments matching tool schema")

class ToolResult(BaseModel):
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    content: Optional[Any] = None
    status_code: Optional[int] = None
    body: Optional[str] = None
    execution_time_ms: Optional[float] = None
    error: Optional[str] = None

class GatewayResponse(BaseModel):
    decision: DecisionType
    reason: str
    rule_id: str
    score: float = 0.0
    result: Optional[dict[str, Any]] = None
    audit_id: int
    policy_hash: str

class AuditEntry(BaseModel):
    id: int
    ts: str
    session: str
    task: str
    source: str
    tool: str
    args: str
    decision: str
    reason: str
    rule_id: str
    score: float
    policy_hash: str
    prev_hash: str
    hash: str

class AskResolution(BaseModel):
    decision: DecisionType
    reason: str

class TaskManifest(BaseModel):
    task_id: str
    description: str
    tools: list[str]
    paths_read: list[str]
    paths_write: list[str]
    domains: list[str]
    max_calls: int = 25
    timeout_s: int = 60
