import json
import sqlite3
import hashlib
import hmac
from pathlib import Path
from typing import Any, Optional, Tuple

from ..config import settings

GENESIS_HASH = "0" * 64

def canonical_json_dumps(obj: Any) -> str:
    """
    Canonical JSON serialization:
    - Sorted keys
    - Compact separators (',', ':') without whitespace variance
    - Stable string encoding
    """
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def compute_entry_hash(prev_hash: str, canonical_json: str, secret_key: Optional[bytes] = None) -> str:
    """
    Cryptographic signature: HMAC-SHA256(key, prev_hash || canonical_json).
    Falls back to SHA-256 if secret_key is not configured.
    """
    payload_bytes = (prev_hash + canonical_json).encode("utf-8")
    if secret_key:
        return hmac.new(secret_key, payload_bytes, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload_bytes).hexdigest()

def build_entry_canonical_payload(
    ts: str,
    session: str,
    task: str,
    source: str,
    tool: str,
    args_str: str,
    decision: str,
    reason: str,
    rule_id: str,
    score: float,
    policy_hash: str,
    agent_thought: Optional[str] = None,
    user_input: Optional[str] = None
) -> str:
    """
    Builds the canonical JSON string representing an audit record's content.
    """
    payload_dict = {
        "agent_thought": agent_thought,
        "args": args_str,
        "decision": decision,
        "policy_hash": policy_hash,
        "reason": reason,
        "rule_id": rule_id,
        "score": round(float(score), 4),
        "session": session,
        "source": source,
        "task": task,
        "tool": tool,
        "ts": ts,
        "user_input": user_input,
    }
    return canonical_json_dumps(payload_dict)

def verify_audit_chain(
    db_path: Optional[Path] = None,
    hmac_key: Optional[str] = None
) -> Tuple[bool, int, Optional[int], str]:
    """
    Recomputes the cryptographic HMAC-SHA256 hash chain from root to head.
    Returns:
        (ok, checked, first_bad_seq, status_message)
    """
    target_db = db_path or settings.AUDIT_DB_PATH
    if not Path(target_db).exists():
        return True, 0, None, "Audit database does not exist yet (0 entries)."

    key_bytes = (hmac_key or settings.HMAC_SECRET_KEY).encode("utf-8")

    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    total_rows = len(rows)
    if total_rows == 0:
        return True, 0, None, "Audit log is empty (chain intact)."

    expected_prev = GENESIS_HASH

    for idx, row in enumerate(rows):
        entry_id = row["id"]
        actual_prev = row["prev_hash"]
        actual_hash = row["hash"]

        # Check hash link continuity
        if actual_prev != expected_prev:
            return (
                False,
                idx,
                entry_id,
                f"Broken chain link at entry #{entry_id}: prev_hash '{actual_prev}' does not match expected '{expected_prev}'"
            )

        # Reconstruct canonical payload
        canonical_json = build_entry_canonical_payload(
            ts=row["ts"],
            session=row["session"],
            task=row["task"],
            source=row["source"],
            tool=row["tool"],
            args_str=row["args"],
            decision=row["decision"],
            reason=row["reason"],
            rule_id=row["rule_id"],
            score=row["score"],
            policy_hash=row["policy_hash"],
            agent_thought=row["agent_thought"] if "agent_thought" in row.keys() else None,
            user_input=row["user_input"] if "user_input" in row.keys() else None
        )

        computed_hash = compute_entry_hash(actual_prev, canonical_json, key_bytes)

        if computed_hash != actual_hash:
            # Fallback legacy format check for backward compatibility with pre-WP6 entries
            legacy_payload = (
                f"{row['prev_hash']}|{row['ts']}|{row['source']}|{row['tool']}|"
                f"{row['args']}|{row['decision']}|{row['reason']}|{row['rule_id']}|{row['policy_hash']}"
            )
            legacy_hash = hmac.new(key_bytes, legacy_payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if legacy_hash != actual_hash:
                return (
                    False,
                    idx,
                    entry_id,
                    f"Tampered entry detected at #{entry_id}: computed hash '{computed_hash}' != stored hash '{actual_hash}'"
                )

        expected_prev = actual_hash

    return True, total_rows, None, f"Audit chain verified successfully across {total_rows} entries."
