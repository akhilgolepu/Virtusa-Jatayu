"""Phase 3 gate: the whole demo flow, offline, through the real models."""
import io
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from jatayu import config
from jatayu.api import create_app

pytestmark = [pytest.mark.models,
              pytest.mark.skipif(not config.LLM_MODEL_PATH.exists(), reason="LLM not downloaded")]


def test_demo_flow_offline(tmp_path, no_network):
    db = tmp_path / "demo.sqlite"
    c = TestClient(create_app(db_path=db, audio_dir=tmp_path / "audio", recordings_dir=tmp_path / "rec"))
    inc = c.post("/api/incidents", json={"label": "Demo: RTA"}).json()["id"]

    r = c.post("/api/utterances", data={"incident_id": inc, "extractor": "hybrid"},
               files={"audio": ("a.wav", Path("tests/fixtures/adrenaline.wav").read_bytes(), "audio/wav")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["warnings"] == [] and body["asr"]["device"] in ("cuda", "cpu")
    [e] = body["entries"]
    assert (e["drug"]["value"], e["dose_value"]["value"], e["dose_unit"]["value"], e["route"]["value"]) == \
        ("epinephrine", 0.3, "mg", "IM")
    assert e["drug"]["source"] == "llm" and e["flags"] == []

    e["dose_value"]["value"] = 3
    edited = c.post(f"/api/incidents/{inc}/entries/{e['id']}/edit", json={"entry": e}).json()["entry"]
    assert [f["code"] for f in edited["flags"]] == ["dose_out_of_range"]
    assert c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": []}).status_code == 409
    assert c.post(f"/api/incidents/{inc}/confirm",
                  json={"entry_ids": [e["id"]], "acknowledged": ["dose_out_of_range"]}).status_code == 200

    bundle = c.get(f"/api/incidents/{inc}/bundle").json()
    assert bundle["entry"][0]["resource"]["status"] == "completed"
    assert bundle["entry"][0]["resource"]["dosage"]["dose"] == {"value": 3.0, "unit": "mg"}

    pdf = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(c.get(f"/api/incidents/{inc}/note.pdf").content)).pages)
    assert "epinephrine" in pdf and "CONFIRMED" in pdf and "dose_out_of_range" in pdf

    wav = c.get(f"/api/incidents/{inc}/entries/{e['id']}/readback.wav").content
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getframerate() == 16000 and w.getnframes() > 16000

    assert c.get("/api/audit/verify").json() == {"ok": True, "checked": 3, "first_bad_seq": None, "reason": None}
    subprocess.run([sys.executable, "scripts/tamper.py", "--db", str(db), "--seq", "1", "--dose", "0.5"], check=True)
    v = c.get("/api/audit/verify").json()
    assert not v["ok"] and v["first_bad_seq"] == 1
