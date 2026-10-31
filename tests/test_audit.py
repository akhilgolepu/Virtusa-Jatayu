import sqlite3
import subprocess
import sys
import threading

import pytest

from jatayu.audit import GENESIS, AuditLog, VerifyResult


def test_append_and_verify(tmp_db):
    log = AuditLog(tmp_db)
    r1 = log.append("draft", "inc1", {"a": 1}, transcript="hello")
    r2 = log.append("edit", "inc1", {"a": 2}, supersedes_seq=r1.seq)
    assert r1.prev_hash == GENESIS and r2.prev_hash == r1.entry_hash
    assert log.verify() == VerifyResult(ok=True, checked=2, first_bad_seq=None, reason=None)


def test_update_and_delete_blocked(tmp_db):
    log = AuditLog(tmp_db)
    log.append("draft", "inc1", {"a": 1})
    con = sqlite3.connect(tmp_db)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        con.execute("UPDATE audit_log SET payload_json='{}'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        con.execute("DELETE FROM audit_log")


def test_tamper_script_is_caught(tmp_db):
    log = AuditLog(tmp_db)
    for i in range(3):
        log.append("draft", "inc1", {"entry": [{"dose": 1.0}], "i": i})
    subprocess.run([sys.executable, "scripts/tamper.py", "--db", str(tmp_db), "--seq", "2", "--dose", "10"], check=True)
    v = AuditLog(tmp_db).verify()
    assert not v.ok and v.first_bad_seq == 2 and v.reason == "payload hash mismatch"


def test_deleted_row_is_caught(tmp_db):
    log = AuditLog(tmp_db)
    for i in range(3):
        log.append("draft", "inc1", {"i": i})
    con = sqlite3.connect(tmp_db)
    con.execute("DROP TRIGGER audit_no_delete")
    con.execute("DELETE FROM audit_log WHERE seq = 2")
    con.commit()
    v = AuditLog(tmp_db).verify()
    assert not v.ok and v.first_bad_seq == 3 and v.reason == "seq gap"


def test_concurrent_appends_stay_linear(tmp_db):
    log = AuditLog(tmp_db)
    ts = [threading.Thread(target=lambda: [log.append("draft", "inc", {"n": n}) for n in range(50)]) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    v = log.verify()
    assert v.ok and v.checked == 100
