import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jatayu.api import create_app

WAV = Path("tests/fixtures/adrenaline.wav").read_bytes()


@dataclass
class _Asr:
    text: str


class StubTranscriber:
    device = "stub"

    def __init__(self, text):
        self.text = text

    def transcribe(self, samples):
        return _Asr(self.text)


def _prompt(pid="p000", text="gave 4 mg ondansetron IV", split="dev"):
    def f(value, surface):
        s = text.index(surface)
        return {"value": value, "surface": surface, "span": [s, s + len(surface)]}
    return {"prompt_id": pid, "split": split, "text": text, "gold_utt_id": "x-0-000", "condition_hint": "quiet",
            "entries": [{"kind": "medication", "context": "given", "drug": f("ondansetron", "ondansetron"),
                         "dose_value": f(4.0, "4"), "dose_unit": f("mg", "mg"), "route": f("IV", "IV"),
                         "time": {"kind": "none"}}]}


def _client(tmp_path, asr_text):
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "prompts.jsonl").write_text(json.dumps(_prompt()) + "\n")
    app = create_app(db_path=tmp_path / "a.sqlite", audio_dir=tmp_path / "audio", recordings_dir=rec,
                     transcriber=StubTranscriber(asr_text))
    return TestClient(app), rec


def _upload(client, pid="p000"):
    return client.post("/api/corpus/recordings", data={"prompt_id": pid, "condition": "quiet"},
                       files={"audio": ("t.webm", WAV, "audio/wav")})


def test_upload_ok_status(tmp_path):
    client, rec = _client(tmp_path, "Gave four milligrams ondansetron IV.")
    row = _upload(client).json()
    assert row["status"] == "ok" and row["wer"] == 0.0 and row["take"] == 1
    assert (rec / row["path"]).exists()
    assert client.get("/api/corpus/prompts?status=todo").json() == []


def test_upload_review_status_on_mismatch(tmp_path):
    client, _ = _client(tmp_path, "something else entirely")
    row = _upload(client).json()
    assert row["status"] == "review" and row["wer"] > 0.4
    assert [p["prompt_id"] for p in client.get("/api/corpus/prompts?status=review").json()] == ["p000"]


def test_takes_never_overwrite(tmp_path):
    client, rec = _client(tmp_path, "gave 4 mg ondansetron IV")
    a, b = _upload(client).json(), _upload(client).json()
    assert (a["take"], b["take"]) == (1, 2) and a["path"] != b["path"]
    assert (rec / a["path"]).exists() and (rec / b["path"]).exists()
    assert len((rec / "manifest.jsonl").read_text().splitlines()) == 2


def test_keep_edited_realigns_spans(tmp_path):
    client, _ = _client(tmp_path, "uh gave 4 mg of ondansetron IV")
    take = _upload(client).json()
    edited = "uh gave 4 mg of ondansetron IV"
    row = client.post(f"/api/corpus/recordings/{take['take_id']}/resolve",
                      json={"action": "keep_edited", "gold_text": edited}).json()
    assert row["status"] == "keep_edited" and row["gold_text"] == edited
    for name in ("drug", "dose_value", "dose_unit", "route"):
        f = row["entries"][0][name]
        assert edited[f["span"][0]:f["span"][1]] == f["surface"]


def test_keep_edited_missing_surface_needs_annotation(tmp_path):
    client, _ = _client(tmp_path, "gave ondansetron IV")
    take = _upload(client).json()
    row = client.post(f"/api/corpus/recordings/{take['take_id']}/resolve",
                      json={"action": "keep_edited", "gold_text": "gave ondansetron IV"}).json()
    assert row["status"] == "needs_annotation"


def test_rerecord_puts_prompt_back_in_todo(tmp_path):
    client, _ = _client(tmp_path, "nothing like it")
    take = _upload(client).json()
    client.post(f"/api/corpus/recordings/{take['take_id']}/resolve", json={"action": "rerecord"})
    assert [p["prompt_id"] for p in client.get("/api/corpus/prompts?status=todo").json()] == ["p000"]


def test_unknown_prompt_404(tmp_path):
    client, _ = _client(tmp_path, "x")
    assert _upload(client, pid="nope").status_code == 404


def test_stats(tmp_path):
    client, _ = _client(tmp_path, "gave 4 mg ondansetron IV")
    _upload(client)
    s = client.get("/api/corpus/stats").json()
    assert s["prompts"] == 1 and s["by_status"]["ok"] == 1 and s["by_condition"]["quiet"] == 1


def test_record_page_offline(tmp_path):
    # /record is a route of the DOT single-page app since Phase 3 (the Phase 2 page lives on as the fallback).
    client, _ = _client(tmp_path, "x")
    html = client.get("/record").text
    assert "Decision-support demo, not a clinical device." in html
    assert not re.search(r"(src|href)=\"https?://", html)


def _entries_for(text, fields):
    out = {"kind": "medication", "context": "given", "time": {"kind": "none"}}
    for name, (value, surface) in fields.items():
        s = text.index(surface)
        out[name] = {"value": value, "surface": surface, "span": [s, s + len(surface)]}
    return [out]


def test_realign_never_matches_inside_a_longer_token():
    from jatayu.corpus import realign
    e = _entries_for("gave 1 mg of atropine", {"dose_value": (1.0, "1"), "dose_unit": ("mg", "mg"),
                                                "drug": ("atropine", "atropine")})
    assert realign(e, "gave 10 mg of atropine") is None
    g = _entries_for("1 g of TXA", {"dose_value": (1.0, "1"), "dose_unit": ("g", "g"), "drug": ("tranexamic acid", "TXA")})
    assert realign(g, "1 mg of TXA") is None
    ok = realign(e, "uh gave 1 mg of atropine")
    assert ok is not None and ok[0]["dose_value"]["span"] == [8, 9]


def test_changed_dose_forces_review_despite_low_wer(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir()
    text = "gave 0.5 mg of glucagon IM two minutes ago please"
    prompt = {"prompt_id": "p000", "split": "dev", "text": text, "gold_utt_id": "x-0-000", "condition_hint": "quiet",
              "entries": _entries_for(text, {"dose_value": (0.5, "0.5"), "dose_unit": ("mg", "mg"),
                                             "drug": ("glucagon", "glucagon"), "route": ("IM", "IM")})}
    (rec / "prompts.jsonl").write_text(json.dumps(prompt) + "\n")
    app = create_app(db_path=tmp_path / "a.sqlite", audio_dir=tmp_path / "audio", recordings_dir=rec,
                     transcriber=StubTranscriber("gave 5 mg of glucagon IM two minutes ago please"))
    row = TestClient(app).post("/api/corpus/recordings", data={"prompt_id": "p000", "condition": "quiet"},
                               files={"audio": ("t.wav", WAV, "audio/wav")}).json()
    assert row["wer"] <= 0.4 and row["status"] == "review" and row["gold_field_mismatch"] == ["dose_value"]


def test_test_take_is_sealed_and_never_transcribed(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "prompts.jsonl").write_text(json.dumps(_prompt(split="test")) + "\n")

    class Boom:
        device = "stub"

        def transcribe(self, samples):
            raise AssertionError("a sealed test take must not be transcribed")
    client = TestClient(create_app(db_path=tmp_path / "a.sqlite", audio_dir=tmp_path / "audio", recordings_dir=rec,
                                   transcriber=Boom()))
    row = _upload(client).json()
    assert row["status"] == "sealed" and row["asr_text"] is None and row["wer"] is None
    assert (rec / row["path"]).exists()
