"""Decode any uploaded audio (wav/webm/ogg/mp3...) to 16 kHz mono float32 plus canonical WAV bytes."""
from __future__ import annotations

import io
import wave

import numpy as np

SAMPLE_RATE = 16000


def decode_to_16k(data: bytes) -> tuple[np.ndarray, bytes]:
    from faster_whisper import decode_audio  # PyAV under the hood; no ffmpeg binary needed

    try:
        samples = decode_audio(io.BytesIO(data), sampling_rate=SAMPLE_RATE)
    except Exception as exc:
        raise ValueError("could not decode audio") from exc
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)

    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return samples, buf.getvalue()
