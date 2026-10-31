"""Synthesise the committed test fixture audio with an offline Piper voice.

Usage: python scripts/make_fixture_wav.py
"""
import wave
from pathlib import Path

from piper import PiperVoice

ROOT = Path(__file__).resolve().parent.parent
VOICE = ROOT / "models/tts/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
FIXTURES = {
    "adrenaline.wav": "Gave zero point three milligrams of adrenaline I M two minutes ago.",
}


def main() -> None:
    voice = PiperVoice.load(VOICE)
    for name, text in FIXTURES.items():
        out = ROOT / "tests/fixtures" / name
        with wave.open(str(out), "wb") as wf:
            voice.synthesize_wav(text, wf)
        print(f"{out.relative_to(ROOT)}: {out.stat().st_size // 1024} KB  <- {text!r}")


if __name__ == "__main__":
    main()
