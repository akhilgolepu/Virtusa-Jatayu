import sqlite3

import pytest
from fastapi.testclient import TestClient

from jatayu.api import create_app


def _app(tmp_path):
    return create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "audio", recordings_dir=tmp_path / "rec")


@pytest.fixture
def client(tmp_path):
    return TestClient(_app(tmp_path))


def _say(client, inc, text):
    r = client.post("/api/utterances", data={"incident_id": inc, "text": text, "extractor": "rules"})
    assert r.status_code == 200, r.text
    return r.json()


def _rows(tmp_path):
    return sqlite3.connect(tmp_path / "j.sqlite").execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]


def test_entries_have_ids_and_state_folds_drafts(client):
    inc = client.post("/api/incidents", json={"label": "RTA, NH44"}).json()["id"]
    r = _say(client, inc, "adrenaline 0.3 mg IM two mins ago")
    entry_id = r["entries"][0]["id"]
    state = client.get(f"/api/incidents/{inc}").json()
    assert state["label"] == "RTA, NH44" and state["entries"][0]["entry"]["id"] == entry_id
    assert state["entries"][0]["status"] == "draft" and state["utterances"][0]["transcript"].startswith("adrenaline")


def test_edit_appends_and_never_updates(client, tmp_path):
    inc = client.post("/api/incidents", json={}).json()["id"]
    entry = _say(client, inc, "adrenaline 0.3 mg IM two mins ago")["entries"][0]
    before = _rows(tmp_path)
    entry["dose_value"]["value"] = 0.5
    r = client.post(f"/api/incidents/{inc}/entries/{entry['id']}/edit", json={"entry": entry})
    assert r.status_code == 200 and _rows(tmp_path) == before + 1
    cur = client.get(f"/api/incidents/{inc}").json()["entries"][0]
    assert cur["status"] == "edited" and cur["entry"]["dose_value"]["value"] == 0.5
    assert cur["entry"]["dose_value"]["source"] == "user" and cur["entry"]["dose_value"]["span"] is None
    assert len(cur["history"]) == 2
    assert client.get("/api/audit/verify").json()["ok"]


def test_confirm_requires_acknowledging_high_flags(client, tmp_path):
    inc = client.post("/api/incidents", json={}).json()["id"]
    entry = _say(client, inc, "gave aspirin")["entries"][0]          # no dose -> high field_missing flag
    before = _rows(tmp_path)
    r = client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [entry["id"]], "acknowledged": []})
    assert r.status_code == 409 and r.json()["detail"]["unacknowledged"][0]["code"] == "field_missing"
    assert _rows(tmp_path) == before
    r = client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [entry["id"]], "acknowledged": ["field_missing"]})
    assert r.status_code == 200
    assert client.get(f"/api/incidents/{inc}").json()["entries"][0]["status"] == "confirmed"


def test_bundle_marks_confirmed_completed(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    e = _say(client, inc, "aspirin 300 mg PO two mins ago")["entries"][0]
    client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": []})
    b = client.get(f"/api/incidents/{inc}/bundle").json()
    assert b["entry"][0]["resource"]["status"] == "completed"
    assert b["utterances"][0]["transcript"].startswith("aspirin")


def test_incidents_persist_across_restart(tmp_path):
    inc = TestClient(_app(tmp_path)).post("/api/incidents", json={"label": "x"}).json()["id"]
    assert TestClient(_app(tmp_path)).get(f"/api/incidents/{inc}").json()["label"] == "x"
    assert [i["id"] for i in TestClient(_app(tmp_path)).get("/api/incidents").json()] == [inc]


def test_edit_unknown_entry_404(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    assert client.post(f"/api/incidents/{inc}/entries/nope/edit", json={"entry": {}}).status_code == 404


def test_readback_text_endpoint(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    e = _say(client, inc, "aspirin 300 mg PO at 10:42")["entries"][0]
    r = client.get(f"/api/incidents/{inc}/entries/{e['id']}/readback.txt")
    assert r.status_code == 200 and r.text.startswith("Aspirin, three hundred milligrams, by mouth, at 10:42.")
    assert client.get(f"/api/incidents/{inc}/entries/nope/readback.txt").status_code == 404


def test_edit_to_out_of_range_dose_blocks_confirm_until_acknowledged(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    entry = _say(client, inc, "adrenaline 0.3 mg IM two mins ago")["entries"][0]
    assert entry["flags"] == []
    entry["dose_value"]["value"] = 3
    edited = client.post(f"/api/incidents/{inc}/entries/{entry['id']}/edit", json={"entry": entry}).json()["entry"]
    assert [f["code"] for f in edited["flags"]] == ["dose_out_of_range"]
    r = client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [entry["id"]], "acknowledged": []})
    assert r.status_code == 409
    r = client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [entry["id"]], "acknowledged": ["dose_out_of_range"]})
    assert r.status_code == 200


def test_repeat_across_utterances_is_flagged(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    _say(client, inc, "adrenaline 0.3 mg IM at 10 40")
    second = _say(client, inc, "adrenaline 0.3 mg IM at 10 42")["entries"][0]
    assert "repeat_too_soon" in [f["code"] for f in second["flags"]]


def test_confirm_is_bound_to_the_version_seen(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    e = _say(client, inc, "aspirin 300 mg PO two mins ago")["entries"][0]
    seen = client.get(f"/api/incidents/{inc}").json()["entries"][0]["history"][-1]
    e["dose_value"]["value"] = 325
    client.post(f"/api/incidents/{inc}/entries/{e['id']}/edit", json={"entry": e})
    r = client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": [], "expected": {e["id"]: seen}})
    assert r.status_code == 409 and "stale" in str(r.json()["detail"])
    now = client.get(f"/api/incidents/{inc}").json()["entries"][0]["history"][-1]
    assert client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": [], "expected": {e["id"]: now}}).status_code == 200


def test_reject_appends_and_marks_entered_in_error(client, tmp_path):
    inc = client.post("/api/incidents", json={}).json()["id"]
    e = _say(client, inc, "aspirin 300 mg PO two mins ago")["entries"][0]
    before = _rows(tmp_path)
    r = client.post(f"/api/incidents/{inc}/entries/{e['id']}/reject", json={"reason": "said in error"})
    assert r.status_code == 200 and _rows(tmp_path) == before + 1
    s = client.get(f"/api/incidents/{inc}").json()["entries"][0]
    assert s["status"] == "rejected"
    assert client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": []}).status_code == 409
    assert client.get(f"/api/incidents/{inc}/bundle").json()["entry"][0]["resource"]["status"] == "entered-in-error"
    assert client.get("/api/audit/verify").json()["ok"]


def test_rejected_entries_do_not_trigger_repeat_flags(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    first = _say(client, inc, "adrenaline 0.3 mg IM at 10 40")["entries"][0]
    client.post(f"/api/incidents/{inc}/entries/{first['id']}/reject", json={})
    second = _say(client, inc, "adrenaline 0.3 mg IM at 10 42")["entries"][0]
    assert "repeat_too_soon" not in [f["code"] for f in second["flags"]]


def test_device_id_is_stable_and_in_the_bundle(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    _say(client, inc, "aspirin 300 mg PO")
    a = client.get(f"/api/incidents/{inc}/bundle").json()["meta"]["device"]
    b = client.get(f"/api/incidents/{inc}/bundle").json()["meta"]["device"]
    assert a == b and len(a) >= 8
