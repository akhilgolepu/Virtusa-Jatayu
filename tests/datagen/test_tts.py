import io
import wave

import pytest

from datagen.schema import GoldUtterance
from datagen.tts import assign_voices, render_split, synthesize
from datagen.voices import VOICES, voice_by_id

pytestmark = pytest.mark.models


def _utt(i, lang="en", split="dev"):
    return GoldUtterance(id=f"t-{i}", family="t", category="med_basic", split=split, lang=lang,
                         text="gave four milligrams of ondansetron IV", capture_time="2026-10-31T10:45:00+05:30",
                         entries=[])


def test_voice_registry_files_exist():
    assert len(VOICES) >= 14
    for v in VOICES:
        assert v.model_path.exists(), v
    assert {v.accent for v in VOICES} >= {"us", "gb", "in"}


def test_synthesize_16k_mono():
    wav = synthesize(voice_by_id("lessac"), "four milligrams of ondansetron")
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        assert 0.5 < w.getnframes() / 16000 < 6


def test_test_split_gets_three_voices_with_indian():
    for i in range(20):
        vs = assign_voices(_utt(i, split="test"))
        assert len(vs) == 3 and sum(v.accent in ("in", "hi") for v in vs) >= 2 and len({v.id for v in vs}) == 3
    for i in range(10):
        vs = assign_voices(_utt(i, lang="hinglish", split="test"))
        assert all(v.accent in ("in", "hi") for v in vs)
    assert len(assign_voices(_utt(1))) == 1


def test_render_split_resumable(tmp_path):
    utts = [_utt(0), _utt(1)]
    rows = render_split("dev", utts, tmp_path)
    assert len(rows) == 2 and all((tmp_path / r["path"]).exists() for r in rows)
    assert (tmp_path / "dev.jsonl").exists()
    mtimes = [(tmp_path / r["path"]).stat().st_mtime_ns for r in rows]
    again = render_split("dev", utts, tmp_path)
    assert [(tmp_path / r["path"]).stat().st_mtime_ns for r in again] == mtimes


@pytest.mark.parametrize("text,spoken", [
    (".15 milligram adrenalin", "point one five milligram adrenalin"),
    ("adrenaline .5 mg IM", "adrenaline point five mg IM"),
    ("gave 0.3 mg", "gave 0.3 mg"),
    ("given i.m. at 10:42", "given i.m. at 10:42"),
])
def test_speakable_leading_dot_decimals(text, spoken):
    from datagen.tts import speakable
    assert speakable(text) == spoken
