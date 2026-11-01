import collections
import subprocess
import sys

import pytest

from datagen.generate import generate, load_templates
from datagen.splits import load_split, split_families, write_splits


@pytest.fixture(scope="module")
def utts():
    return generate(seed=1234, per_pattern=4)


@pytest.fixture(scope="module")
def fam_split():
    return split_families([(f["id"], f["category"]) for f in load_templates()], seed=1234)


def test_no_family_leak(utts, tmp_path, fam_split):
    write_splits(utts, fam_split, tmp_path)
    seen = collections.defaultdict(set)
    for name in ("train", "dev", "test"):
        for u in load_split(name, final=True, root=tmp_path):
            seen[u.family].add(name)
            assert u.split == name
    assert all(len(s) == 1 for s in seen.values())
    assert len(seen) == 73


def test_split_ratios_close(utts, fam_split):
    counts = collections.Counter(fam_split[u.family] for u in utts)
    total = sum(counts.values())
    # +-6 points: every category is guaranteed a dev family (review finding I4), which costs train ~5 points.
    for name, target in (("train", 0.7), ("dev", 0.1), ("test", 0.2)):
        assert abs(counts[name] / total - target) <= 0.06, (name, counts)


def test_every_category_in_test(fam_split):
    cats = collections.defaultdict(list)
    for f in load_templates():
        cats[f["category"]].append(fam_split[f["id"]])
    for cat, splits in cats.items():
        if len(splits) >= 2:
            assert "test" in splits and "train" in splits, (cat, splits)


def test_load_test_requires_final(utts, tmp_path, fam_split):
    write_splits(utts, fam_split, tmp_path)
    with pytest.raises(PermissionError):
        load_split("test", root=tmp_path)
    assert load_split("dev", root=tmp_path)


def test_modified_test_detected(utts, tmp_path, fam_split):
    write_splits(utts, fam_split, tmp_path)
    with open(tmp_path / "test" / "test.jsonl", "a") as fh:
        fh.write(" ")
    with pytest.raises(ValueError, match="test split modified"):
        load_split("test", final=True, root=tmp_path)


def test_build_refuses_refreeze(tmp_path):
    cmd = [sys.executable, "-m", "datagen.build", "--seed", "1234", "--per-pattern", "2", "--root", str(tmp_path)]
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    assert (tmp_path / "synth" / "STATS.md").exists() and (tmp_path / "review" / "sample50.md").exists()
    second = subprocess.run(cmd, capture_output=True, text=True)
    assert second.returncode != 0 and "refreeze" in second.stderr


def test_hard_categories_have_dev_and_two_test_families(fam_split):
    cats = collections.defaultdict(list)
    for f in load_templates():
        cats[f["category"]].append(fam_split[f["id"]])
    for cat, splits in cats.items():
        assert "dev" in splits, cat
    for cat in ("med_correction", "med_incomplete", "context_negation", "context_measurement"):
        assert splits_count(cats[cat], "test") >= 2, (cat, cats[cat])


def splits_count(splits, name):
    return sum(s == name for s in splits)


def test_final_test_is_sealed_and_template_disjoint_from_test(utts, tmp_path, fam_split):
    write_splits(utts, fam_split, tmp_path)
    test = load_split("test", final=True, root=tmp_path)
    with pytest.raises(PermissionError):
        load_split("final_test", final=True, root=tmp_path)
    final = load_split("final_test", final=True, sealed_ok=True, root=tmp_path)
    pattern = lambda u: u.id.rsplit("-", 1)[0]  # noqa: E731
    assert test and final and not ({pattern(u) for u in test} & {pattern(u) for u in final})
    assert {u.category for u in final} == {u.category for u in test}
    assert all(u.split == "final_test" for u in final)


def test_committed_hash_file_guards_both_sets(utts, tmp_path, fam_split):
    write_splits(utts, fam_split, tmp_path)
    lines = (tmp_path / "frozen.sha256").read_text().split("\n")
    assert any(l.endswith("test.jsonl") for l in lines) and any(l.endswith("final_test.jsonl") for l in lines)
    with open(tmp_path / "final_test" / "final_test.jsonl", "a") as fh:
        fh.write(" ")
    with pytest.raises(ValueError, match="modified"):
        load_split("final_test", final=True, sealed_ok=True, root=tmp_path)
