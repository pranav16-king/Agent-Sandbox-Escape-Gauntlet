# PS01 PPT: Feasibility & Viability, Impact & Benefits, Research & References

I used current sources for the numbers. Anything marked **Target** is our own goal, to be proven by the gauntlet scoreboard. Anything marked **Plan** is our own build plan. Everything else is a published figure with a source.

---

# SLIDE 4: Feasibility & Viability

**Title:** *Buildable in a hackathon. Viable beyond it.*

### Feasibility (can we build it?)
- **100% open-source stack, ₹0 licensing:** Docker, Squid, dnsmasq, OPA, SQLite, FastAPI, Ollama.
- **Runs on one laptop:** Qwen3/Llama 3.1 at 4-bit, and Prompt Guard 2 is an 86M-parameter model, small enough to run alongside the agent.
- **8-step build; steps 1–8 are mandatory:** container, gateway, agent, policy gate, audit chain, egress proxy, normal tasks, attacks. Dashboard and extras come after.
- **Plan (time split):** sandbox + agent 25% · policy gate + audit 25% · egress 15% · gauntlet 20% · dashboard 10% · demo 5%.
- **Fallbacks ready:** Python rules if OPA is slow, Streamlit if React is slow.

### Viability (does it matter and last?)
- **Demand is growing fast:** Gartner expects 33% of enterprise software applications to include agentic AI by 2028, up from under 1% in 2024.
- **Security gap is real:** of organizations whose AI models or apps were breached, 97% had no AI access controls.
- **Agent-agnostic:** one HTTP/MCP gateway works with any agent framework, so adoption doesn't mean rewriting agents.
- **Upgrade path:** gVisor or Firecracker slot in behind the same executor; policy packs and audit export can become a product.
- **Business paths:** open-source core, with enterprise add-ons such as managed policy packs, compliance audit reports, and SIEM export.

### Risks and mitigations (one row each)
| Risk | Mitigation |
|---|---|
| Small model is flaky at tool calls | Scripted attack payloads, so demos are repeatable |
| Over-blocking breaks normal tasks | Task manifests + false-positive metric |
| Docker shares the host kernel | Seccomp, caps dropped; gVisor optional |

## Detailed explanation (speaker notes)

**Feasibility.** Judges will ask "can this be done in the time you have?" The answer is that nothing here is research. Each layer is a mature tool configured correctly: Docker flags for isolation, Squid and dnsmasq for network control, a rule engine for decisions, SQLite for the hash chain. Our contribution is the integration, and the order in which we build it matters. Steps 1–8 give a complete demo (contained attacks, completing tasks, a verifiable log), so even if the dashboard or extras slip, we still have a winning submission. The model side is light: an 8B model at 4-bit fits consumer hardware (roughly 5–6 GB, approximate), and the classifier is tiny by comparison.

**Viability.** Two facts frame the opportunity. Agents are moving into enterprise software quickly, and basic controls around them are missing. Gartner's forecast shows adoption; IBM's breach data shows the control gap. Gartner also warns that over 40% of agentic AI projects may be cancelled by end of 2027 due to cost, unclear value, or inadequate risk controls, so containment is part of what lets agent projects survive. Because our gateway is agent-agnostic, it fits whatever framework a team already uses, which is the main adoption blocker for security tooling.

**Talking point on risks:** state the Docker-kernel limitation yourself. Judges reward honesty, and it shows you know where gVisor fits.

---

# SLIDE 5: Impact & Benefits

**Title:** *Contain the damage, keep the productivity.*

### The problem in numbers
- **₹22 crore:** average cost of a data breach in India in 2025 (INR 220 million), 13% higher than 2024.
- **$4.44M global / $10.22M US:** average breach cost in 2025.
- **13%:** of organizations reported breaches of AI models or applications.
- **37%:** of Indian organizations have AI access controls in place, and nearly 60% lack fully developed AI governance policies.
- **+₹1.79 crore:** extra breach cost from shadow AI in India (INR 17.9 million).

### What our solution delivers
- **Target: 0 of 8** attack scenarios succeed with defenses ON (compared live with OFF).
- **Target: 5 of 5** normal tasks still complete.
- **Design: 2+ independent layers** stop every attack, so one bypass doesn't mean a breach.
- **100% of decisions explained:** every call logged with decision, reason, and rule ID.
- **Tamper-evident proof:** edit one log row and verification fails at that entry.

### Why layering works (published evidence)
- Meta's LlamaFirewall on the AgentDojo benchmark: attack success dropped from 17.6% to 7.5% with Prompt Guard 2 alone (a 57% drop), and to 1.75% combined (over 90% reduction).
- Trade-off to design around: task utility fell from 47.7% to 42.7%. Our task manifests aim to avoid that cost.

### Who benefits
- **Developers and students:** a ₹0, laptop-scale way to run agents safely.
- **Enterprises:** least-privilege agents, evidence for audits.
- **Security teams:** live visibility, replayable logs.

## Detailed explanation (speaker notes)

**Reading the numbers.** The ₹22 crore figure is an *average breach cost*, not a promise that our tool saves exactly that amount. Present it as "one contained incident is worth more than the whole project", which is a fair framing. The IBM India findings also say AI governance lags adoption, with only 37% having AI access controls, and that gap is exactly the control our gateway provides. The global number that stands out is that 97% of organizations with breached AI systems lacked access controls.

**Why we aren't relying on a classifier alone.** The LlamaFirewall result is encouraging and supports layered defense. But a 2025 study by researchers from several leading labs bypassed 12 recent defenses with attack success above 90% in most cases, while most of those defenses had originally reported near-zero success. That is why our design uses Prompt Guard 2 only as a signal that can tighten decisions, while hard limits (read-only filesystem, no network route, seccomp, allowlists) do the real work. This is also our strongest answer to "isn't this just a filter?"

**Real-world proof that the threat is serious.** In June 2025, a zero-click flaw in Microsoft 365 Copilot (EchoLeak) was assigned CVE-2025-32711 with a CVSS score of 9.3; it showed that a crafted email could lead to data exfiltration with no user action. Mention it in one line as proof that this is not hypothetical.

**Targets vs claims.** The 0/8 and 5/5 figures are targets that the live gauntlet will measure. Show the OFF run first so the ON run's contrast is real. Report false positives honestly; if one benign call gets blocked, say so and show the rule that caused it.

---

# SLIDE 6: Research & References

**Title:** *Grounded in current research and standards.*

### Key evidence (one line each)
- **#1 risk:** prompt injection remains the top risk in the OWASP Top 10 for LLM Applications (2025), alongside the new Excessive Agency category.
- **Layered defense works:** 17.6% → 1.75% attack success on AgentDojo (Meta LlamaFirewall).
- **Single filters break:** 12 defenses bypassed at over 90% success by adaptive attackers.
- **Real exploit:** EchoLeak, CVE-2025-32711, CVSS 9.3.
- **Cost of failure:** ₹22 crore average breach, India (IBM 2025).
- **Adoption wave:** 33% of enterprise apps with agentic AI by 2028 (Gartner).

### References
1. IBM, *Cost of a Data Breach Report 2025* (global release, 30 Jul 2025): newsroom.ibm.com
2. IBM India, *India Records Highest Average Cost of a Data Breach at INR 220 Million*, 7 Aug 2025: in.newsroom.ibm.com
3. S. Chennabasappa et al. (Meta), *LlamaFirewall: An open source guardrail system for building secure AI agents*, arXiv:2505.03574, 2025.
4. M. Nasr, N. Carlini, et al., *The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against LLM Jailbreaks and Prompt Injections*, arXiv:2510.09023, Oct 2025.
5. Aim Security / Microsoft, *EchoLeak*, CVE-2025-32711, June 2025 (reported by The Hacker News, 12 Jun 2025).
6. OWASP GenAI Security Project, *OWASP Top 10 for LLM Applications 2025* (v2.0, Nov 2024).
7. Gartner, press release on agentic AI project cancellations and adoption forecasts, 2025.
8. Meta, *Llama Prompt Guard 2* model card.
9. E. Debenedetti et al., *AgentDojo* benchmark for agent prompt-injection robustness (NeurIPS 2024 datasets track), and *Defeating Prompt Injections by Design* (CaMeL), arXiv:2503.18813, 2025.
10. Docker security docs (seccomp, capabilities, rootless/read-only), Open Policy Agent docs, Squid and dnsmasq docs.

## Detailed explanation (speaker notes)

**Why these sources.** Each reference supports one claim in the deck: IBM for the cost and governance gap, OWASP for the threat classification, LlamaFirewall for layered-defense evidence, the adaptive-attack paper for why classifiers can't be the boundary, and EchoLeak for a real exploit. This mapping makes the slide convincing in under a minute: threat, cost, evidence, limits, our design.

**Be careful in Q&A with these points:**
- LlamaFirewall's numbers come from the authors' own AgentDojo evaluation. They are not a guarantee for our system, which is why we run our own gauntlet.
- Gartner's cancellation figure is a forecast, not an observed result.
- I excluded the India breach-lifecycle figure because two outlets reported different numbers (263 vs 292 days); the IBM release says 263 days. Use it only if you cite IBM directly.
- References 7–10 are standard sources I listed from general knowledge rather than re-checking this session. Open each link once before printing the slide.

**Suggested one-sentence close for slides 4–6:** *"The research says no single filter holds under attack, the data says the control gap is costly, and our design answers both with layers that don't depend on trusting the model."*
