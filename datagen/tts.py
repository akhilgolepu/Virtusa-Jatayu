"""Render utterances to 16 kHz mono WAV with Piper (offline). Resumable: existing files are kept."""
from __future__ import annotations

import hashlib
import io
import json
import wave
from functools import lru_cache
from pathlib import Path

from datagen.schema import GoldUtterance
from datagen.voices import HINDI_VOICES, USE_HINDI_VOICES, VOICES, Voice
from jatayu.audio import decode_to_16k


@lru_cache(maxsize=8)
def _load(model_path: Path):
    from piper import PiperVoice

    return PiperVoice.load(model_path)


def synthesize(voice: Voice, text: str) -> bytes:
    from piper.config import SynthesisConfig

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        _load(voice.model_path).synthesize_wav(text, wf, syn_config=SynthesisConfig(speaker_id=voice.speaker_id))
    _, wav16 = decode_to_16k(buf.getvalue())
    return wav16


def _h(*parts: str) -> int:
    return int.from_bytes(hashlib.sha256(":".join(parts).encode()).digest()[:8], "big")


def assign_voices(utt: GoldUtterance) -> list[Voice]:
    """train/dev: one voice. test: three distinct voices, at least two Indian-accented; Hinglish lines get
    Indian-accented (and, if enabled, Hindi) voices only."""
    indian = [v for v in VOICES if v.accent == "in"] + (HINDI_VOICES if USE_HINDI_VOICES else [])
    western = [v for v in VOICES if v.accent in ("us", "gb")]
    pool_all = indian if utt.lang == "hinglish" else VOICES
    if utt.split != "test":
        return [pool_all[_h(utt.id) % len(pool_all)]]
    first_pool = indian if utt.lang == "hinglish" else western
    first = first_pool[_h(utt.id, "a") % len(first_pool)]
    rest = [v for v in indian if v.id != first.id]
    second = rest[_h(utt.id, "b") % len(rest)]
    rest = [v for v in rest if v.id != second.id]
    third = rest[_h(utt.id, "c") % len(rest)]
    return [first, second, third]


def render_split(split: str, utts: list[GoldUtterance], out_root: Path) -> list[dict]:
    """Writes <out_root>/<split>/<utt_id>__<voice>.wav and <out_root>/<split>.jsonl; paths are relative."""
    out_root = Path(out_root)
    (out_root / split).mkdir(parents=True, exist_ok=True)
    rows = []
    for utt in utts:
        for voice in assign_voices(utt):
            rel = Path(split) / f"{utt.id}__{voice.id}.wav"
            path = out_root / rel
            if not path.exists():
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(synthesize(voice, utt.text))
                tmp.replace(path)  # atomic: an interrupted run never leaves a half-written WAV
            with wave.open(str(path)) as w:
                duration = w.getnframes() / w.getframerate()
            rows.append({"utt_id": utt.id, "voice": voice.id, "accent": voice.accent, "path": str(rel),
                         "duration_s": round(duration, 3), "lang": utt.lang})
    (out_root / f"{split}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return rows
