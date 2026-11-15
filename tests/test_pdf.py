import io

from fastapi.testclient import TestClient
from pypdf import PdfReader

from jatayu.api import create_app


def test_pdf_note_contents(tmp_path):
    c = TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))
    inc = c.post("/api/incidents", json={"label": "RTA NH44"}).json()["id"]
    good = c.post("/api/utterances", data={"incident_id": inc, "text": "aspirin 300 mg PO at 10 40", "extractor": "rules"}).json()
    c.post("/api/utterances", data={"incident_id": inc, "text": "gave morphine", "extractor": "rules"})
    c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [good["entries"][0]["id"]], "acknowledged": []})
    r = c.get(f"/api/incidents/{inc}/note.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    head = c.get("/api/audit").json()[-1]["entry_hash"]
    for needle in ("Device", "RTA NH44", "aspirin", "300", "CONFIRMED", "morphine", "field_missing", head[:12],
                   "Decision-support demo, not a clinical device.", "Chain verified"):
        assert needle in text, needle


def test_pdf_entries_come_from_the_fhir_bundle(tmp_path):
    """The PDF has no path of its own: change a value in the bundle and the PDF shows the changed value."""
    import copy

    from jatayu.audit import AuditLog
    from jatayu.output.pdf import render_note

    c = TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))
    inc = c.post("/api/incidents", json={"label": "same json"}).json()["id"]
    c.post("/api/utterances", data={"incident_id": inc, "text": "aspirin 300 mg PO at 10 40"})
    c.post("/api/utterances", data={"incident_id": inc, "text": "patient allergic to morphine"})
    bundle = c.get(f"/api/incidents/{inc}/bundle").json()
    assert [e["resource"]["status"] for e in bundle["entry"]] == ["in-progress", "not-done"]
    altered = copy.deepcopy(bundle)
    altered["entry"][0]["resource"]["dosage"]["dose"]["value"] = 325
    audit = AuditLog(tmp_path / "j.sqlite")
    pdf = render_note({"id": inc, "label": "same json", "started_at": bundle["timestamp"]}, altered,
                      audit.rows(inc), audit.verify())
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert "325 mg" in text and "300 mg" not in text and "NOT GIVEN" in text
