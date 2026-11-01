import json
import subprocess
import sys

import pytest

from jatayu import config


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
