import json
import sqlite3
import hashlib
import hmac
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from pathlib import Path

from ..config import settings
from ..models import AuditEntry

GENESIS_HASH = "0" * 64

class AuditLedger:
    def __init__(self, db_path: Optional[Path] = None, hmac_key: Optional[str] = None):
        self.db_path = db_path or settings.AUDIT_DB_PATH
        self.hmac_key = (hmac_key or settings.HMAC_SECRET_KEY).encode("utf-8")
        self._lock = threading.Lock()
        self._listeners: list[Callable[[dict[str, Any]], None]] = []
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    session TEXT NOT NULL,
                    task TEXT NOT NULL,
                    source TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    args TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    policy_hash TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    agent_thought TEXT,
                    user_input TEXT
                )
                """)
                # Safe migration if table was created previously without new columns
                try:
                    conn.execute("ALTER TABLE audit ADD COLUMN agent_thought TEXT")
                except Exception:
                    pass
                try:
                    conn.execute("ALTER TABLE audit ADD COLUMN user_input TEXT")
                except Exception:
                    pass
                conn.commit()

    def compute_hash(self, prev_hash: str, ts: str, source: str, tool: str, 
                     args_str: str, decision: str, reason: str, rule_id: str, 
                     policy_hash: str) -> str:
        """
        Compute deterministic cryptographic hash over the canonical payload.
        """
        canonical_payload = (
            f"{prev_hash}|{ts}|{source}|{tool}|{args_str}|"
            f"{decision}|{reason}|{rule_id}|{policy_hash}"
        )
        if self.hmac_key:
            return hmac.new(self.hmac_key, canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    def get_latest_hash(self) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row["hash"]
            return GENESIS_HASH

    def append(self, session: str, task: str, source: str, tool: str, 
               args: dict[str, Any], decision: str, reason: str, 
               rule_id: str, score: float = 0.0, policy_hash: Optional[str] = None,
               agent_thought: Optional[str] = None, user_input: Optional[str] = None) -> AuditEntry:
        """
        Write-ahead append to the tamper-evident cryptographic hash chain.
        """
        policy_hash = policy_hash or settings.POLICY_HASH
        ts = datetime.now(timezone.utc).isoformat()
        args_str = json.dumps(args, sort_keys=True)

        with self._lock:
            prev_hash = self.get_latest_hash()
            curr_hash = self.compute_hash(
                prev_hash=prev_hash,
                ts=ts,
                source=source,
                tool=tool,
                args_str=args_str,
                decision=decision,
                reason=reason,
                rule_id=rule_id,
                policy_hash=policy_hash
            )

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit (
                        ts, session, task, source, tool, args, decision, 
                        reason, rule_id, score, policy_hash, prev_hash, hash,
                        agent_thought, user_input
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ts, session, task, source, tool, args_str, decision, 
                      reason, rule_id, score, policy_hash, prev_hash, curr_hash,
                      agent_thought, user_input))
                entry_id = cursor.lastrowid
                conn.commit()

            entry = AuditEntry(
                id=entry_id,
                ts=ts,
                session=session,
                task=task,
                source=source,
                tool=tool,
                args=args_str,
                decision=decision,
                reason=reason,
                rule_id=rule_id,
                score=score,
                policy_hash=policy_hash,
                prev_hash=prev_hash,
                hash=curr_hash,
                agent_thought=agent_thought,
                user_input=user_input
            )

            # Broadcast event to real-time subscribers (WebSockets)
            self._notify_listeners(entry.model_dump())
            return entry

    def register_listener(self, callback: Callable[[dict[str, Any]], None]):
        self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[dict[str, Any]], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, event_data: dict[str, Any]):
        for listener in list(self._listeners):
            try:
                listener(event_data)
            except Exception:
                pass

    def get_entries(self, limit: int = 100, offset: int = 0) -> list[AuditEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audit ORDER BY id DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            return [AuditEntry(**dict(row)) for row in rows]

    def get_entry_by_id(self, entry_id: int) -> Optional[AuditEntry]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            if row:
                return AuditEntry(**dict(row))
            return None

    def tamper_entry(self, entry_id: int, new_args: str = '{"tampered": true, "attack": "bypassed"}') -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE audit SET args = ? WHERE id = ?", (new_args, entry_id))
                conn.commit()
                return cursor.rowcount > 0

audit_ledger = AuditLedger()
