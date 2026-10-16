from datetime import datetime, timezone
import json
from typing import Any, Callable, Optional

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
        self.pending_ask_details: dict[int, dict[str, Any]] = {}
        # Real observed network activity ring buffer
        self.network_events: list[dict[str, Any]] = []
        self._listeners: list[Callable[[str, dict[str, Any]], None]] = []

    def register_listener(self, callback: Callable[[str, dict[str, Any]], None]):
        self._listeners.append(callback)

    def _notify(self, event_type: str, data: dict[str, Any]):
        for listener in list(self._listeners):
            try:
                listener(event_type, data)
            except Exception:
                pass

    def record_network_event(self, event_type: str, target: str, action: str, rule_id: str):
        evt = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "target": target,
            "action": action,
            "rule_id": rule_id
        }
        self.network_events.insert(0, evt)
        if len(self.network_events) > 100:
            self.network_events.pop()
        self._notify("network", evt)

    def get_network_events(self) -> list[dict[str, Any]]:
        return list(self.network_events)

    def get_pending_asks(self) -> list[dict[str, Any]]:
        return list(self.pending_ask_details.values())

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

        # 3. Track Real Network Activity
        if call.tool.value == "http":
            url = call.args.get("url", "")
            action = "allow" if decision == DecisionType.ALLOW else "block"
            self.record_network_event("HTTP", url, action, rule_id)
        elif call.tool.value == "shell":
            cmd = call.args.get("cmd", "")
            if any(k in cmd.lower() for k in ("curl", "wget", "http://", "https://", "/dev/tcp", "socket")):
                action = "allow" if decision == DecisionType.ALLOW else "block"
                target = cmd.split()[1] if len(cmd.split()) > 1 else cmd[:60]
                self.record_network_event("HTTP", target, action, rule_id)

        # 4. Handle ASK (Human In The Loop queue with timeout)
        if decision == DecisionType.ASK:
            resolved_decision, resolved_reason = await self._await_human_approval(
                audit_id=audit_entry.id,
                tool=call.tool.value,
                args=json.dumps(call.args),
                reason=reason,
                risk_score=score
            )
            decision = resolved_decision
            reason = resolved_reason

        # 5. If Blocked or Denied, return without executing
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

        # 6. Execute in Hardened Sandbox Runtime
        raw_result = sandbox_executor.run_in_container(session, call.tool.value, call.args)

        # 7. Result Inspection (Secrets Redaction, Untrusted Tagging, Taint Tracking)
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

    async def _await_human_approval(
        self,
        audit_id: int,
        tool: str,
        args: str,
        reason: str,
        risk_score: float,
        timeout_sec: float = 30.0
    ) -> tuple[DecisionType, str]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self.pending_asks[audit_id] = future

        expires_at_iso = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + timeout_sec,
            timezone.utc
        ).isoformat()

        ask_data = {
            "audit_id": audit_id,
            "tool": tool,
            "args": args,
            "reason": reason,
            "risk_score": risk_score,
            "expires_at": expires_at_iso
        }
        self.pending_ask_details[audit_id] = ask_data
        self._notify("ask_request", ask_data)

        try:
            # Wait for operator response or timeout (fail-closed)
            decision, res_reason = await asyncio.wait_for(future, timeout=timeout_sec)
            self._notify("ask_resolved", {
                "audit_id": audit_id,
                "outcome": "approved" if decision == DecisionType.ALLOW else "denied"
            })
            return decision, res_reason
        except asyncio.TimeoutError:
            self._notify("ask_resolved", {
                "audit_id": audit_id,
                "outcome": "timeout"
            })
            return DecisionType.BLOCK, "HITL operator approval timed out; request denied (fail-closed)"
        finally:
            self.pending_asks.pop(audit_id, None)
            self.pending_ask_details.pop(audit_id, None)

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
