from typing import Any, Tuple
from ..models import ToolCall, DecisionType, TaskManifest
from .manifests import get_manifest
from .rules import check_path_security, check_command_security, check_network_security
from ..inspector.content import content_inspector
from ..inspector.taint import taint_tracker

class PolicyEngine:
    def __init__(self):
        pass

    def evaluate(self, call: ToolCall) -> Tuple[DecisionType, str, str, float]:
        """
        Evaluates a tool call and returns:
            (DecisionType, reason, rule_id, risk_score)
        """
        try:
            manifest = get_manifest(call.task_id)

            # 1. Check tool authorization under task manifest (TOOL-001)
            if call.tool.value not in manifest.tools:
                return (
                    DecisionType.BLOCK,
                    f"Tool '{call.tool.value}' is not permitted for task '{manifest.task_id}'",
                    "TOOL-001",
                    0.9
                )

            # 2. Check call budget and rate limit (BUDGET-001)
            call_count = taint_tracker.record_call(call.agent_id)
            if call_count > manifest.max_calls:
                return (
                    DecisionType.BLOCK,
                    f"Call budget of {manifest.max_calls} exceeded for task '{manifest.task_id}'",
                    "BUDGET-001",
                    0.7
                )

            # 3. Pre-call Prompt Injection analysis on arguments (INJ-001 / INJ-002)
            args_text = " ".join(str(v) for v in call.args.values())
            inj_score, inj_reasons = content_inspector.score_prompt_injection(args_text)

            if inj_score > 0.8:
                return (
                    DecisionType.BLOCK,
                    f"Prompt injection detected in tool arguments (Score: {inj_score}): {'; '.join(inj_reasons)}",
                    "INJ-001",
                    inj_score
                )
            elif inj_score >= 0.5:
                return (
                    DecisionType.ASK,
                    f"Suspicious prompt pattern in tool arguments (Score: {inj_score}): {'; '.join(inj_reasons)}",
                    "INJ-002",
                    inj_score
                )

            # 4. Sequence & Taint Check - Lethal Trifecta (TAINT-001)
            is_outbound = (call.tool.value == "http") or (call.tool.value == "shell" and any(k in args_text for k in ("curl", "wget", "socket", "http")))
            is_lethal, lethal_reason = taint_tracker.check_lethal_trifecta(call.agent_id, is_outbound)
            if is_lethal:
                return (
                    DecisionType.BLOCK,
                    lethal_reason,
                    "TAINT-001",
                    0.95
                )

            # 5. Tool-specific security verification
            if call.tool.value == "file":
                path = call.args.get("path", "")
                op = call.args.get("op", "read")
                content = call.args.get("content", "")

                allowed, rule_id, reason = check_path_security(path, op, manifest)
                if not allowed:
                    return DecisionType.BLOCK, reason, rule_id, 0.85

                # If reading honeytoken or sensitive files, mark session
                if "secret" in path.lower() or "token" in path.lower():
                    taint_tracker.mark_sensitive_read(call.agent_id, f"File read: {path}")

            elif call.tool.value == "shell":
                cmd = call.args.get("cmd", "")
                allowed, rule_id, reason = check_command_security(cmd)
                if not allowed:
                    return DecisionType.BLOCK, reason, rule_id, 0.90

                # Also inspect for honeytoken references in shell command
                for ht in ["/.aws", "/.ssh", "/.env", "fake_aws"]:
                    if ht in cmd:
                        return (
                            DecisionType.BLOCK,
                            f"Shell command accesses honeytoken/credential target: '{ht}'",
                            "HT-001",
                            0.99
                        )

            elif call.tool.value == "http":
                url = call.args.get("url", "")
                allowed, rule_id, reason = check_network_security(url, manifest)
                if not allowed:
                    return DecisionType.BLOCK, reason, rule_id, 0.95

            # 6. All checks passed
            return DecisionType.ALLOW, "Tool call approved under active security policy", "POL-PASS", inj_score

        except Exception as e:
            # Fail-closed guarantee
            return (
                DecisionType.BLOCK,
                f"Fail-closed: Policy engine evaluation error: {str(e)}",
                "FAIL-CLOSED",
                1.0
            )

policy_engine = PolicyEngine()
