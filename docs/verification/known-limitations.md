# sandboxX (PS01) — Known Limitations & Threat Model Boundary Disclosures

**System Designation:** `sandboxX` — Agent Sandbox Escape Gauntlet  
**Classification:** Security Architecture & Operational Disclosures  
**Author:** Application Security & Threat Modeling  
**Date:** 2026-10-16  

---

## 1. Purpose of this Document

In accordance with transparent security engineering, this document explicitly details the operational assumptions, known limitations, and trust boundaries of the `sandboxX` security platform. These disclosures ensure that operators, judges, and security auditors understand the precise capabilities and limits of the defense mechanisms.

---

## 2. Technical Limitations & Trust Boundary Disclosures

### 2.1 Docker Host Availability & Fallback Confinement
- **Limitation:** When `sandboxX` runs on a host machine where the Docker daemon is offline or uninstalled (e.g., standard non-containerized Windows dev workstations), the containerized kernel isolation (`ps01-sandbox`) cannot be engaged.
- **Defensive Behavior:** The system automatically falls back to the tokenized non-shell host execution runner (`shell=False`, process group isolation, output truncation, and workspace path containment).
- **Truthful Status:** The active probe endpoint (`GET /api/controls/status`) marks `Container Running`, `Non-Root & Read-Only Rootfs`, `Seccomp Profile`, and `Network Internal Isolation` as `"unverified"`. The system **never** displays fake green statuses when container isolation is not active.
- **Production Requirement:** For full production isolation, Docker Engine (with cgroups v2 and seccomp support) must be active and running `docker-compose up -d`.

### 2.2 Cryptographic Audit Chain & SQLite Storage Boundaries
- **Limitation:** SQLite triggers (`trg_audit_no_update` and `trg_audit_no_delete`) prevent SQL injection attacks and accidental application-level mutations. However, SQLite triggers do not protect the file against an attacker who gains direct OS-level root write access to the host disk where `audit.db` resides.
- **Threat Mitigation:**
  1. The container sandbox has **no mount access** to the host `audit.db` file or its directory.
  2. The `HMAC_SECRET_KEY` is held purely in host memory / host environment variables and is never exposed inside the container.
  3. `verify_audit_chain()` verifies cryptographic hash chain continuity independently of database triggers. Any offline deletion, insertion, or row modification is immediately detected upon verification.

### 2.3 Machine Learning (ML) Classifier Capabilities & Probabilistic Boundaries
- **Limitation:** The 3-tier Security ML Classifier (`ALLOW`, `ASK`, `BLOCK`) is a lightweight, calibrated probabilistic model trained on n-gram syntax and semantic markers. Like all machine learning models, it cannot provide 100% mathematical guarantees against novel, highly sophisticated, or multi-turn prompt obfuscations.
- **Asymmetric Safety Enforcement:**
  - The ML classifier operates solely as a **unidirectional escalation mechanism**: it can escalate a tool call from `ALLOW` to `ASK` or `BLOCK`, but it can **never** downgrade a policy denial to an allow.
  - Deterministic policy rules (`FS-001`, `FS-002`, `CMD-001`, `NET-003`, `NET-004`) evaluate before or independently of ML scoring.

### 2.4 Egress Proxy Inspection Scope
- **Limitation:** The Squid forward proxy enforces explicit domain allowlists (`pypi.org`, `github.com`, `huggingface.co`, etc.) and blocks non-allowlisted domains and direct IP addresses. For TLS/HTTPS connections, Squid filters based on SNI (Server Name Indication) and CONNECT domain handshakes without terminating TLS (no full MITM TLS decryption).
- **Consequence:** While an agent cannot connect to unapproved domains, traffic to approved domains (e.g., `github.com`) is encrypted end-to-end. Fine-grained URL path filtering on HTTPS destinations relies on the host gateway's pre-execution URL inspection before requests are dispatched.

### 2.5 Local LLM Service Availability (Ollama)
- **Limitation:** The Live Agent Workbench connects to a local Ollama instance serving `qwen3:4b`. If the Ollama service is stopped or the model is unloaded, the agent cannot generate tool calls.
- **Truthful Degradation:** The agent loop terminates gracefully and returns an explicit `model_offline` error. Fabricated responses or fake tool calls are strictly forbidden and were eliminated during WP8.

### 2.6 Windows vs. Linux Host Differences
- **Limitation:** Linux kernel namespaces, cgroups v2, and seccomp filters require a Linux host or Docker Desktop with WSL2 backend.
- **Defensive Behavior on Windows:** On native Windows without Docker, subprocesses use `CREATE_NEW_PROCESS_GROUP` and tokenized non-shell execution (`shell=False`) to prevent fork bombs and subshell execution. Full kernel containment requires running inside Docker containers as configured in `docker-compose.yml`.

---

## 3. Summary of Operational Assumptions

| Component | Minimum Operational Requirement | Fallback State |
|:---|:---|:---|
| **Host Gateway** | Python 3.11+ on Host | Required (Core Security Plane) |
| **Audit Ledger** | SQLite with Host HMAC Secret | Immutable append-only ledger |
| **Container Sandbox** | Docker Engine with cgroup v2 & seccomp | Tokenized host executor (probes unverified) |
| **Egress Proxy** | Squid & dnsmasq containers | Host SSRF Guard & IP Pinning |
| **Local LLM** | Ollama with `qwen3:4b` | Bounded error response (no fake fallback) |
| **Dashboard UI** | Node.js 20+ / Modern Web Browser | REST & WebSocket observability |
