"""Family-stratified 70/10/20 splits and the frozen-test guard."""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from datagen.schema import GoldUtterance
from jatayu import config

SPLITS = ("train", "dev", "test", "final_test")
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


FROZEN_SETS = ("test", "final_test")
COMMITTED_HASHES = config.ROOT / "eval" / "frozen.sha256"  # committed; the data itself is git-ignored


def _path(name: str, root: Path) -> Path:
    if name in FROZEN_SETS:
        return root / name / f"{name}.jsonl"
    return root / "synth" / f"{name}.jsonl"


def _hash_file(root: Path) -> Path:
    """The real data/ build is checked against the committed hash file; scratch builds against their own copy."""
    return COMMITTED_HASHES if Path(root).resolve() == config.DATA_DIR.resolve() else Path(root) / "frozen.sha256"


def _pattern_index(utt_id: str) -> int:
    return int(utt_id.rsplit("-", 2)[1])


def write_splits(utts: list[GoldUtterance], fam_split: dict[str, str], root: Path) -> dict[str, int]:
    """Writes synth/train.jsonl, synth/dev.jsonl, test/test.jsonl and final_test/final_test.jsonl, plus the
    SHA-256 hash file. Within each held-out family, paraphrase patterns alternate between test (even) and the sealed
    final_test (odd): split by template, every category in both, no pattern shared."""
    rows: dict[str, list[str]] = {s: [] for s in SPLITS}
    for u in utts:
        split = fam_split[u.family]
        if split == "test" and _pattern_index(u.id) % 2 == 1:
            split = "final_test"
        rows[split].append(u.model_copy(update={"split": split}).model_dump_json())
    for split, lines in rows.items():
        path = _path(split, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    hashes = "".join(f"{_sha256(_path(n, root))}  {n}/{n}.jsonl\n" for n in FROZEN_SETS)
    target = _hash_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(hashes)
    return {s: len(v) for s, v in rows.items()}


def frozen_hashes(root: Path = config.DATA_DIR) -> dict[str, str]:
    lines = [l.split() for l in _hash_file(root).read_text().splitlines() if l.strip()]
    return {Path(rel).name: h for h, rel in lines}


def load_split(name: str, *, final: bool = False, sealed_ok: bool = False,
               root: Path = config.DATA_DIR) -> list[GoldUtterance]:
    if name not in SPLITS:
        raise ValueError(f"unknown split {name!r}")
    path = _path(name, root)
    if name in FROZEN_SETS:
        if not final:
            raise PermissionError(f"the {name} split is frozen; pass final=True only for an evaluation run")
        if name == "final_test" and not sealed_ok:
            raise PermissionError("final_test is sealed until Stage 3 week 7 (S7); pass sealed_ok=True only then")
        if _sha256(path) != frozen_hashes(root)[path.name]:
            raise ValueError(f"{name} split modified since it was frozen")
    return [GoldUtterance.model_validate_json(line) for line in path.read_text("utf-8").splitlines() if line]
