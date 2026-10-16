# Why Existing Solutions Fail Against PS01

PS01 states the key fact itself: **you cannot fully stop prompt injection inside the model.** Most existing defenses fail because they try to, or because they protect only one layer. This file explains each failure mode, the root cause, and how our design answers it.

---

## 1. The core failure: trusting the model to police itself

| Symptom | Root cause |
|---|---|
| Agent obeys instructions hidden in a file, webpage, or tool result | LLMs cannot reliably separate *instructions* from *data* in the same context window |
| "System prompt says never do X" is bypassed | Instructions are just more tokens; later or more persuasive text can override them |
| Defenses pass benchmarks, then fail in the wild | Static test sets; attackers adapt (encoding, role-play, multi-step, multilingual) |

Public research through 2025 repeatedly reported that detection-style defenses can be bypassed by adaptive attackers, often at high rates. Treat any model-based defense as probabilistic.

**Our answer:** the model is assumed compromised. The security boundary is built from kernel, network, and policy layers outside the model. The classifier (Prompt Guard 2) is a signal that can only make decisions *stricter*.

---

## 2. Failure catalogue

### F1. Prompt-level guardrails only
- **What it is:** system prompts, "ignore malicious instructions" warnings, delimiters around untrusted text.
- **Why it fails:** advisory, not enforced. One successful injection defeats it, and there is no second line of defense.
- **Our fix:** enforcement outside the model (gate + container + network). A fully hijacked agent still hits hard limits.

### F2. Injection classifiers as the main control
- **What it is:** Prompt Guard, Llama Guard, vendor "prompt shield" APIs used as a pass/fail filter.
- **Why it fails:** false negatives on obfuscated or novel payloads (base64, split across files, other languages); false positives on legitimate documents; latency and context-length limits on long inputs.
- **Our fix:** chunked scoring, preprocessing (decode, strip HTML), and the score only escalates `allow → ask → block`. Never the only gate.

### F3. Plain container sandboxing
- **What it is:** run the agent in Docker with a mounted folder.
- **Why it fails:** isolation without *judgment*. Inside the allowed folder and network, a hijacked agent can still read every secret mounted there and send it to any reachable host. No per-call decision, no reason, no visibility.
- **Our fix:** container + per-call policy gate + honeytokens + egress control, each with logged reasons.

### F4. Weak container configuration
- **What it is:** default Docker (root user, all default capabilities, writable root, docker.sock mounted, default network).
- **Why it fails:** known escape and abuse paths: privilege escalation, writing persistence into the image, reaching the cloud metadata endpoint, pivoting through the Docker socket.
- **Our fix:** read-only root, non-root, `cap-drop=ALL`, `no-new-privileges`, custom seccomp, internal network, no docker.sock.

### F5. Command blocklists and regex rules
- **What it is:** deny `rm -rf`, `curl`, `wget`, `cat ~/.aws/*`.
- **Why it fails:** trivially bypassed (`python -c`, `$(printf ...)`, base64 pipes, aliasing, `perl`, `/dev/tcp`). Also over-blocks legitimate work, so teams loosen rules until they're useless.
- **Our fix:** parse commands structurally, allowlist binaries, remove network tools from the image, and rely on the kernel/network layers when a rule is bypassed anyway.

### F6. Domain allowlists with no DNS or content control
- **What it is:** proxy blocks unknown domains, nothing else.
- **Why it fails:** DNS tunneling (`<secret>.allowed-or-attacker.com`) bypasses HTTP proxies; exfiltration via POST to an *allowed* site (paste/gist/code host, or an image URL with data in the query string); direct IP connections.
- **Our fix:** internal network with no default route, dnsmasq allowlist + entropy detector, method and body-size limits, outbound secret scan, metadata IP dropped at iptables.

### F7. Checking requests only, never results
- **What it is:** validate the tool call, trust whatever comes back.
- **Why it fails:** indirect injection arrives **in tool results** (a fetched page, a file's contents). The poisoned text goes straight into the model's context.
- **Our fix:** result inspector: scan, redact secrets, mark as untrusted, flag the session as tainted.

### F8. Stateless, per-call decisions
- **What it is:** each call judged in isolation.
- **Why it fails:** attacks are sequences. "Read secret" is fine; "HTTP POST to allowed host" is fine; together they are exfiltration. Often called the "lethal trifecta": private data + untrusted content + an outbound channel.
- **Our fix:** session taint tracking and sequence rules.

### F9. One global policy for every task
- **What it is:** a single allowlist for the whole agent.
- **Why it fails:** either too broad (a hijack can do anything any task may do) or too narrow (normal tasks break).
- **Our fix:** task capability manifests: each task declares paths, domains, tools, and call budget.

### F10. Human-in-the-loop for everything
- **What it is:** confirm every action.
- **Why it fails:** approval fatigue; users click "yes"; tasks become slow. Also fails open if the approver is absent.
- **Our fix:** `ask` only for medium-risk or tainted-and-sensitive actions; unanswered ask = deny.

### F11. Weak or editable audit trails
- **What it is:** plain text or database logs.
- **Why it fails:** an attacker (or insider) with write access can edit or delete entries. A bare hash chain can be recomputed from scratch. Network and kernel events live in separate, unlinked logs.
- **Our fix:** hash chain + HMAC with host-held key + anchored head + policy hash + network/seccomp/cgroup events in the same chain + `verify_chain` tamper demo.

### F12. Fail-open behavior
- **What it is:** if the policy engine or classifier errors, the call proceeds.
- **Why it fails:** an attacker only needs to crash or stall the checker.
- **Our fix:** engine error, classifier timeout, or unanswered ask all resolve to **deny**.

### F13. Resource abuse ignored
- **What it is:** no CPU, memory, process, or time limits.
- **Why it fails:** a hijacked agent can fork-bomb, mine, fill disk, or hang the host, a denial of service even if no data leaks.
- **Our fix:** cgroup limits, `pids-limit`, ulimits, tmpfs caps, subprocess timeouts, watchdog.

### F14. Framework lock-in
- **What it is:** a defense that works only inside one agent framework.
- **Why it fails:** teams switch frameworks; MCP and third-party agents bypass the protection entirely.
- **Our fix:** HTTP and MCP adapter; the sandbox is a tool broker any agent can call.

### F15. No measurement
- **What it is:** claims of safety without evidence.
- **Why it fails:** can't tell whether attacks are actually blocked or normal tasks actually work.
- **Our fix:** gauntlet harness with attack success rate, task success rate, false positives, and defenses ON vs OFF.

---

## 3. Publicly reported incident patterns

These illustrate the failure modes above (verify details against primary sources before citing in slides):

| Pattern | Typical mechanism | Failure mode it shows |
|---|---|---|
| Assistant exfiltrates data via rendered image/link | Injected text makes the model emit a URL containing secrets | F6, F7 |
| Zero-click injection through email or document | Poisoned content processed automatically; assistant leaks data | F1, F7, F8 |
| Tool-server (MCP) abuse | Malicious issue/page instructs the agent to use a legitimate tool with private repo access | F8, F9 |
| Coding agents running attacker commands | README or dependency text triggers shell execution | F3, F5 |

---

## 4. Summary table: failure → our countermeasure

| Failure | Our countermeasure |
|---|---|
| Model polices itself | Controls outside the model; classifier only escalates |
| Container without judgment | Host-side policy gate with reasons |
| Weak container config | ro root, non-root, caps dropped, seccomp |
| Bypassable command rules | Structural parsing + kernel/network backstop |
| DNS/allowed-domain exfil | dnsmasq allowlist, entropy detector, size/method limits |
| Results trusted | Result inspector + taint |
| Stateless decisions | Session state and sequence rules |
| One global policy | Task capability manifests |
| Approval fatigue | Selective ask, timeout = deny |
| Editable logs | HMAC hash chain with network events |
| Fail-open | Fail-closed everywhere |
| Resource abuse | cgroups, timeouts, watchdog |
| Framework lock-in | HTTP/MCP adapter |
| No evidence | Gauntlet scoreboard |

---

## 5. Honest limits of our approach

- Prompt Guard 2 remains bypassable; we never rely on it alone.
- Docker shares the host kernel; gVisor or a microVM would be stronger.
- Allowed domains still permit some low-bandwidth covert channels.
- Manifests must be scoped correctly by whoever writes them.
