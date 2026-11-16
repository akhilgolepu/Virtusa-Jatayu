"""Three speakers share the recording: /record?part=N shows one balanced share, and the import labels each share with
its own anonymous speaker id (synthetic prompts in a throwaway folder; no real recording is read)."""
import json
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from jatayu.corpus import assign_parts


def _prompts(n_test=18, n_dev=6):
    out = {}
    conds = ["quiet", "fan", "street", "siren-playback", "fast", "mumbled"]
    for i in range(n_test + n_dev):
        split = "test" if i < n_test else "dev"
        pid = f"{split}-{i:03d}"
        out[pid] = {"prompt_id": pid, "split": split, "lang": "hinglish" if i % 6 == 0 else "en",
                    "condition_hint": conds[i % 6], "text": f"synthetic {i}", "entries": []}
    return out


def test_parts_are_balanced_deterministic_and_cover_every_prompt():
    p = _prompts()
    a = assign_parts(p, 3)
    assert a == assign_parts(dict(reversed(list(p.items()))), 3)  # file order does not matter
    assert set(a) == set(p) and set(a.values()) == {1, 2, 3}
    for k in (1, 2, 3):
        mine = [p[pid] for pid, part in a.items() if part == k]
        assert Counter(x["split"] for x in mine) == {"test": 6, "dev": 2}
    with pytest.raises(ValueError):
        assign_parts(p, 0)


def test_record_page_api_filters_one_part(tmp_path):
    from jatayu.api import create_app

    rec = tmp_path / "rec"
    rec.mkdir()
    (rec / "prompts.jsonl").write_text("".join(json.dumps(x) + "\n" for x in _prompts().values()))
    c = TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=rec))
    every = c.get("/api/corpus/prompts").json()
    parts = [c.get(f"/api/corpus/prompts?part={k}&parts=3").json() for k in (1, 2, 3)]
    assert len(every) == 24 and [len(x) for x in parts] == [8, 8, 8]
    assert sorted(p["prompt_id"] for x in parts for p in x) == sorted(p["prompt_id"] for p in every)
    assert c.get("/api/corpus/prompts?part=4&parts=3").status_code == 422


def test_import_by_part_gives_each_speaker_their_own_takes(tmp_path):
    import wave

    from scripts.import_real import import_recordings, load_real

    root = tmp_path / "data"
    rec = root / "recordings"
    (rec / "audio").mkdir(parents=True)
    prompts = _prompts(n_test=0, n_dev=6)
    takes = []
    for i, pid in enumerate(prompts):
        with wave.open(str(rec / "audio" / f"{pid}__01.wav"), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000), w.writeframes(bytes([i + 1, 0]) * 1600)
        takes.append({"take_id": f"t{i}", "prompt_id": pid, "take": 1, "path": f"audio/{pid}__01.wav",
                      "condition": prompts[pid]["condition_hint"], "gold_text": prompts[pid]["text"], "entries": [],
                      "status": "ok"})
    (rec / "prompts.jsonl").write_text("".join(json.dumps(p) + "\n" for p in prompts.values()))
    (rec / "manifest.jsonl").write_text("".join(json.dumps(t) + "\n" for t in takes))
    parts = assign_parts(prompts, 3)
    for k, speaker in ((1, "S01"), (2, "S02"), (3, "S03")):
        assert import_recordings(speaker, root, part=k, parts=3)["dev"] == 2
    rows = load_real("dev", root)
    assert len(rows) == 6 and all(parts[r["prompt_id"]] == int(r["speaker"][-1]) for r in rows)
