from pathlib import Path

import numpy as np
import pytest

from jatayu.asr import Transcriber
from jatayu.audio import decode_to_16k


@pytest.fixture(scope="module")
def transcriber():
    from jatayu.lexicon import Lexicon

    t = Transcriber(lexicon=Lexicon.load())
    yield t
    t.unload()


@pytest.mark.models
def test_transcribe_fixture(transcriber, no_network):
    samples, _ = decode_to_16k(Path("tests/fixtures/adrenaline.wav").read_bytes())
    r = transcriber.transcribe(samples)
    assert "adrenaline" in r.text.lower() and r.latency_s > 0 and r.device in ("cuda", "cpu")


@pytest.mark.models
def test_silence_gives_empty_text(transcriber):
    r = transcriber.transcribe(np.zeros(16000 * 2, dtype=np.float32))
    assert r.text.strip() == ""
