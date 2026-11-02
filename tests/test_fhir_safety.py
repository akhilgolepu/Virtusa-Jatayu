"""An utterance that says a drug was NOT given (or is a reading) must never become a completed administration,
in the FHIR-lite bundle or in the PDF, even after the medic confirms it (evaluator round 3, item 10)."""
import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from jatayu.api import create_app
from jatayu.output.fhir import to_bundle, validate_bundle


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))


@pytest.mark.parametrize("text,flag,reason", [
    ("patient allergic to morphine", "possible_not_given", "Not given"),
    ("did not give aspirin 300 mg", "possible_not_given", "Not given"),
    ("patient refused ondansetron", "possible_not_given", "Not given"),
    ("blood glucose 3.2 mmol", "possible_measurement", "A reading"),
])
def test_context_flagged_entry_is_not_done_after_confirm(client, text, flag, reason):
    inc = client.post("/api/incidents", json={"label": "safety"}).json()["id"]
    [e] = client.post("/api/utterances", data={"incident_id": inc, "text": text, "extractor": "rules"}).json()["entries"]
    assert flag in [f["code"] for f in e["flags"]]
    draft = client.get(f"/api/incidents/{inc}/bundle").json()["entry"][0]["resource"]
    assert draft["status"] == "not-done" and draft["statusReason"][0]["text"].startswith(reason)
    high = [f["code"] for f in e["flags"] if f["severity"] == "high"]
    assert client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": high}).status_code == 200
    res = client.get(f"/api/incidents/{inc}/bundle").json()["entry"][0]["resource"]
    assert res["status"] == "not-done" and res["status"] != "completed"
    assert res["statusReason"][0]["text"].startswith(reason)
    pdf = client.get(f"/api/incidents/{inc}/note.pdf").content
    text_pdf = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert ("NOT GIVEN" if flag == "possible_not_given" else "READING") in text_pdf


def test_given_entry_still_completes(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    [e] = client.post("/api/utterances", data={"incident_id": inc, "text": "aspirin 300 mg PO at 10 40",
                                               "extractor": "rules"}).json()["entries"]
    client.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": []})
    res = client.get(f"/api/incidents/{inc}/bundle").json()["entry"][0]["resource"]
    assert res["status"] == "completed" and "statusReason" not in res


def test_rejected_context_entry_stays_entered_in_error(client):
    inc = client.post("/api/incidents", json={}).json()["id"]
    [e] = client.post("/api/utterances", data={"incident_id": inc, "text": "patient allergic to morphine",
                                               "extractor": "rules"}).json()["entries"]
    assert client.post(f"/api/incidents/{inc}/entries/{e['id']}/reject", json={}).status_code == 200
    res = client.get(f"/api/incidents/{inc}/bundle").json()["entry"][0]["resource"]
    assert res["status"] == "entered-in-error"


def test_single_utterance_bundle_marks_not_done(lexicon, sample_utterance):
    from jatayu.extract.rules import RulesExtractor

    entries = RulesExtractor(lexicon).extract("known allergy to morphine, not given", sample_utterance.capture_time)
    b = to_bundle(sample_utterance, entries, lexicon)
    validate_bundle(b)
    assert b["entry"][0]["resource"]["status"] == "not-done"
