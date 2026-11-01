import pytest

from jatayu import config
from jatayu.llm import LlmError, LlmRunner

needs_llm = pytest.mark.skipif(not config.LLM_MODEL_PATH.exists(), reason="LLM not downloaded")


def test_missing_model_raises_llm_error(tmp_path):
    with pytest.raises(LlmError):
        LlmRunner(tmp_path / "nope.gguf").complete_json("s", "u", {"type": "object"})


@needs_llm
@pytest.mark.models
def test_llm_json_follows_schema():
    r = LlmRunner(config.LLM_MODEL_PATH)
    schema = {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}
    assert r.complete_json("Answer in JSON.", "Return n=7.", schema) == {"n": 7}


@needs_llm
@pytest.mark.models
def test_llm_quotes_cleanly_with_chatml():
    r = LlmRunner(config.LLM_MODEL_PATH)
    schema = {"type": "object", "properties": {"drugs": {"type": "array", "items": {"type": "string"}}},
              "required": ["drugs"]}
    out = r.complete_json("List every drug name exactly as written in the transcript.",
                          "Transcript: gave 0.3 mg adrenaline IM and 4 mg ondansetron IV", schema)
    assert [d.lower() for d in out["drugs"]] == ["adrenaline", "ondansetron"]
