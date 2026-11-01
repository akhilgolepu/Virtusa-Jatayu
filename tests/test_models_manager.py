from jatayu.models_manager import ModelManager


def _mgr(keep):
    calls = []
    loaders = {n: (lambda n=n: calls.append(("load", n)) or f"<{n}>") for n in ("asr", "llm")}
    unloaders = {n: (lambda obj, n=n: calls.append(("unload", n))) for n in ("asr", "llm")}
    return ModelManager(loaders, unloaders, keep_all=keep), calls


def test_manager_swaps_by_default():
    m, calls = _mgr(keep=False)
    assert m.get("asr") == "<asr>" and m.get("llm") == "<llm>" and m.get("llm") == "<llm>"
    assert calls == [("load", "asr"), ("unload", "asr"), ("load", "llm")]
    assert m.loaded == ["llm"]


def test_manager_keep_all():
    m, calls = _mgr(keep=True)
    m.get("asr"); m.get("llm"); m.get("asr")
    assert calls == [("load", "asr"), ("load", "llm")] and sorted(m.loaded) == ["asr", "llm"]
