"""
sandboxX Security Pipeline Engine (PS01 Agent Sandbox Escape Gauntlet).

Modular 7-Stage Execution Pipeline:
  Stage 1: Normalization & Pre-Call Analysis
  Stage 2: Deterministic Policy & Prompt Guard Evaluation
  Stage 3: Write-Ahead Tamper-Evident Hash Chaining
  Stage 4: Token-Authenticated HITL Approvals with Call Hash Binding & 60s Expiry
  Stage 5: Hardened Container Runtime Execution (ps01-sandbox)
  Stage 6: Return-Path Content Sanitization & Secret Redaction
  Stage 7: Provenance Tainting & Live Telemetry Broadcasting
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Dict
from pydantic import BaseModel

from ..config import settings
from ..models import ToolCall, DecisionType, GatewayResponse
from ..policy.engine import policy_engine
from ..audit.ledger import audit_ledger
from ..audit.chain import canonical_json_dumps
from ..runtime.executor import sandbox_executor
from ..inspector.content import content_inspector
from ..inspector.taint import taint_tracker

class ApprovalRecord(BaseModel):
    approval_id: str
    call_id: str
    args_sha256: str
    requested_at: str
    expires_at: str
    status: str  # "pending", "approved", "denied", "expired"
    approved_by: Optional[str] = None
    audit_id: int
    tool: str
    args: dict[str, Any]
    reason: str
    risk_score: float
    session: str

class SandboxGateway:
    def __init__(self):
        # Pending HITL approval records and async futures
        self.approvals_by_id: Dict[str, ApprovalRecord] = {}
        self.approvals_by_audit: Dict[int, ApprovalRecord] = {}
        self.pending_futures: Dict[str, asyncio.Future] = {}
        self.pending_asks: Dict[int, asyncio.Future] = {}

        # Observed network activity ring buffer
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
        """
        Returns list of active pending asks formatted for UI / dashboard consumption.
        """
        pending_list = []
        now_ts = datetime.now(timezone.utc)
        for record in list(self.approvals_by_id.values()):
            if record.status == "pending":
                exp_ts = datetime.fromisoformat(record.expires_at)
                if now_ts > exp_ts:
                    record.status = "expired"
                    continue
                pending_list.append({
                    "audit_id": record.audit_id,
                    "approval_id": record.approval_id,
                    "call_id": record.call_id,
                    "args_sha256": record.args_sha256,
                    "tool": record.tool,
                    "args": json.dumps(record.args),
                    "reason": record.reason,
                    "risk_score": record.risk_score,
                    "requested_at": record.requested_at,
                    "expires_at": record.expires_at,
                    "status": record.status,
                })
        return pending_list

    async def process_tool_call(self, call: ToolCall, session_id: Optional[str] = None) -> GatewayResponse:
        session = session_id or call.agent_id

        # Stage 1 & 2: Evaluate Policy Gate
        decision, reason, rule_id, score = policy_engine.evaluate(call)

        # Stage 3: Write-Ahead Audit Entry to Hash Chain
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

        # Stage 3b: Track Observed Network Activity
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

        # Stage 4: Handle ASK (Human In The Loop queue with 60s timeout & default deny)
        if decision == DecisionType.ASK:
            resolved_decision, resolved_reason = await self._await_human_approval(
                audit_id=audit_entry.id,
                session=session,
                tool=call.tool.value,
                args=call.args,
                reason=reason,
                risk_score=score,
                timeout_sec=60.0
            )
            decision = resolved_decision
            reason = resolved_reason

        # Stage 4b: If Blocked or Denied, return without executing
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

        # Stage 5: Execute in Hardened Sandbox Runtime
        raw_result = sandbox_executor.run_in_container(session, call.tool.value, call.args)

        # Stage 6 & 7: Result Inspection (Secrets Redaction, Untrusted Tagging, Taint Tracking)
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
        session: str,
        tool: str,
        args: dict[str, Any],
        reason: str,
        risk_score: float,
        timeout_sec: float = 60.0
    ) -> tuple[DecisionType, str]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        # Compute SHA-256 bound to canonical tool arguments
        canonical_args_str = canonical_json_dumps(args)
        args_sha256 = hashlib.sha256(canonical_args_str.encode("utf-8")).hexdigest()

        call_id = f"call-{audit_id}-{int(time.time()*1000)}"
        approval_id = f"appr-{audit_id}-{int(time.time()*1000)}"

        now_utc = datetime.now(timezone.utc)
        requested_at_iso = now_utc.isoformat()
        expires_at_iso = datetime.fromtimestamp(
            now_utc.timestamp() + timeout_sec,
            timezone.utc
        ).isoformat()

        record = ApprovalRecord(
            approval_id=approval_id,
            call_id=call_id,
            args_sha256=args_sha256,
            requested_at=requested_at_iso,
            expires_at=expires_at_iso,
            status="pending",
            approved_by=None,
            audit_id=audit_id,
            tool=tool,
            args=args,
            reason=reason,
            risk_score=risk_score,
            session=session
        )

        self.approvals_by_id[approval_id] = record
        self.approvals_by_audit[audit_id] = record
        self.pending_futures[approval_id] = future
        self.pending_asks[audit_id] = future

        # Broadcast structured ask_request envelope to dashboard / approvers
        ask_payload = {
            "audit_id": audit_id,
            "approval_id": approval_id,
            "call_id": call_id,
            "args_sha256": args_sha256,
            "tool": tool,
            "args": json.dumps(args),
            "reason": reason,
            "risk_score": risk_score,
            "requested_at": requested_at_iso,
            "expires_at": expires_at_iso,
            "status": "pending"
        }
        self._notify("ask_request", ask_payload)

        try:
            # 60s timeout with default deny (fail-closed)
            decision, res_reason = await asyncio.wait_for(future, timeout=timeout_sec)
            return decision, res_reason
        except asyncio.TimeoutError:
            record.status = "expired"
            self._notify("ask_resolved", {
                "audit_id": audit_id,
                "approval_id": approval_id,
                "outcome": "timeout",
                "status": "expired"
            })
            return DecisionType.BLOCK, f"HITL operator approval timed out after {int(timeout_sec)}s; request denied (fail-closed default deny)"
        finally:
            self.pending_futures.pop(approval_id, None)
            self.pending_asks.pop(audit_id, None)

    def resolve_approval(
        self,
        approval_id: Optional[str] = None,
        audit_id: Optional[int] = None,
        decision: DecisionType = DecisionType.ALLOW,
        reason: str = "Operator approved",
        approver: str = "security-admin",
        expected_args_sha256: Optional[str] = None
    ) -> tuple[bool, str, Optional[ApprovalRecord]]:
        """
        Validates tokenized HITL approval request against the tool call hash,
        enforces one-time use, 60s expiration, and records approver in the audit chain.
        """
        record: Optional[ApprovalRecord] = None
        if approval_id and approval_id in self.approvals_by_id:
            record = self.approvals_by_id[approval_id]
        elif audit_id and audit_id in self.approvals_by_audit:
            record = self.approvals_by_audit[audit_id]

        if not record:
            return False, "Approval request not found or already cleaned up", None

        # 1. Enforce one-time use
        if record.status != "pending":
            return False, f"Approval request is already '{record.status}' (one-time use enforced)", record

        # 2. Enforce 60s expiration
        now_utc = datetime.now(timezone.utc)
        expires_dt = datetime.fromisoformat(record.expires_at)
        if now_utc > expires_dt:
            record.status = "expired"
            return False, "Approval request has expired (default deny)", record

        # 3. Validate bound tool call args hash
        if expected_args_sha256 and expected_args_sha256 != record.args_sha256:
            return False, f"Tool call args hash mismatch: expected '{record.args_sha256}', received '{expected_args_sha256}'", record

        # 4. Resolve status
        record.status = "approved" if decision == DecisionType.ALLOW else "denied"
        record.approved_by = approver

        # 5. Record approver in the cryptographic audit ledger
        audit_ledger.append(
            session=record.session,
            task="hitl-approval",
            source="hitl_approver",
            tool=record.tool,
            args={
                "approval_id": record.approval_id,
                "call_id": record.call_id,
                "args_sha256": record.args_sha256,
                "approved_by": approver,
                "decision": decision.value,
                "audit_id": record.audit_id
            },
            decision=decision.value,
            reason=f"HITL approval {decision.value} by {approver} for call {record.call_id}: {reason}",
            rule_id="HITL-APPROVE" if decision == DecisionType.ALLOW else "HITL-DENY",
            score=record.risk_score
        )

        # 6. Unblock waiting execution future
        if record.approval_id in self.pending_futures and not self.pending_futures[record.approval_id].done():
            self.pending_futures[record.approval_id].set_result((decision, reason))
        if record.audit_id in self.pending_asks and not self.pending_asks[record.audit_id].done():
            self.pending_asks[record.audit_id].set_result((decision, reason))

        # 7. Broadcast resolution event
        self._notify("ask_resolved", {
            "audit_id": record.audit_id,
            "approval_id": record.approval_id,
            "outcome": "approved" if decision == DecisionType.ALLOW else "denied",
            "approver": approver,
            "status": record.status
        })

        return True, "Approval resolved successfully", record

    def resolve_ask(self, audit_id: int, decision: DecisionType, reason: str, approver: str = "operator") -> bool:
        """
        Backward-compatible resolution method.
        """
        success, _, _ = self.resolve_approval(
            audit_id=audit_id,
            decision=decision,
            reason=reason,
            approver=approver
        )
        return success

    def _inspect_and_sanitize_result(self, session_id: str, tool: str, result: dict[str, Any]) -> dict[str, Any]:
        sanitized = dict(result)

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
                elif tool == "http":
                    taint_tracker.mark_untrusted_context(
                        session_id,
                        f"External HTTP content ingested from remote endpoint into session"
                    )

                # Tag provenance
                tagged_text = content_inspector.tag_untrusted(redacted_text, source=f"runtime:{tool}", score=inj_score)
                sanitized[key] = tagged_text

        return sanitized

sandbox_gateway = SandboxGateway()
