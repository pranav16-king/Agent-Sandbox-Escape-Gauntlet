import json
import asyncio
from typing import Any, Optional
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import ToolCall, GatewayResponse, AskResolution
from .gateway import sandbox_gateway
from .audit.ledger import audit_ledger
from .audit.verifier import verify_chain
from .policy.manifests import TASK_MANIFESTS

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="PS01 — Agent Sandbox Escape Gauntlet Host Gateway & Policy Enforcement Plane"
)

# Enable CORS for dashboard UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections for live dashboard
active_connections: list[WebSocket] = []

def ws_broadcaster(event_data: dict[str, Any]):
    """
    Called by audit_ledger whenever a new entry is appended.
    """
    if not active_connections:
        return

    # Broadcast event asynchronously across connections
    message = json.dumps(event_data)
    for ws in list(active_connections):
        try:
            asyncio.create_task(ws.send_text(message))
        except Exception:
            pass

# Register the broadcaster with the audit ledger
audit_ledger.register_listener(ws_broadcaster)

@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "active",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": settings.AUDIT_DB_PATH.exists(),
        "total_audit_records": len(audit_ledger.get_entries(limit=1)),
        "policy_hash": settings.POLICY_HASH
    }

@app.post("/v1/tool", response_model=GatewayResponse)
async def execute_tool(
    call: ToolCall,
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")
):
    """
    Unified Tool Gateway endpoint. All agent tool calls must pass through this endpoint.
    """
    # 1. Authenticate agent token
    if x_agent_token != settings.AGENT_AUTH_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized agent: Invalid or missing X-Agent-Token header"
        )

    # 2. Process tool call through sandbox gateway
    response = await sandbox_gateway.process_tool_call(call)
    return response

@app.get("/v1/audit")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Fetches paginated records from the tamper-evident audit ledger.
    """
    entries = audit_ledger.get_entries(limit=limit, offset=offset)
    return {
        "total": len(entries),
        "limit": limit,
        "offset": offset,
        "entries": [e.model_dump() for e in entries]
    }

@app.get("/v1/audit/verify")
def verify_audit_chain():
    """
    Cryptographically verifies the SHA-256 hash chain from root to head.
    Detects any database tampering or retroactive modification.
    """
    is_valid, broken_id, message = verify_chain()
    return {
        "chain_valid": is_valid,
        "broken_entry_id": broken_id,
        "message": message
    }

@app.get("/v1/tasks")
def list_tasks():
    """
    Returns available task capability manifests.
    """
    return {
        "tasks": {k: v.model_dump() for k, v in TASK_MANIFESTS.items()}
    }

@app.post("/v1/ask/{audit_id}")
def resolve_operator_ask(audit_id: int, resolution: AskResolution):
    """
    Resolves a pending Human-in-the-Loop (HITL) ASK request.
    """
    success = sandbox_gateway.resolve_ask(audit_id, resolution.decision, resolution.reason)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Pending ask for audit_id {audit_id} not found or already timed out"
        )
    return {"status": "resolved", "audit_id": audit_id, "decision": resolution.decision}

@app.websocket("/ws")
async def websocket_dashboard(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for the live dashboard.
    Streams every tool call, policy decision, and audit record in real time.
    """
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Keep connection open and receive optional ping/pong
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)
