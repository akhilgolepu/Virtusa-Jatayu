"""Incidents: mutable metadata in SQLite; the clinical history is the append-only audit log, folded into state."""
from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter

from jatayu.audit import AuditLog
from jatayu.models import Entry

ENTRY = TypeAdapter(Entry)


class IncidentStore:
    def __init__(self, db_path: Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con, con:
            con.execute("CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, label TEXT, started_at TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    def create(self, label: str | None = None) -> dict:
        inc = {"id": uuid.uuid4().hex, "label": label, "started_at": datetime.now().astimezone().isoformat()}
        with closing(self._connect()) as con, con:
            con.execute("INSERT INTO incidents (id, label, started_at) VALUES (:id, :label, :started_at)", inc)
        return inc

    def get(self, incident_id: str) -> dict | None:
        with closing(self._connect()) as con:
            row = con.execute("SELECT id, label, started_at FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        return dict(zip(("id", "label", "started_at"), row)) if row else None

    def list(self) -> list[dict]:
        with closing(self._connect()) as con:
            rows = con.execute("SELECT id, label, started_at FROM incidents ORDER BY started_at DESC").fetchall()
        return [dict(zip(("id", "label", "started_at"), r)) for r in rows]


@dataclass
class EntryState:
    entry: Entry
    utterance_id: str
    status: str = "draft"  # draft | edited | confirmed | rejected
    history: list[int] = field(default_factory=list)
    acknowledged: list[str] = field(default_factory=list)


@dataclass
class IncidentState:
    incident_id: str
    entries: dict[str, EntryState] = field(default_factory=dict)
    utterances: list[dict] = field(default_factory=list)

    def current_entries(self) -> list[Entry]:
        """Entries that still stand (rejected ones are kept in the chain but take no part in checks)."""
        return [s.entry for s in self.entries.values() if s.status != "rejected"]


def incident_state(audit: AuditLog, incident_id: str) -> IncidentState:
    import json

    state = IncidentState(incident_id)
    for row in audit.rows(incident_id):
        payload = json.loads(row.payload_json)
        if row.event_type == "draft" and payload.get("type") == "draft":
            utt = payload["utterance"]
            state.utterances.append({"id": utt["id"], "transcript": utt["raw_transcript"],
                                     "capture_time": utt["capture_time"], "audio_sha256": utt.get("audio_sha256"),
                                     "seq": row.seq})
            for raw in payload["entries"]:
                e = ENTRY.validate_python(raw)
                state.entries[e.id] = EntryState(entry=e, utterance_id=utt["id"], history=[row.seq])
        elif row.event_type == "edit" and payload.get("type") == "reject" and payload.get("entry_id") in state.entries:
            s = state.entries[payload["entry_id"]]  # stored as an edit row: the chain schema allows draft/edit/confirm
            s.status = "rejected"
            s.history.append(row.seq)
        elif row.event_type == "edit" and payload.get("entry_id") in state.entries:
            s = state.entries[payload["entry_id"]]
            s.entry = ENTRY.validate_python(payload["entry"])
            s.status = "edited"
            s.history.append(row.seq)
        elif row.event_type == "confirm":
            for eid in payload.get("entry_ids", []):
                if eid in state.entries:
                    s = state.entries[eid]
                    s.status = "confirmed"
                    s.history.append(row.seq)
                    s.acknowledged = list(payload.get("acknowledged", []))
    return state


STRUCTURAL = {"field_missing", "time_not_stated", "low_confidence", "llm_unsupported", "ambiguous_dose",
              "dose_range_stated", "time_borrowed", "low_asr_confidence", "self_correction", "concentration_not_dose"}
_CHECKED = {"medication": ("drug", "dose_value", "dose_unit", "route", "time"), "procedure": ("procedure", "time", "detail")}


def apply_user_edit(current: Entry, edited: Entry) -> Entry:
    """Fields whose value the user changed become source="user" (span None: the transcript no longer supports
    them). Structural flags are recomputed; context flags (possible_not_given, ...) stay until acknowledged.
    The result is re-validated, so an edited time is parsed back into an aware datetime."""
    base = current.model_dump(mode="json")
    new = edited.model_dump(mode="json")
    changed = []
    for name in _CHECKED[current.kind]:
        old_v = (base.get(name) or {}).get("value")
        new_v = (new.get(name) or {}).get("value")
        if new_v != old_v:
            changed.append(name)
            base[name] = None if new.get(name) is None else {"value": new_v, "span": None, "confidence": 1.0,
                                                               "source": "user"}
    flags = [f for f in base["flags"] if f["code"] not in STRUCTURAL or f.get("field") not in changed]
    if current.kind == "medication":
        for name, sev in (("dose_value", "high"), ("dose_unit", "high"), ("route", "medium")):
            missing = (base.get(name) or {}).get("value") is None
            if name == "dose_unit" and (base.get("dose_value") or {}).get("value") is None:
                continue
            if missing and not any(f["code"] == "field_missing" and f.get("field") == name for f in flags):
                flags.append({"code": "field_missing", "field": name, "severity": sev,
                              "message": f"{name.replace('_', ' ').capitalize()} not stated."})
    base["flags"] = flags
    return ENTRY.validate_python(base)
