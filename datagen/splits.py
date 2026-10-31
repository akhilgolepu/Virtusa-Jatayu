"""Family-stratified 70/10/20 splits and the frozen-test guard."""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from datagen.schema import GoldUtterance
from jatayu import config

SPLITS = ("train", "dev", "test")
# Categories that carry the safety metric's hardest cases get two test families so a single phrasing
# ("refused") cannot pass the whole category.
HARD_CATEGORIES = {"med_correction", "med_incomplete", "context_negation", "context_measurement"}


def split_families(families: list[tuple[str, str]], seed: int) -> dict[str, str]:
    """families: [(family_id, category)] -> {family_id: split}. Per category: >=1 test family when the
    category has >=2 (>=2 for HARD_CATEGORIES with >=6), >=1 dev family when it has >=5; counts round down so
    the test share stays near 20%."""
    by_cat: dict[str, list[str]] = defaultdict(list)
    for fam, cat in families:
        by_cat[cat].append(fam)
    out = {}
    for cat in sorted(by_cat):
        fams = sorted(by_cat[cat])
        random.Random(f"{seed}:{cat}").shuffle(fams)
        n = len(fams)
        n_test = max(1, int(0.2 * n)) if n >= 2 else 0
        if cat in HARD_CATEGORIES and n >= 6:
            n_test = max(2, n_test)
        n_dev = max(1, int(0.1 * n)) if n >= 5 else 0
        for i, fam in enumerate(fams):
            out[fam] = "test" if i < n_test else "dev" if i < n_test + n_dev else "train"
    return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(name: str, root: Path) -> Path:
    return root / "test" / "test.jsonl" if name == "test" else root / "synth" / f"{name}.jsonl"


def write_splits(utts: list[GoldUtterance], fam_split: dict[str, str], root: Path) -> dict[str, int]:
    """Writes synth/train.jsonl, synth/dev.jsonl and test/test.jsonl (+ test/FROZEN.json). The test split
    lives ONLY under test/ so nothing reads it by accident."""
    rows: dict[str, list[str]] = {s: [] for s in SPLITS}
    for u in utts:
        split = fam_split[u.family]
        rows[split].append(u.model_copy(update={"split": split}).model_dump_json())
    for split, lines in rows.items():
        path = _path(split, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    frozen = root / "test" / "FROZEN.json"
    frozen.write_text(json.dumps({"test.jsonl": _sha256(_path("test", root))}, indent=2) + "\n")
    return {s: len(v) for s, v in rows.items()}


def load_split(name: str, *, final: bool = False, root: Path = config.DATA_DIR) -> list[GoldUtterance]:
    if name not in SPLITS:
        raise ValueError(f"unknown split {name!r}")
    path = _path(name, root)
    if name == "test":
        if not final:
            raise PermissionError("the test split is frozen; pass final=True only for the final evaluation")
        expected = json.loads((root / "test" / "FROZEN.json").read_text())["test.jsonl"]
        if _sha256(path) != expected:
            raise ValueError("test split modified since it was frozen")
    return [GoldUtterance.model_validate_json(line) for line in path.read_text("utf-8").splitlines() if line]
