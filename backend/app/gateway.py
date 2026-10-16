import asyncio
from typing import Any, Optional

from .config import settings
from .models import ToolCall, DecisionType, GatewayResponse
from .policy.engine import policy_engine
from .audit.ledger import audit_ledger
from .runtime.executor import sandbox_executor
from .inspector.content import content_inspector
from .inspector.taint import taint_tracker

class SandboxGateway:
    def __init__(self):
        # Pending HITL (Human-In-The-Loop) asks: {audit_id: asyncio.Future}
        self.pending_asks: dict[int, asyncio.Future] = {}

    async def process_tool_call(self, call: ToolCall, session_id: Optional[str] = None) -> GatewayResponse:
        session = session_id or call.agent_id

        # 1. Evaluate Policy Gate
        decision, reason, rule_id, score = policy_engine.evaluate(call)

        # 2. Write-Ahead Audit Entry to Hash Chain
        audit_entry = audit_ledger.append(
            session=session,
            task=call.task_id,
            source="gateway",
            tool=call.tool.value,
            args=call.args,
            decision=decision.value,
            reason=reason,
            rule_id=rule_id,
            score=score,
            policy_hash=settings.POLICY_HASH,
            agent_thought=call.agent_thought,
            user_input=call.user_input
        )

        # 3. Handle ASK (Human In The Loop queue with timeout)
        if decision == DecisionType.ASK:
            resolved_decision, resolved_reason = await self._await_human_approval(audit_entry.id)
            decision = resolved_decision
            reason = resolved_reason

        # 4. If Blocked or Denied, return without executing
        if decision != DecisionType.ALLOW:
            return GatewayResponse(
                decision=decision,
                reason=reason,
                rule_id=rule_id,
                score=score,
                result=None,
                audit_id=audit_entry.id,
                policy_hash=settings.POLICY_HASH
            )

        # 5. Execute in Hardened Sandbox Runtime
        raw_result = sandbox_executor.run_in_container(session, call.tool.value, call.args)

        # 6. Result Inspection (Secrets Redaction, Untrusted Tagging, Taint Tracking)
        inspected_result = self._inspect_and_sanitize_result(session, call.tool.value, raw_result)

        return GatewayResponse(
            decision=DecisionType.ALLOW,
            reason=reason,
            rule_id=rule_id,
            score=score,
            result=inspected_result,
            audit_id=audit_entry.id,
            policy_hash=settings.POLICY_HASH
        )

    async def _await_human_approval(self, audit_id: int, timeout_sec: float = 3.0) -> tuple[DecisionType, str]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self.pending_asks[audit_id] = future

        try:
            # Wait for operator response or timeout (fail-closed)
            decision, reason = await asyncio.wait_for(future, timeout=timeout_sec)
            return decision, reason
        except asyncio.TimeoutError:
            # Fail-closed guarantee on unanswered ASK
            return DecisionType.BLOCK, "HITL operator approval timed out; request denied (fail-closed)"
        finally:
            self.pending_asks.pop(audit_id, None)

    def resolve_ask(self, audit_id: int, decision: DecisionType, reason: str) -> bool:
        if audit_id in self.pending_asks and not self.pending_asks[audit_id].done():
            self.pending_asks[audit_id].set_result((decision, reason))
            return True
        return False

    def _inspect_and_sanitize_result(self, session_id: str, tool: str, result: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(result)

        # Extract text content depending on tool
        target_keys = ["content", "stdout", "body"]
        for key in target_keys:
            if key in sanitized and isinstance(sanitized[key], str):
                text = sanitized[key]

                # Secret redaction
                redacted_text, redactions = content_inspector.redact_secrets(text)

                # Heuristic injection score on returned content
                inj_score, _ = content_inspector.score_prompt_injection(text)
                if inj_score >= 0.5:
                    taint_tracker.mark_untrusted_context(
                        session_id, 
                        f"Tool '{tool}' returned content with injection risk score {inj_score}"
                    )

                # Tag provenance
                tagged_text = content_inspector.tag_untrusted(redacted_text, source=f"runtime:{tool}", score=inj_score)
                sanitized[key] = tagged_text

        return sanitized

sandbox_gateway = SandboxGateway()
