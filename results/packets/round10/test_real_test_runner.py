"""Round 10, item 4: the real-test runner, exercised ONLY on dummy clips in a throwaway folder (tmp_path). It must refuse
unless the tree is clean, the real test manifest hash is frozen and the evaluator's release file names it; it writes
aggregates only — no transcript, no per-clip result."""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import eval.real_test as rt
from datagen.schema import GoldEntry, GoldField, GoldTime

FIXTURE = Path(__file__).parent / "fixtures" / "adrenaline.wav"
SAID = "Gave 0.3 mg of adrenaline IM two minutes ago."


@dataclass
class _Res:
    text: str
    words: list = field(default_factory=list)


class StubASR:
    def __init__(self):
        self.calls = 0

    def transcribe(self, samples):
        self.calls += 1
        return _Res(SAID)


def _gold() -> dict:
    f = lambda v: GoldField(value=v, surface=str(v), span=(0, 1))  # noqa: E731
    return GoldEntry(kind="medication", context="given", drug=f("epinephrine"), dose_value=f(0.3), dose_unit=f("mg"),
                     route=f("IM"), time=GoldTime(kind="relative", offset_s=-120, surface="two minutes ago",
                                                  span=(0, 1))).model_dump(mode="json")


@pytest.fixture
def root(tmp_path):
    from jatayu.audio import decode_to_16k

    base = tmp_path / "data" / "real" / "test"
    (base / "S99").mkdir(parents=True)
    rows = []
    for k in range(3):  # three dummy "takes" of the same fixture clip (bytes differ by a trailing pad)
        wav = decode_to_16k(FIXTURE.read_bytes())[1] + b"\x00\x00" * k
        sha = hashlib.sha256(wav).hexdigest()
        (base / "S99" / f"{sha[:8]}.wav").write_bytes(wav)
        rows.append({"id": f"real-test-S99-{sha[:8]}", "speaker": "S99", "path": f"S99/{sha[:8]}.wav", "sha256": sha,
                     "reference": "gave 0.3 mg adrenaline IM two minutes ago", "entries": [_gold()]})
    (base / "manifest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return tmp_path / "data"


@pytest.fixture
def clean(monkeypatch):
    monkeypatch.setattr(rt, "dirty_paths", lambda: [])


def _release(tmp_path, h, kind="real-test"):
    p = tmp_path / "release.json"
    p.write_text(json.dumps({"release": kind, "manifest_sha256": h, "released_by": "evaluator (dummy)"}))
    return p


def _run(tmp_path, root, release, asr=None):
    return rt.main(["--tag", "dummy-real-test", "--root", str(root), "--release", str(release),
                    "--out", str(tmp_path / "results")], transcriber=asr or StubASR())


def test_refuses_on_a_dirty_tree(tmp_path, root, monkeypatch, capsys):
    monkeypatch.setattr(rt, "dirty_paths", lambda: ["jatayu/extract/rules.py"])
    h = rt.freeze_manifest(root)
    asr = StubASR()
    assert _run(tmp_path, root, _release(tmp_path, h), asr) == 2 and asr.calls == 0
    assert "dirty" in capsys.readouterr().err and not (tmp_path / "results").exists()


def test_refuses_without_a_frozen_manifest_hash(tmp_path, root, clean, capsys):
    assert _run(tmp_path, root, _release(tmp_path, "0" * 64)) == 2
    assert "not frozen" in capsys.readouterr().err


def test_refuses_when_the_manifest_changed_after_freezing(tmp_path, root, clean, capsys):
    h = rt.freeze_manifest(root)
    m = root / "real" / "test" / "manifest.jsonl"
    m.write_text(m.read_text() + m.read_text().splitlines()[0] + "\n")
    assert _run(tmp_path, root, _release(tmp_path, h)) == 2 and "changed" in capsys.readouterr().err


def test_refuses_without_the_release_file_or_with_a_wrong_one(tmp_path, root, clean, capsys):
    h = rt.freeze_manifest(root)
    assert _run(tmp_path, root, tmp_path / "missing.json") == 2 and "no release file" in capsys.readouterr().err
    assert _run(tmp_path, root, _release(tmp_path, "f" * 64)) == 2
    assert _run(tmp_path, root, _release(tmp_path, h, kind="dev")) == 2
    assert not (tmp_path / "results").exists()


def test_a_changed_clip_is_refused_before_scoring(tmp_path, root, clean):
    h = rt.freeze_manifest(root)
    clip = next((root / "real" / "test" / "S99").iterdir())
    clip.write_bytes(clip.read_bytes() + b"\x01")
    with pytest.raises(ValueError, match="changed since import"):
        _run(tmp_path, root, _release(tmp_path, h))


def test_freezing_never_overwrites_a_different_hash(tmp_path, root):
    rt.freeze_manifest(root)
    assert rt.freeze_manifest(root)  # same manifest again: no-op
    m = root / "real" / "test" / "manifest.jsonl"
    m.write_text(m.read_text().splitlines()[0] + "\n")
    with pytest.raises(rt.RealTestRefused, match="never overwritten"):
        rt.freeze_manifest(root)


def test_scores_aggregate_only_and_logs_once(tmp_path, root, clean):
    h = rt.freeze_manifest(root)
    asr = StubASR()
    assert _run(tmp_path, root, _release(tmp_path, h), asr) == 0 and asr.calls == 3
    out = tmp_path / "results" / "dummy-real-test"
    assert sorted(p.name for p in out.iterdir()) == ["metrics.json", "report.md"]
    m = json.loads((out / "metrics.json").read_text())
    assert m["clips"] == 3 and m["speakers"] == 1 and m["manifest_sha256"] == h
    assert m["entity"]["f1"] == 1.0 and m["dangerous_error_r10"]["count"] == 0 and m["dangerous_error_r10"]["denominator"] == 3
    for f in out.iterdir():  # no transcript, no reference text, no clip id anywhere in the output
        text = f.read_text()
        assert SAID not in text and "two minutes ago" not in text and "real-test-S99" not in text
    rows = [json.loads(l) for l in (tmp_path / "results" / "run_log.jsonl").read_text().splitlines()]
    assert [r["split"] for r in rows] == ["real-test"] and rows[0]["manifest_sha256"] == h


@pytest.mark.models
def test_runs_with_the_real_recogniser_on_dummy_clips(tmp_path, root, clean):
    h = rt.freeze_manifest(root)
    assert rt.main(["--tag", "dummy-real-asr", "--root", str(root), "--release", str(_release(tmp_path, h)),
                    "--out", str(tmp_path / "results")]) == 0
    m = json.loads((tmp_path / "results" / "dummy-real-asr" / "metrics.json").read_text())
    assert m["clips"] == 3 and m["drug_term_recall"] == 1.0 and m["wer"] < 0.3
