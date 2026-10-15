import threading
from typing import Dict

class SessionState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_tainted: bool = False
        self.has_read_sensitive: bool = False
        self.has_untrusted_context: bool = False
        self.taint_reasons: list[str] = []
        self.call_count: int = 0

class TaintTracker:
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> SessionState:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState(session_id)
            return self._sessions[session_id]

    def record_call(self, session_id: str) -> int:
        session = self.get_or_create(session_id)
        with self._lock:
            session.call_count += 1
            return session.call_count

    def mark_sensitive_read(self, session_id: str, reason: str):
        session = self.get_or_create(session_id)
        with self._lock:
            session.has_read_sensitive = True
            session.taint_reasons.append(f"Sensitive read: {reason}")

    def mark_untrusted_context(self, session_id: str, reason: str):
        session = self.get_or_create(session_id)
        with self._lock:
            session.has_untrusted_context = True
            session.is_tainted = True
            session.taint_reasons.append(f"Untrusted ingest: {reason}")

    def check_lethal_trifecta(self, session_id: str, is_outbound_tool: bool) -> tuple[bool, str]:
        """
        Detects the sequence:
        Sensitive Read + Untrusted Ingestion in context + Outbound Network Attempt.
        """
        session = self.get_or_create(session_id)
        with self._lock:
            if is_outbound_tool and session.has_read_sensitive and session.has_untrusted_context:
                return (
                    True,
                    f"Sequence violation (Lethal Trifecta): Session '{session_id}' read sensitive files and ingested untrusted content before calling outbound network tool."
                )
            return False, ""

    def reset_session(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

taint_tracker = TaintTracker()
