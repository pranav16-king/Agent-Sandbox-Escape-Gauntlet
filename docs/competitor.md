# Competitor and Alternative Analysis: PS01 Agent Sandbox

> **Verification note:** this analysis is written from general knowledge of the agent-security landscape. Products change quickly (features, pricing, acquisitions). Check each vendor's current docs before quoting specifics in a pitch, and treat the "gap" column as our positioning, not a verified claim about any company.

---

## 1. Landscape map

Solutions for "agent does something dangerous" fall into five categories. None covers all PS01 requirements together.

| Category | Examples | What they protect |
|---|---|---|
| A. Execution sandboxes | Docker/Podman, gVisor, Firecracker/Kata microVMs, E2B, Modal, Daytona-style cloud sandboxes | Where code runs (isolation) |
| B. Injection and content guardrails | Meta Llama Prompt Guard 2 / Llama Guard, LlamaFirewall, NVIDIA NeMo Guardrails, Lakera Guard, vendor prompt-shield APIs, Rebuff-style detectors | What text goes into/out of the model |
| C. Policy and guardrail frameworks for agents | Invariant-style guardrail rules and MCP scanners, Open Policy Agent, cloud guardrail services (e.g. Bedrock Guardrails) | Which actions are allowed |
| D. Design-level research | CaMeL-style capability/data-flow separation, "dual LLM" and plan-then-execute patterns | Architecture that limits injection impact |
| E. Built-in agent sandboxes | Sandboxing in coding-agent products (OS-level file and network restrictions, network-off-by-default cloud runners) | Local or cloud agent runs |

---

## 2. Comparison against PS01 requirements

Legend: ● strong, ◐ partial, ○ absent or not the focus.

| Capability | A. Exec sandbox | B. Guardrails / classifiers | C. Policy frameworks | D. Design research | E. Built-in agent sandbox | **Ours** |
|---|---|---|---|---|---|---|
| Isolated runtime limited to `/workspace` | ● | ○ | ○ | ○ | ● | ● |
| Network allowlist with logging | ◐ | ○ | ○ | ○ | ◐ | ● |
| DNS exfiltration control | ○ | ○ | ○ | ○ | ○ | ● |
| Per-call allow/block/ask with reason | ○ | ◐ | ● | ◐ | ◐ | ● |
| Injection detection signal | ○ | ● | ◐ | ○ | ○ | ● (as signal only) |
| Result inspection and redaction | ○ | ◐ | ◐ | ● | ○ | ● |
| Session taint / sequence rules | ○ | ○ | ◐ | ● | ○ | ● |
| Task-scoped permissions | ○ | ○ | ◐ | ● | ◐ | ● |
| Resource limits | ● | ○ | ○ | ○ | ◐ | ● |
| Tamper-evident audit chain | ○ | ○ | ◐ | ○ | ○ | ● |
| Live dashboard | ◐ | ◐ | ◐ | ○ | ○ | ● |
| Works with any agent framework | ● | ◐ | ◐ | ○ | ○ | ● (HTTP/MCP) |
| Built-in attack/normal-task benchmark | ○ | ◐ | ○ | ◐ | ○ | ● |
| Self-hostable, open-weight, runs offline | ◐ | ◐ | ● | ● | ◐ | ● |

---

## 3. Competitor-by-competitor notes

### A. Execution sandboxes (Docker, gVisor, Firecracker, E2B, Modal, etc.)
- **Strengths:** strong isolation; mature; microVMs and gVisor give stronger kernel separation than plain Docker.
- **Gaps for PS01:** isolation without per-call judgment, reasons, taint, or audit. Network policy is usually coarse, and DNS exfiltration and honeytokens are not part of the product.
- **How we position:** *we use the same primitives (Docker, seccomp, optionally gVisor) and add the decision, inspection, and audit layers they leave to the user.*

### B. Injection and content guardrails (Prompt Guard 2, Llama Guard, LlamaFirewall, NeMo Guardrails, Lakera, etc.)
- **Strengths:** good first-pass detection; easy to integrate; some include agent-alignment or code-scanning checks.
- **Gaps for PS01:** probabilistic, so a single bypass defeats a pass/fail design. They do not isolate execution, control the network, or give tamper-evident logs. Typically they inspect text, not OS-level actions.
- **How we position:** *we consume the classifier as one input that can only tighten decisions; the guarantee comes from layers that don't depend on it.*

### C. Policy and guardrail frameworks (OPA, Invariant-style rules, cloud guardrails)
- **Strengths:** expressive, auditable rules; good fit for allow/deny logic; OPA is battle-tested.
- **Gaps for PS01:** they decide but don't contain: no container, proxy, or resource enforcement. Rules are usually stateless unless you build session state yourself.
- **How we position:** *we use OPA/Rego (or Python) as the engine, but wire it to a real sandbox, taint state, task manifests, and a hash-chained log.*

### D. Design-level research (CaMeL-style capability and data-flow control, dual-LLM patterns)
- **Strengths:** the most principled answer: separate trusted planning from untrusted data so injected text cannot trigger privileged actions, with provable-style guarantees in some designs.
- **Gaps for PS01:** research prototypes; require restructuring how the agent works (not drop-in for arbitrary agents); don't provide OS/network isolation or dashboards.
- **How we position:** *we borrow the idea (capabilities, taint, task-scoped permissions) but enforce it at a tool-broker boundary that works with any existing agent.*

### E. Built-in agent sandboxes (coding-agent products and cloud runners)
- **Strengths:** convenient, well-engineered OS-level restrictions; network allow/deny controls; proven at scale.
- **Gaps for PS01:** tied to one product; policy and logs are not exposed as a framework you can inspect; no tamper-evident chain or scenario scoreboard you control.
- **How we position:** *an open, inspectable, agent-agnostic equivalent with a measurable gauntlet.*

---

## 4. Our differentiators (what judges should remember)

1. **Defense in depth, no single point of failure:** every attack maps to at least two independent layers.
2. **Classifier-as-signal:** Prompt Guard can only escalate; hard limits do the real work.
3. **Task capability manifests:** least privilege per task, not per agent.
4. **Taint and sequence rules:** catches "read secret then send out" even when each step looks harmless.
5. **Bidirectional inspection:** results are scanned before the model sees them.
6. **Honeytokens:** deterministic credential-theft detection with a clear demo moment.
7. **DNS and egress depth:** dnsmasq allowlist, entropy detection, size/method limits, metadata IP drop.
8. **Tamper-evident audit that includes network and kernel events,** with a live tamper demo.
9. **Agent-agnostic via HTTP/MCP,** shown working with more than one agent.
10. **Measured results:** attack success rate, task success rate, false positives, defenses ON vs OFF.

---

## 5. Objections judges may raise, and answers

| Objection | Answer |
|---|---|
| "Why not just use gVisor or a microVM?" | Great upgrade (we list it as optional). It adds isolation but not decisions, reasons, taint, or audit. Our gate sits on top of any runtime. |
| "Prompt Guard is bypassable." | Agreed. That's why it can only escalate and is never the boundary. |
| "Won't this block normal tasks?" | The gauntlet's normal-task suite and false-positive metric measure exactly that, and manifests keep rules narrow per task. |
| "Isn't a regex/AST command check bypassable?" | Yes, so it's backed by a read-only root, removed network binaries, an internal network, and seccomp. |
| "What about a malicious allowed domain?" | Method and body-size limits, outbound secret scan, and taint rules reduce risk; we state the residual risk openly. |
| "Why Docker, not a microVM?" | Hackathon time and hardware; the design is runtime-agnostic and gVisor/Firecracker slot in behind the same executor. |

---

## 6. Positioning statement

> Existing tools either **contain** (sandboxes), **detect** (classifiers), or **decide** (policy engines), but rarely all three, and almost none **prove** what happened. Our solution combines containment, detection, decision, and tamper-evident proof behind one agent-agnostic tool broker, and measures the result with a built-in attack gauntlet.

---

## 7. Follow-up to-do before presenting

- [ ] Verify current features of 2–3 named competitors from their official docs and cite them.
- [ ] Replace this table's qualitative marks with tested results from your own gauntlet where possible.
- [ ] Add one slide: "Layers, not a silver bullet", mapping each attack to two layers.
