import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from pathlib import Path

from ..config import settings

class SessionState:
    def __init__(
        self,
        session_id: str,
        is_tainted: bool = False,
        has_read_sensitive: bool = False,
        has_untrusted_context: bool = False,
        taint_reasons: Optional[list[str]] = None,
        call_count: int = 0
    ):
        self.session_id = session_id
        self.is_tainted: bool = is_tainted
        self.has_read_sensitive: bool = has_read_sensitive
        self.has_untrusted_context: bool = has_untrusted_context
        self.taint_reasons: list[str] = taint_reasons or []
        self.call_count: int = call_count

class TaintTracker:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.AUDIT_DB_PATH
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS session_taint (
                    session_id TEXT PRIMARY KEY,
                    is_tainted INTEGER NOT NULL DEFAULT 0,
                    has_read_sensitive INTEGER NOT NULL DEFAULT 0,
                    has_untrusted_context INTEGER NOT NULL DEFAULT 0,
                    taint_reasons TEXT NOT NULL DEFAULT '[]',
                    call_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """)
                conn.commit()

    def _persist(self, session: SessionState):
        with self._get_connection() as conn:
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO session_taint (
                    session_id, is_tainted, has_read_sensitive,
                    has_untrusted_context, taint_reasons, call_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    is_tainted = excluded.is_tainted,
                    has_read_sensitive = excluded.has_read_sensitive,
                    has_untrusted_context = excluded.has_untrusted_context,
                    taint_reasons = excluded.taint_reasons,
                    call_count = excluded.call_count,
                    updated_at = excluded.updated_at
            """, (
                session.session_id,
                1 if session.is_tainted else 0,
                1 if session.has_read_sensitive else 0,
                1 if session.has_untrusted_context else 0,
                json.dumps(session.taint_reasons),
                session.call_count,
                now_iso
            ))
            conn.commit()

    def get_or_create(self, session_id: str) -> SessionState:
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]

            # Try to read persistent taint record from SQLite
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM session_taint WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                if row:
                    try:
                        reasons = json.loads(row["taint_reasons"])
                    except Exception:
                        reasons = []
                    session = SessionState(
                        session_id=row["session_id"],
                        is_tainted=bool(row["is_tainted"]),
                        has_read_sensitive=bool(row["has_read_sensitive"]),
                        has_untrusted_context=bool(row["has_untrusted_context"]),
                        taint_reasons=reasons,
                        call_count=int(row["call_count"])
                    )
                    self._sessions[session_id] = session
                    return session

            # Fresh session
            session = SessionState(session_id=session_id)
            self._sessions[session_id] = session
            self._persist(session)
            return session

    def record_call(self, session_id: str) -> int:
        session = self.get_or_create(session_id)
        with self._lock:
            session.call_count += 1
            self._persist(session)
            return session.call_count

    def mark_sensitive_read(self, session_id: str, reason: str):
        session = self.get_or_create(session_id)
        with self._lock:
            session.has_read_sensitive = True
            session.taint_reasons.append(f"Sensitive read: {reason}")
            self._persist(session)

    def mark_untrusted_context(self, session_id: str, reason: str):
        session = self.get_or_create(session_id)
        with self._lock:
            session.has_untrusted_context = True
            session.is_tainted = True
            session.taint_reasons.append(f"Untrusted ingest: {reason}")
            self._persist(session)

    def mark_tainted(self, session_id: str, reason: str):
        session = self.get_or_create(session_id)
        with self._lock:
            session.is_tainted = True
            session.taint_reasons.append(f"Session taint: {reason}")
            self._persist(session)

    def is_session_tainted(self, session_id: str) -> bool:
        session = self.get_or_create(session_id)
        return session.is_tainted

    def check_lethal_trifecta(self, session_id: str, is_outbound_tool: bool) -> Tuple[bool, str]:
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
            self._sessions.pop(session_id, None)
            with self._get_connection() as conn:
                conn.execute("DELETE FROM session_taint WHERE session_id = ?", (session_id,))
                conn.commit()

    def clear_all(self):
        with self._lock:
            self._sessions.clear()
            with self._get_connection() as conn:
                conn.execute("DELETE FROM session_taint")
                conn.commit()

taint_tracker = TaintTracker()
