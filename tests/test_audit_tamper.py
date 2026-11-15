"""M1 tamper suite: every mutation type below must make verify() fail at the right row.
Tail deletion is the one documented blind spot of a bare hash chain (caught only by server receipts, Stage 3 S3)."""
import json
import sqlite3

import pytest

from jatayu.audit import AuditLog, canonical_json, sha256_hex


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.sqlite"
    log = AuditLog(path)
    for i in range(5):
        log.append("draft", "inc", {"entries": [{"dose": 0.3, "drug": "epinephrine"}], "i": i}, transcript=f"say {i}")
    return path


def _sql(path, *stmts):
    con = sqlite3.connect(path)
    con.execute("DROP TRIGGER IF EXISTS audit_no_update")
    con.execute("DROP TRIGGER IF EXISTS audit_no_delete")
    for s, args in stmts:
        con.execute(s, args)
    con.commit()
    con.close()


def _verify(path):
    return AuditLog(path).verify()


def _row(path, seq):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    r = dict(con.execute("SELECT * FROM audit_log WHERE seq = ?", (seq,)).fetchone())
    con.close()
    return r


MUTATIONS = {
    "edit_payload_field": ("UPDATE audit_log SET payload_json = replace(payload_json, '0.3', '3.0') WHERE seq = 3", 3),
    "edit_transcript_hash": ("UPDATE audit_log SET transcript_sha256 = 'x' || substr(transcript_sha256, 2) WHERE seq = 2", 2),
    "edit_timestamp": ("UPDATE audit_log SET ts = '2020-01-01T00:00:00+00:00' WHERE seq = 4", 4),
    "edit_event_type": ("UPDATE audit_log SET event_type = 'confirm' WHERE seq = 2", 2),
    "edit_incident_id": ("UPDATE audit_log SET incident_id = 'other' WHERE seq = 3", 3),
    "delete_middle_row": ("DELETE FROM audit_log WHERE seq = 3", 4),
    # always a different first hex digit (the old replace(...,'f') was a no-op when the hash began with 'f': 1 run in 16)
    "edit_prev_hash": ("UPDATE audit_log SET prev_hash = (CASE WHEN substr(prev_hash, 1, 1) = 'f' THEN '0' ELSE 'f' END)"
                       " || substr(prev_hash, 2) WHERE seq = 4", 4),
    "edit_audio_hash": ("UPDATE audit_log SET audio_sha256 = 'deadbeef' WHERE seq = 5", 5),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_mutation_is_detected(db, name):
    stmt, bad_seq = MUTATIONS[name]
    assert _verify(db).ok
    _sql(db, (stmt, ()))
    v = _verify(db)
    assert not v.ok and v.first_bad_seq == bad_seq, (name, v)


def test_inserted_forged_row_is_detected(db):
    r = _row(db, 5)
    forged = {**r, "seq": 6, "payload_json": canonical_json({"entries": [{"dose": 10}]})}
    forged["json_sha256"] = sha256_hex(forged["payload_json"])  # self-consistent hash, but no valid link/entry hash
    _sql(db, ("INSERT INTO audit_log VALUES (:seq,:ts,:incident_id,:event_type,:supersedes_seq,:audio_sha256,"
              ":transcript_sha256,:json_sha256,:payload_json,:prev_hash,:entry_hash)", forged))
    v = _verify(db)
    assert not v.ok and v.first_bad_seq == 6


def test_reordered_rows_are_detected(db):
    a, b = _row(db, 2), _row(db, 3)
    cols = [k for k in a if k != "seq"]
    sets = ", ".join(f"{c} = :{c}" for c in cols)
    _sql(db, (f"UPDATE audit_log SET {sets} WHERE seq = 2", {c: b[c] for c in cols}),
         (f"UPDATE audit_log SET {sets} WHERE seq = 3", {c: a[c] for c in cols}))
    v = _verify(db)
    assert not v.ok and v.first_bad_seq == 2


def test_swapped_entry_hashes_are_detected(db):
    a, b = _row(db, 2), _row(db, 3)
    _sql(db, ("UPDATE audit_log SET entry_hash = ? WHERE seq = 2", (b["entry_hash"],)),
         ("UPDATE audit_log SET entry_hash = ? WHERE seq = 3", (a["entry_hash"],)))
    assert _verify(db).first_bad_seq == 2


def test_consistently_rehashed_row_breaks_the_next_link(db):
    """An attacker edits row 3 and recomputes its own hashes; row 4 still points at the old hash."""
    from jatayu.audit import AuditRow
    r = _row(db, 3)
    r["payload_json"] = canonical_json({"entries": [{"dose": 3.0, "drug": "epinephrine"}], "i": 2})
    r["json_sha256"] = sha256_hex(r["payload_json"])
    r["entry_hash"] = AuditRow(**r).compute_hash()
    _sql(db, ("UPDATE audit_log SET payload_json = ?, json_sha256 = ?, entry_hash = ? WHERE seq = 3",
              (r["payload_json"], r["json_sha256"], r["entry_hash"])))
    v = _verify(db)
    assert not v.ok and v.first_bad_seq == 4 and v.reason == "broken link"


def test_tail_deletion_is_NOT_detectable_by_the_chain_alone(db):
    """Documented limitation: deleting the newest rows leaves a valid shorter chain. Needs server receipts (S3)."""
    _sql(db, ("DELETE FROM audit_log WHERE seq >= 4", ()))
    v = _verify(db)
    assert v.ok and v.checked == 3


def test_tamper_type_count_meets_the_milestone():
    assert len(MUTATIONS) + 4 >= 8  # 8 parametrised + insert + reorder + swap + consistent re-hash = 12
