"""python -m datagen.build --seed 1234 [--per-pattern 20] [--root data] [--refreeze]

Generates the synthetic set, writes family-stratified splits, freezes the test split, and writes
synth/STATS.md plus review/sample50.md (the 50-utterance human spot-check sheet)."""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

from datagen.generate import generate, load_templates
from datagen.schema import GoldUtterance
from datagen.splits import split_families, write_splits
from jatayu import config


def _stats(utts: list[GoldUtterance], fam_split: dict[str, str]) -> str:
    split_of = lambda u: fam_split[u.family]  # noqa: E731
    lines = ["# Synthetic dataset stats", "", "| split | utterances | families |", "|---|---|---|"]
    for s in ("train", "dev", "test"):
        lines.append(f"| {s} | {sum(split_of(u) == s for u in utts)} | {sum(v == s for v in fam_split.values())} |")
    cats = Counter((u.category, split_of(u)) for u in utts)
    lines += ["", "| category | train | dev | test |", "|---|---|---|---|"]
    for cat in sorted({c for c, _ in cats}):
        lines.append(f"| {cat} | {cats[(cat, 'train')]} | {cats[(cat, 'dev')]} | {cats[(cat, 'test')]} |")
    drugs = Counter(e.drug.value for u in utts for e in u.entries if e.drug)
    procs = Counter(e.procedure.value for u in utts for e in u.entries if e.procedure)
    langs = Counter(u.lang for u in utts)
    anomalies = Counter(e.anomaly for u in utts for e in u.entries if e.anomaly)
    lines += ["", f"Drugs: {len(drugs)} distinct · Procedures: {len(procs)} distinct · "
              f"Languages: {dict(langs)} · Anomalies: {dict(anomalies)}", "",
              "Drug counts: " + ", ".join(f"{d} {n}" for d, n in drugs.most_common())]
    return "\n".join(lines) + "\n"


def _review_sheet(utts: list[GoldUtterance], seed: int) -> str:
    sample = random.Random(f"review:{seed}").sample(utts, 50)
    lines = ["# Spot-check sheet (50 random synthetic utterances)", "",
             "Tick the box if the gold is what a responder meant. Note anything wrong.", "",
             "| ok | id | text | gold |", "|---|---|---|---|"]
    for u in sample:
        gold = []
        for e in u.entries:
            if e.kind == "medication":
                bits = [e.drug.value if e.drug else "?"]
                if e.dose_value:
                    bits.append(f"{e.dose_value.value:g}")
                if e.dose_unit:
                    bits.append(e.dose_unit.value)
                if e.route:
                    bits.append(e.route.value)
            else:
                bits = [e.procedure.value] + ([e.detail.value] if e.detail else [])
            if e.time.kind == "relative":
                bits.append(f"t{e.time.offset_s:+d}s")
            elif e.time.kind == "clock":
                bits.append(f"@{e.time.hh}:{e.time.mm:02d}")
            if e.context != "given":
                bits.append(f"[{e.context}]")
            if e.anomaly:
                bits.append(f"[anomaly {e.anomaly}]")
            gold.append(" ".join(bits))
        lines.append(f"| [ ] | {u.id} | {u.text.replace('|', '/')} | {' ; '.join(gold)} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--per-pattern", type=int, default=20)
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--refreeze", action="store_true", help="overwrite an existing frozen test split")
    args = ap.parse_args(argv)

    if (args.root / "test" / "FROZEN.json").exists() and not args.refreeze:
        print("test split already frozen; pass --refreeze to regenerate it (this invalidates past results)",
              file=sys.stderr)
        return 2
    utts = generate(args.seed, args.per_pattern)
    fam_split = split_families([(f["id"], f["category"]) for f in load_templates()], args.seed)
    counts = write_splits(utts, fam_split, args.root)
    (args.root / "synth").mkdir(parents=True, exist_ok=True)
    (args.root / "synth" / "STATS.md").write_text(_stats(utts, fam_split), encoding="utf-8")
    (args.root / "review").mkdir(parents=True, exist_ok=True)
    (args.root / "review" / "sample50.md").write_text(_review_sheet(utts, args.seed), encoding="utf-8")
    print(f"wrote {counts} under {args.root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
