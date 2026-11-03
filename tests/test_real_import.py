import json
import wave

import numpy as np
import pytest

from scripts.import_real import import_clips, load_real


def _wav(path, seconds=1.0, rate=22050, freq=440):
    t = np.arange(int(seconds * rate)) / rate
    pcm = (0.2 * np.sin(2 * np.pi * freq * t) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm.tobytes())  # noqa: E702


def _refs(tmp_path, n=2):
    lines = []
    for i in range(n):
        p = tmp_path / f"take{i}.wav"
        _wav(p, freq=440 + 100 * i)
        lines.append(f"{p}\tgave {i + 1} mg morphine IV")
    refs = tmp_path / "refs.tsv"
    refs.write_text("\n".join(lines) + "\n")
    return refs


def test_import_writes_16k_mono_clips_and_a_manifest(tmp_path):
    root = tmp_path / "data"
    added = import_clips("dev", "S01", _refs(tmp_path), root)
    assert len(added) == 2
    rows = load_real("dev", root)
    assert [r["speaker"] for r in rows] == ["S01", "S01"] and rows[0]["reference"] == "gave 1 mg morphine IV"
    with wave.open(str(root / "real" / "dev" / rows[0]["path"])) as w:
        assert (w.getframerate(), w.getnchannels()) == (16000, 1)
    assert len((root / "real" / "dev" / "manifest.sha256").read_text().splitlines()) == 2
    assert import_clips("dev", "S01", tmp_path / "refs.tsv", root) == []  # same audio again: no-op


def test_real_test_clips_are_sealed(tmp_path):
    root = tmp_path / "data"
    import_clips("test", "S02", _refs(tmp_path, 1), root)
    with pytest.raises(PermissionError):
        load_real("test", root)
    assert len(load_real("test", root, sealed_ok=True)) == 1


def test_changed_clip_is_detected(tmp_path):
    root = tmp_path / "data"
    import_clips("dev", "S01", _refs(tmp_path, 1), root)
    clip = next((root / "real" / "dev" / "S01").glob("*.wav"))
    clip.write_bytes(clip.read_bytes()[:-10] + b"\0" * 10)
    with pytest.raises(ValueError):
        load_real("dev", root)


def test_speaker_id_must_be_anonymous_token(tmp_path):
    with pytest.raises(ValueError):
        import_clips("dev", "Akhil G", _refs(tmp_path, 1), tmp_path / "data")


def test_real_wer_refuses_test_and_reports_zero_clips(tmp_path, monkeypatch):
    from eval import real_wer, runlog
    monkeypatch.setattr(runlog, "dirty_paths", lambda: [])
    piper = tmp_path / "piper"
    piper.mkdir()
    (piper / "metrics.json").write_text(json.dumps({"config": {"n_clips": 3}, "asr": {"wer": 0.4, "wer_raw": 0.6,
                                                                                    "drug_term_recall": 0.5}}))
    with pytest.raises(PermissionError):
        real_wer.main(["--tag", "x", "--piper", str(piper), "--split", "test", "--root", str(tmp_path / "data"),
                       "--out", str(tmp_path / "out")])
    real_wer.main(["--tag", "y", "--piper", str(piper), "--root", str(tmp_path / "data"), "--out", str(tmp_path / "out")])
    assert "No real dev recordings" in (tmp_path / "out" / "y" / "report.md").read_text()


def test_audio_manifest_freeze_and_verify(tmp_path):
    from datagen.audio_manifest import build, freeze, verify
    root = tmp_path / "data"
    for sub in ("tts", "noisy"):
        (root / "audio" / sub / "test").mkdir(parents=True)
        _wav(root / "audio" / sub / "test" / "a.wav")
        (root / "audio" / sub / "test.jsonl").write_text(json.dumps({"path": "test/a.wav"}) + "\n")
    (root / "frozen.sha256").write_text("")
    build("test", root)
    freeze("test", root)
    verify("test", root)
    clip = root / "audio" / "noisy" / "test" / "a.wav"
    clip.write_bytes(clip.read_bytes()[:-4] + b"\1\1\1\1")
    with pytest.raises(ValueError, match="audio changed"):
        verify("test", root)
