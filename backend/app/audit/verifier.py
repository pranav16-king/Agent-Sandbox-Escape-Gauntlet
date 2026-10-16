from pathlib import Path
from typing import Optional, Tuple
from .chain import verify_audit_chain, GENESIS_HASH

def verify_chain(db_path: Optional[Path] = None, hmac_key: Optional[str] = None) -> Tuple[bool, Optional[int], str]:
    """
    Recomputes the cryptographic SHA-256 / HMAC hash chain from root to head.
    Returns:
        (is_valid, broken_entry_id, status_message)
    """
    ok, checked, broken_seq, msg = verify_audit_chain(db_path=db_path, hmac_key=hmac_key)
    return ok, broken_seq, msg
