import json
import subprocess
import sys

from datagen.prompts import make_prompts


def test_make_prompts_quotas_and_coverage(tmp_path):
    subprocess.run([sys.executable, "-m", "datagen.build", "--seed", "1234", "--per-pattern", "4",
                    "--root", str(tmp_path)], check=True, capture_output=True)
    rows = make_prompts(seed=1, root=tmp_path, n_test=40, n_dev=20, min_hinglish=8)
    saved = [json.loads(line) for line in (tmp_path / "recordings" / "prompts.jsonl").read_text().splitlines()]
    assert saved == rows and len(rows) == 60
    assert sum(r["split"] == "test" for r in rows) == 40
    assert sum(r["text"] and r["gold_utt_id"].startswith("hi") for r in rows) >= 8
    assert len({r["prompt_id"] for r in rows}) == 60
    for r in rows:
        for e in r["entries"]:
            for f in (e.get("drug"), e.get("dose_value"), e.get("procedure")):
                if f:
                    assert r["text"][f["span"][0]:f["span"][1]] == f["surface"]
    assert make_prompts(seed=1, root=tmp_path, n_test=40, n_dev=20, min_hinglish=8, force=True) == rows


def test_prompts_are_stable_and_never_silently_overwritten(tmp_path):
    import pytest
    subprocess.run([sys.executable, "-m", "datagen.build", "--seed", "1234", "--per-pattern", "4",
                    "--root", str(tmp_path)], check=True, capture_output=True)
    rows = make_prompts(seed=1, root=tmp_path, n_test=30, n_dev=10, min_hinglish=8)
    assert all(r["prompt_id"] == r["gold_utt_id"] for r in rows)
    with pytest.raises(FileExistsError):
        make_prompts(seed=2, root=tmp_path, n_test=30, n_dev=10, min_hinglish=8)
    assert make_prompts(seed=2, root=tmp_path, n_test=30, n_dev=10, min_hinglish=8, force=True)
