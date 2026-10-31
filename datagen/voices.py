"""Piper voice registry: 14 English voice/speaker combinations (US, GB, Indian-accented) + 3 Hindi voices."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from jatayu import config

TTS = config.MODELS_DIR / "tts"


@dataclass(frozen=True)
class Voice:
    id: str
    model_path: Path
    speaker_id: int | None
    accent: Literal["us", "gb", "in", "hi"]


def _p(rel: str) -> Path:
    return TTS / rel


VOICES: list[Voice] = [
    Voice("lessac", _p("en/en_US/lessac/medium/en_US-lessac-medium.onnx"), None, "us"),
    Voice("ryan", _p("en/en_US/ryan/medium/en_US-ryan-medium.onnx"), None, "us"),
    Voice("amy", _p("en/en_US/amy/medium/en_US-amy-medium.onnx"), None, "us"),
    Voice("kusal", _p("en/en_US/kusal/medium/en_US-kusal-medium.onnx"), None, "us"),
    Voice("libritts_r-0", _p("en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx"), 0, "us"),
    Voice("alan", _p("en/en_GB/alan/medium/en_GB-alan-medium.onnx"), None, "gb"),
    Voice("southern_female", _p("en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx"),
          None, "gb"),
    # L2-ARCTIC Hindi-L1 speakers and VCTK Indian-accented speakers (ids from the models' speaker_id_map).
    Voice("l2arctic-ASI", _p("en/en_US/l2arctic/medium/en_US-l2arctic-medium.onnx"), 10, "in"),
    Voice("l2arctic-RRBI", _p("en/en_US/l2arctic/medium/en_US-l2arctic-medium.onnx"), 19, "in"),
    Voice("l2arctic-SVBI", _p("en/en_US/l2arctic/medium/en_US-l2arctic-medium.onnx"), 2, "in"),
    Voice("l2arctic-TNI", _p("en/en_US/l2arctic/medium/en_US-l2arctic-medium.onnx"), 9, "in"),
    Voice("vctk-p248", _p("en/en_GB/vctk/medium/en_GB-vctk-medium.onnx"), 87, "in"),
    Voice("vctk-p251", _p("en/en_GB/vctk/medium/en_GB-vctk-medium.onnx"), 92, "in"),
    Voice("vctk-p376", _p("en/en_GB/vctk/medium/en_GB-vctk-medium.onnx"), 26, "in"),
]

HINDI_VOICES: list[Voice] = [
    Voice("hi-pratham", _p("hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx"), None, "hi"),
    Voice("hi-priyamvada", _p("hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium.onnx"), None, "hi"),
    Voice("hi-rohan", _p("hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx"), None, "hi"),
]

# Set by the Task 5 spike (Hindi voices reading romanised Hinglish): see datagen/README.md.
USE_HINDI_VOICES = False


def voice_by_id(voice_id: str) -> Voice:
    for v in VOICES + HINDI_VOICES:
        if v.id == voice_id:
            return v
    raise KeyError(voice_id)
