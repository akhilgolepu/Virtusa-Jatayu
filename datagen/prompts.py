"""python -m datagen.prompts [--seed 7]

Pick the sentences Akhil reads aloud: mostly test (they become the real-audio test set), some dev, a
Hinglish quota, every category represented, condition hints rotated."""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from datagen.schema import GoldUtterance
from datagen.splits import load_split
from jatayu import config

CONDITIONS = ["quiet", "fan", "street", "siren-playback", "fast", "mumbled"]


def _pick(utts: list[GoldUtterance], n: int, n_hinglish: int, rng: random.Random) -> list[GoldUtterance]:
    hing = [u for u in utts if u.lang == "hinglish"]
    rng.shuffle(hing)
    chosen = hing[:n_hinglish]
    by_cat = defaultdict(list)
    for u in utts:
        if u.lang != "hinglish":
            by_cat[u.category].append(u)
    for pool in by_cat.values():
        rng.shuffle(pool)
    cats = sorted(by_cat)
    while len(chosen) < n and any(by_cat.values()):  # round-robin so every category is represented
        for cat in cats:
            if by_cat[cat] and len(chosen) < n:
                chosen.append(by_cat[cat].pop())
    return chosen


def make_prompts(seed: int, root: Path = config.DATA_DIR, n_test: int = 180, n_dev: int = 60,
                 min_hinglish: int = 40, force: bool = False) -> list[dict]:
    out = root / "recordings" / "prompts.jsonl"
    if out.exists() and not force:
        # Recordings reference prompt ids; regenerating silently could re-point them at other sentences.
        raise FileExistsError(f"{out} exists; pass force=True (--force) only if no takes reference it")
    rng = random.Random(seed)
    # Building the recording prompts is part of constructing the test set, not tuning on it.
    test = _pick(load_split("test", final=True, root=root), n_test, (min_hinglish * 3) // 4, rng)
    dev = _pick(load_split("dev", root=root), n_dev, min_hinglish - (min_hinglish * 3) // 4, rng)
    rows = []
    for i, u in enumerate(test + dev):  # i drives the condition-hint rotation only
        rows.append({"prompt_id": u.id, "split": u.split, "text": u.text, "gold_utt_id": u.id,
                     "condition_hint": CONDITIONS[i % len(CONDITIONS)], "lang": u.lang,
                     "entries": [e.model_dump(mode="json") for e in u.entries]})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--force", action="store_true", help="overwrite prompts.jsonl (only if nothing is recorded)")
    args = ap.parse_args(argv)
    rows = make_prompts(args.seed, args.root, force=args.force)
    print(f"wrote {len(rows)} prompts ({sum(r['lang'] == 'hinglish' for r in rows)} Hinglish) "
          f"to {args.root / 'recordings' / 'prompts.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
