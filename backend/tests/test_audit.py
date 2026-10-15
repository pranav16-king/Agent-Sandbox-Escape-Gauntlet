import sqlite3
from pathlib import Path
from app.audit.ledger import AuditLedger
from app.audit.verifier import verify_chain

def test_audit_hash_chain_verification_and_tampering(tmp_path: Path):
    test_db = tmp_path / "test_audit.db"
    hmac_key = "test-hmac-key"
    ledger = AuditLedger(db_path=test_db, hmac_key=hmac_key)

    # 1. Append valid audit entries
    for i in range(1, 6):
        ledger.append(
            session=f"session-{i}",
            task="default-task",
            source="gateway",
            tool="file",
            args={"op": "read", "path": f"/workspace/file_{i}.txt"},
            decision="allow" if i < 4 else "block",
            reason=f"Policy verdict #{i}",
            rule_id="FS-PASS" if i < 4 else "FS-001",
            score=0.1 * i,
            policy_hash="test-policy-hash"
        )

    # 2. Verify untampered chain
    is_valid, broken_id, message = verify_chain(db_path=test_db, hmac_key=hmac_key)
    assert is_valid is True
    assert broken_id is None
    assert "verified successfully across 5 entries" in message

    # 3. Simulate retroactive attacker tampering on entry #3
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    cursor.execute("UPDATE audit SET decision = 'tampered_override' WHERE id = 3")
    conn.commit()
    conn.close()

    # 4. Verify that tampering is immediately caught at exact entry #3
    tampered_valid, tampered_broken_id, tampered_msg = verify_chain(db_path=test_db, hmac_key=hmac_key)
    assert tampered_valid is False
    assert tampered_broken_id == 3
    assert "Tampered entry detected at #3" in tampered_msg
