# Agent Sandbox Escape Gauntlet — Host Gateway & Control Plane

The **Backend** is the central host control plane for the **Agent Sandbox Escape Gauntlet (PS01)**. It exposes an agent-neutral JSON tool broker, evaluates tool calls using a defense-in-depth policy gate, logs every action into a tamper-evident SHA-256 hash-chained SQLite ledger, and executes approved calls inside a hardened sandbox.

---

## 🏗️ Directory Layout

```text
backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment configuration & security limits
│   ├── models.py              # Pydantic schemas (ToolCall, GatewayResponse, AuditEntry)
│   ├── main.py                # FastAPI web server, REST endpoints & WebSocket feed
│   ├── gateway.py             # Central orchestrator (Policy -> Audit -> Sandbox -> Inspector)
│   ├── policy/
│   │   ├── __init__.py
│   │   ├── engine.py          # PolicyEngine: rule evaluation & precedence
│   │   ├── rules.py           # Path normalization, command AST parser, network allowlist, honeytokens
│   │   └── manifests.py       # Task capability manifests (N1–N5 + default)
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── ledger.py          # SQLite ledger with sequential SHA-256 hash chain & HMAC
│   │   └── verifier.py        # Cryptographic verifier to detect database tampering
│   ├── inspector/
│   │   ├── __init__.py
│   │   ├── content.py         # Secret redaction, prompt injection scoring & <untrusted> tagging
│   │   └── taint.py           # Session taint & lethal trifecta sequence tracking
│   └── runtime/
│       ├── __init__.py
│       └── executor.py        # SandboxExecutor: isolated execution & honeytoken bait management
├── tests/
│   ├── __init__.py
│   ├── test_policy.py         # Unit tests for policy security rules
│   ├── test_audit.py          # Cryptographic hash chain & tamper-detection tests
│   └── test_gateway.py        # Integration tests for /v1/tool & endpoints
├── requirements.txt           # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run the Host Gateway
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

### 3. Run Test Suite
```bash
python -m pytest backend/tests -v
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/tool` | Main Tool Execution Gateway (requires `X-Agent-Token` header) |
| `GET` | `/v1/audit` | Paginated query of the tamper-evident audit ledger |
| `GET` | `/v1/audit/verify` | Cryptographically verify SHA-256 hash chain from root to head |
| `GET` | `/v1/tasks` | List active task capability manifests (N1–N5) |
| `POST` | `/v1/ask/{audit_id}` | Operator approve/deny resolution for pending HITL requests |
| `WS` | `/ws` | Real-time WebSocket event stream for live monitoring dashboard |
| `GET` | `/health` | Gateway healthcheck & database status |

---

## 🛡️ Standard Tool Contract (`POST /v1/tool`)

### Request
```json
{
  "agent_id": "qwen-1",
  "task_id": "N1-code-summary",
  "tool": "file",
  "args": {
    "op": "read",
    "path": "/workspace/report.md"
  }
}
```

### Response
```json
{
  "decision": "allow",
  "reason": "Tool call approved under active security policy",
  "rule_id": "POL-PASS",
  "score": 0.0,
  "result": {
    "content": "<untrusted_content source=\"runtime:file\" prompt_guard_score=\"0.00\">\n# Project Report\n</untrusted_content>"
  },
  "audit_id": 1,
  "policy_hash": "v1-opa-rego-sha256-strict"
}
```

When an operation is **blocked** (e.g., path traversal or unauthorized network access):
```json
{
  "decision": "block",
  "reason": "Path '/etc/passwd' resolves outside /workspace boundary",
  "rule_id": "FS-001",
  "score": 0.85,
  "result": null,
  "audit_id": 2,
  "policy_hash": "v1-opa-rego-sha256-strict"
}
```
The agent observes the block reason as standard tool feedback and gracefully recovers without crashing.
