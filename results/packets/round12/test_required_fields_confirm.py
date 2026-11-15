"""Round 12, item 2 (no fix this round): can an entry with a dose but no unit, or with no drug, be confirmed without an
explicit entry or an explicit "unknown"?

The requirement is written as tests marked xfail(strict=True): they FAIL today, which records that it is NOT enforced,
and they will turn into errors the day it is (strict), so the change cannot go unnoticed. The plain tests next to them
pin down exactly what happens today."""
import pytest
from fastapi.testclient import TestClient

from jatayu.api import create_app


def _client(tmp_path):
    return TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))


def _entry(c, inc, text):
    [e] = c.post("/api/utterances", data={"incident_id": inc, "text": text}).json()["entries"]
    return e


def _confirm(c, inc, e, ack):
    return c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": ack})


# ---- a dose with no unit ----------------------------------------------------------------------------------------
def test_today_dose_without_unit_needs_a_tick_and_nothing_more(tmp_path):
    c = _client(tmp_path)
    inc = c.post("/api/incidents", json={}).json()["id"]
    e = _entry(c, inc, "gave aspirin 300 PO")
    assert e["dose_value"]["value"] == 300 and e["dose_unit"]["value"] is None
    assert any(f["code"] == "field_missing" and f["field"] == "dose_unit" and f["severity"] == "high" for f in e["flags"])
    assert _confirm(c, inc, e, []).status_code == 409  # not silently: the high flag must be ticked ...
    assert _confirm(c, inc, e, ["field_missing"]).status_code == 200  # ... but ticking it is enough: unit stays empty
    state = c.get(f"/api/incidents/{inc}").json()["entries"][0]
    assert state["status"] == "confirmed" and state["entry"]["dose_unit"]["value"] is None


@pytest.mark.xfail(strict=True, reason="NOT ENFORCED (round 12): a tick on field_missing confirms a dose with no unit; "
                                       "no unit entry or explicit 'unknown' is required")
def test_required_dose_without_unit_cannot_be_confirmed_by_a_tick_alone(tmp_path):
    c = _client(tmp_path)
    inc = c.post("/api/incidents", json={}).json()["id"]
    e = _entry(c, inc, "gave aspirin 300 PO")
    assert _confirm(c, inc, e, ["field_missing"]).status_code == 409


# ---- an entry with no drug ---------------------------------------------------------------------------------------
def _drugless(c, inc):
    e = _entry(c, inc, "gave ondansetron 4 mg IV")
    edited = c.post(f"/api/incidents/{inc}/entries/{e['id']}/edit",
                    json={"entry": {**e, "drug": {**e["drug"], "value": None}}})
    assert edited.status_code == 200
    return edited.json()["entry"]


def test_today_an_entry_with_no_drug_confirms_without_any_tick(tmp_path):
    """The extractors never create a medication without a drug; an edit can blank it, and nothing then flags it."""
    c = _client(tmp_path)
    inc = c.post("/api/incidents", json={}).json()["id"]
    e = _drugless(c, inc)
    assert e["drug"]["value"] is None and not [f for f in e["flags"] if f["severity"] == "high"]
    assert _confirm(c, inc, e, []).status_code == 200


@pytest.mark.xfail(strict=True, reason="NOT ENFORCED (round 12): an entry whose drug is empty is confirmed with no tick "
                                       "and no explicit drug or 'unknown'")
def test_required_entry_with_no_drug_cannot_be_confirmed(tmp_path):
    c = _client(tmp_path)
    inc = c.post("/api/incidents", json={}).json()["id"]
    assert _confirm(c, inc, _drugless(c, inc), []).status_code == 409


def test_today_the_ui_offers_no_explicit_unknown():
    from pathlib import Path

    card = Path(__file__).resolve().parents[1].joinpath("web/src/components/EntryCard.tsx").read_text()
    import re
    options = re.findall(r'<option value="([^"]*)">([^<]*)</option>', card)
    assert ("", "not stated") in options  # the unit and route lists offer only "not stated" besides real values
    assert not any("unknown" in v.lower() or "unknown" in label.lower() for v, label in options)
    edit_fields = [w.lower() for w in re.findall(r"<label><span class=\"label\">(\w+)", card)]
    assert edit_fields == ["dose", "unit", "route"]  # the edit form has no drug field at all
