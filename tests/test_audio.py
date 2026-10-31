import io
import wave
from pathlib import Path

import numpy as np
import pytest

from jatayu.audio import decode_to_16k


def test_decode_wav_roundtrip():
    data = Path("tests/fixtures/adrenaline.wav").read_bytes()
    samples, wav = decode_to_16k(data)
    assert samples.dtype == np.float32 and samples.ndim == 1 and 1.5 < len(samples) / 16000 < 10
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)


def test_decode_rejects_garbage():
    with pytest.raises(ValueError):
        decode_to_16k(b"not audio")
