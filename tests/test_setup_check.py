import json

import pytest

from jatayu import config

pytestmark = [pytest.mark.models, pytest.mark.skipif(not config.LLM_MODEL_PATH.exists(), reason="LLM not downloaded")]


def test_setup_check_writes_every_item(tmp_path):
    from scripts.setup_check import main
    out = tmp_path / "setup_check.json"
    code = main(["--out", str(out)])
    data = json.loads(out.read_text())
    assert set(data["checks"]) >= {"gpu", "asr", "llm", "tts", "offline"}
    for name, c in data["checks"].items():
        assert "pass" in c and "detail" in c, name
    assert data["checks"]["asr"]["latency_s"] > 0 and data["checks"]["llm"]["tokens"] > 0
    assert data["checks"]["llm"]["peak_vram_mib"] > 0
    assert data["checks"]["offline"]["sockets_blocked"] is True
    assert code == (0 if data["all_pass"] else 1)
