"""Append-only, hash-chained audit log in SQLite. Edits are new rows; UPDATE/DELETE are blocked by triggers."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

GENESIS = "0" * 64
EventType = Literal["draft", "edit", "confirm"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    seq               INTEGER PRIMARY KEY,
    ts                TEXT NOT NULL,
    incident_id       TEXT NOT NULL,
    event_type        TEXT NOT NULL CHECK (event_type IN ('draft','edit','confirm')),
    supersedes_seq    INTEGER,
    audio_sha256      TEXT,
    transcript_sha256 TEXT NOT NULL,
    json_sha256       TEXT NOT NULL,
    payload_json      TEXT NOT NULL,
    prev_hash         TEXT NOT NULL,
    entry_hash        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_incident ON audit_log(incident_id);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
"""

_COLUMNS = ("seq", "ts", "incident_id", "event_type", "supersedes_seq", "audio_sha256",
            "transcript_sha256", "json_sha256", "payload_json", "prev_hash", "entry_hash")
_HASHED = _COLUMNS[:9]  # everything except prev_hash and entry_hash


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


@dataclass
class AuditRow:
    seq: int
    ts: str
    incident_id: str
    event_type: str
    supersedes_seq: int | None
    audio_sha256: str | None
    transcript_sha256: str
    json_sha256: str
    payload_json: str
    prev_hash: str
    entry_hash: str

    def compute_hash(self) -> str:
        return sha256_hex(canonical_json({k: getattr(self, k) for k in _HASHED}) + self.prev_hash)


@dataclass
class VerifyResult:
    ok: bool
    checked: int
    first_bad_seq: int | None
    reason: str | None


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con:
            con.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30, isolation_level=None)

    def append(self, event_type: EventType, incident_id: str, payload: dict, *, transcript: str = "",
               audio_sha256: str | None = None, supersedes_seq: int | None = None) -> AuditRow:
        payload_json = canonical_json(payload)
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")  # serialises concurrent writers so the chain stays linear
            last = con.execute("SELECT seq, entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
            row = AuditRow(
                seq=(last[0] + 1) if last else 1,
                ts=datetime.now().astimezone().isoformat(),
                incident_id=incident_id,
                event_type=event_type,
                supersedes_seq=supersedes_seq,
                audio_sha256=audio_sha256,
                transcript_sha256=sha256_hex(transcript),
                json_sha256=sha256_hex(payload_json),
                payload_json=payload_json,
                prev_hash=last[1] if last else GENESIS,
                entry_hash="",
            )
            row.entry_hash = row.compute_hash()
            con.execute(f"INSERT INTO audit_log ({','.join(_COLUMNS)}) VALUES ({','.join('?' * len(_COLUMNS))})",
                        [getattr(row, c) for c in _COLUMNS])
            con.execute("COMMIT")
            return row
        except BaseException:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def rows(self, incident_id: str | None = None) -> list[AuditRow]:
        sql = f"SELECT {','.join(_COLUMNS)} FROM audit_log"
        args: tuple = ()
        if incident_id is not None:
            sql += " WHERE incident_id = ?"
            args = (incident_id,)
        with closing(self._connect()) as con:
            return [AuditRow(*r) for r in con.execute(sql + " ORDER BY seq", args)]

    def verify(self) -> VerifyResult:
        prev_hash, expected_seq, checked = GENESIS, 1, 0
        for row in self.rows():
            if row.seq != expected_seq:
                return VerifyResult(False, checked, row.seq, "seq gap")
            if sha256_hex(row.payload_json) != row.json_sha256:
                return VerifyResult(False, checked, row.seq, "payload hash mismatch")
            if row.prev_hash != prev_hash:
                return VerifyResult(False, checked, row.seq, "broken link")
            if row.compute_hash() != row.entry_hash:
                return VerifyResult(False, checked, row.seq, "entry hash mismatch")
            prev_hash, expected_seq, checked = row.entry_hash, expected_seq + 1, checked + 1
        return VerifyResult(True, checked, None, None)
