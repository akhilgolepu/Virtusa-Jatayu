import json
import subprocess
import sys

import pytest

from jatayu import config


@pytest.fixture(autouse=True)
def _clean_tree(monkeypatch):
    """The dirty-tree refusal is tested in test_runlog.py; here the harness runs on a temporary data root."""
    from eval import runlog
    monkeypatch.setattr(runlog, "dirty_paths", lambda: [])



@pytest.fixture(scope="module")
def tiny_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    subprocess.run([sys.executable, "-m", "datagen.build", "--seed", "1234", "--per-pattern", "1", "--root", str(root)],
                   check=True, capture_output=True)
    return root


def test_text_eval_writes_the_evidence_files(tiny_root, tmp_path):
    from eval.run import main
    assert main(["--split", "dev", "--tag", "t1", "--extractor", "rules", "--mode", "text",
                 "--root", str(tiny_root), "--out", str(tmp_path)]) == 0
    out = tmp_path / "t1"
    m = json.loads((out / "metrics.json").read_text())
    assert m["config"]["split"] == "dev" and m["config"]["extractor"] == "rules" and m["config"]["n_utterances"] > 0
    assert 0 <= m["metrics"]["entity"]["micro"]["f1"] <= 1
    assert "count" in m["metrics"]["dangerous_error"] and m["latency_s"]["p50"] >= 0
    assert "Entity F1" in (out / "report.md").read_text()
    assert (out / "errors.jsonl").exists()


def test_test_split_records_its_frozen_hash_and_final_test_is_refused(tiny_root, tmp_path):
    from eval.run import main
    main(["--split", "test", "--tag", "t2", "--extractor", "rules", "--root", str(tiny_root), "--out", str(tmp_path)])
    m = json.loads((tmp_path / "t2" / "metrics.json").read_text())
    assert len(m["config"]["split_sha256"]) == 64
    with pytest.raises(PermissionError):
        main(["--split", "final_test", "--tag", "t3", "--root", str(tiny_root), "--out", str(tmp_path)])


def test_template_disjointness_is_checked_and_reported(tiny_root, tmp_path):
    from eval.run import main
    main(["--split", "dev", "--tag", "t4", "--extractor", "rules", "--root", str(tiny_root), "--out", str(tmp_path)])
    m = json.loads((tmp_path / "t4" / "metrics.json").read_text())
    assert m["leakage"]["test_families_in_train_or_dev"] == 0 and m["leakage"]["test_patterns_in_final_test"] == 0


@pytest.mark.models
def test_audio_mode_on_real_data(tmp_path):
    from eval.run import main
    if not (config.DATA_DIR / "audio/tts/dev.jsonl").exists():
        pytest.skip("no rendered audio")
    assert main(["--split", "dev", "--tag", "a1", "--extractor", "rules", "--mode", "audio", "--limit", "4",
                 "--out", str(tmp_path)]) == 0
    m = json.loads((tmp_path / "a1" / "metrics.json").read_text())
    assert 0 <= m["asr"]["wer"] <= 2 and 0 <= m["asr"]["drug_term_recall"] <= 1


def test_every_run_is_logged_with_split_tag_and_start_commit(tiny_root, tmp_path):
    from eval.run import main
    main(["--split", "dev", "--tag", "log1", "--extractor", "rules", "--root", str(tiny_root), "--out", str(tmp_path)])
    main(["--split", "test", "--tag", "log2", "--extractor", "rules", "--root", str(tiny_root), "--out", str(tmp_path)])
    rows = [json.loads(l) for l in (tmp_path / "run_log.jsonl").read_text().splitlines()]
    assert [(r["split"], r["tag"]) for r in rows] == [("dev", "log1"), ("test", "log2")]
    assert all(r["commit"] and r["timestamp"] and r["runner"] == "eval.run" for r in rows)
    m = json.loads((tmp_path / "log2" / "metrics.json").read_text())
    assert m["config"]["commit_at_start"] == rows[1]["commit"]


def test_text_results_carry_the_template_label(tiny_root, tmp_path):
    from eval.run import main
    main(["--split", "dev", "--tag", "lab", "--extractor", "rules", "--root", str(tiny_root), "--out", str(tmp_path)])
    m = json.loads((tmp_path / "lab" / "metrics.json").read_text())
    label = "template-generated; extractor and generator share a lexicon; not a headline number"
    assert m["config"]["source_label"] == label and label in (tmp_path / "lab" / "report.md").read_text()


def test_sealed_split_writes_no_individual_records(tiny_root, tmp_path):
    from eval.run import main
    main(["--split", "test", "--tag", "agg", "--extractor", "rules", "--root", str(tiny_root), "--out", str(tmp_path)])
    out = tmp_path / "agg"
    assert not (out / "errors.jsonl").exists()
    assert "aggregate only" in (out / "report.md").read_text()


def test_offtemplate_dev_split_runs_in_text_mode(tiny_root, tmp_path):
    import json

    from eval.run import main
    main(["--split", "offtemplate_dev", "--tag", "ot", "--extractor", "rules", "--root", str(tiny_root), "--out", str(tmp_path)])
    m = json.loads((tmp_path / "ot" / "metrics.json").read_text())
    assert m["config"]["n_utterances"] == 40 and "hand-written" in m["config"]["source_label"]
