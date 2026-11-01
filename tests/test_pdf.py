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
    for needle in ("RTA NH44", "aspirin", "300", "CONFIRMED", "morphine", "field_missing", head[:12],
                   "Decision-support demo, not a clinical device.", "Chain verified"):
        assert needle in text, needle
