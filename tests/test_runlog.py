import json

import pytest

from eval import runlog


def test_sealed_split_refused_on_dirty_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "dirty_paths", lambda: ["jatayu/validate.py"])
    for split in ("test", "final_test"):
        with pytest.raises(runlog.DirtyTreeError):
            runlog.log_run(tmp_path, split=split, tag="x")
    assert not (tmp_path / "run_log.jsonl").exists()  # a refused run is not logged as a run
    row = runlog.log_run(tmp_path, split="dev", tag="x")
    assert row["dirty"] is True and row["commit"].endswith("-dirty") and row["dirty_paths"] == ["jatayu/validate.py"]


def test_clean_tree_runs_sealed_split(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "dirty_paths", lambda: [])
    row = runlog.log_run(tmp_path, split="test", tag="x")
    assert row["dirty"] is False and not row["commit"].endswith("-dirty")
    assert json.loads((tmp_path / "run_log.jsonl").read_text())["split"] == "test"


def test_results_do_not_make_the_tree_dirty(monkeypatch):
    class P:
        stdout = " M results/run_log.jsonl\n?? results/new-run/metrics.json\n M eval/run.py\n"
    monkeypatch.setattr(runlog.subprocess, "run", lambda *a, **k: P())
    assert runlog.dirty_paths() == ["eval/run.py"]
