import sqlite3
import hashlib
import hmac
from pathlib import Path
from typing import Optional, Tuple
from ..config import settings
from .ledger import GENESIS_HASH

def verify_chain(db_path: Optional[Path] = None, hmac_key: Optional[str] = None) -> Tuple[bool, Optional[int], str]:
    """
    Recomputes the cryptographic SHA-256 / HMAC hash chain from root to head.
    Returns:
        (is_valid, broken_entry_id, status_message)
    """
    target_db = db_path or settings.AUDIT_DB_PATH
    if not Path(target_db).exists():
        return True, None, "Audit database does not exist yet (0 entries)."

    key_bytes = (hmac_key or settings.HMAC_SECRET_KEY).encode("utf-8")

    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return True, None, "Audit log is empty (chain intact)."

    expected_prev = GENESIS_HASH

    for row in rows:
        entry_id = row["id"]
        actual_prev = row["prev_hash"]
        actual_hash = row["hash"]

        # Check link with previous record
        if actual_prev != expected_prev:
            return (
                False, 
                entry_id, 
                f"Broken chain link at entry #{entry_id}: prev_hash '{actual_prev}' does not match expected '{expected_prev}'"
            )

        # Recompute hash of current record
        canonical_payload = (
            f"{row['prev_hash']}|{row['ts']}|{row['source']}|{row['tool']}|"
            f"{row['args']}|{row['decision']}|{row['reason']}|{row['rule_id']}|{row['policy_hash']}"
        )

        if key_bytes:
            computed_hash = hmac.new(key_bytes, canonical_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        else:
            computed_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

        if computed_hash != actual_hash:
            return (
                False, 
                entry_id, 
                f"Tampered entry detected at #{entry_id}: computed hash '{computed_hash}' != stored hash '{actual_hash}'"
            )

        expected_prev = actual_hash

    return True, None, f"Audit chain verified successfully across {len(rows)} entries."
