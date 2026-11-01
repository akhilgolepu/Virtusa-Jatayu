"""python -m eval.seeded_errors [--n 200] [--tag m3-seeded]

Seeded-error test (Field-to-Record M3): take correct dev medication records, corrupt each one way (dose x10,
dose /10, mg<->mcg swap, a route the drug is never given by) and measure how many the validator flags. Only a real
catch counts (out/below range, mg-mcg slip, unit or route not allowed) — "no_reference_range" says the dose was NOT
checked, so it is not a catch. Also reports the false-flag rate on the uncorrupted originals. Target >= 95 %.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from jatayu import config
from jatayu.lexicon import Lexicon
from jatayu.models import Field, MedicationEntry
from jatayu.validate import validate

CORRUPTIONS = ("dose_x10", "dose_div10", "mg_mcg_swap", "wrong_route")
CATCH = {"dose_out_of_range", "dose_below_range", "possible_mg_mcg_confusion", "unit_not_allowed", "route_not_allowed"}
SWAP = {"mg": "mcg", "mcg": "mg"}


def corrupt(rec: dict, kind: str, lexicon: Lexicon) -> dict:
    out = dict(rec)
    if kind == "dose_x10":
        out["dose_value"] = round(rec["dose_value"] * 10, 6)
    elif kind == "dose_div10":
        out["dose_value"] = round(rec["dose_value"] / 10, 6)
    elif kind == "mg_mcg_swap":
        out["dose_unit"] = SWAP[rec["dose_unit"]]
    elif kind == "wrong_route":
        allowed = set(lexicon.drug(rec["drug"]).routes)
        out["route"] = next(r for r in lexicon.route_codes() if r not in allowed)
    return out


def _entry(rec: dict, when: datetime) -> MedicationEntry:
    f = lambda v: Field(value=v, span=None, confidence=1.0, source="rules")  # noqa: E731
    return MedicationEntry(drug=f(rec["drug"]), dose_value=f(rec["dose_value"]), dose_unit=f(rec["dose_unit"]),
                           route=f(rec["route"]), time=f(when))


def _records(root: Path) -> list[dict]:
    out = []
    for u in load_split("dev", root=root):
        for e in u.entries:
            if e.kind == "medication" and e.context == "given" and not e.anomaly and e.drug and e.dose_value \
                    and e.dose_unit and e.route:
                out.append({"drug": e.drug.value, "dose_value": float(e.dose_value.value), "dose_unit": e.dose_unit.value,
                            "route": e.route.value, "utt": u.id})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tag", default="m3-seeded")
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    lex = Lexicon.load()
    rng = random.Random(args.seed)
    pool = _records(args.root)
    swappable = [r for r in pool if r["dose_unit"] in SWAP]
    when = datetime(2026, 11, 1, 10, 0).astimezone()
    per = args.n // len(CORRUPTIONS)
    results, misses = {k: [0, 0] for k in CORRUPTIONS}, []
    base_flagged = base_n = 0
    for i, kind in enumerate(CORRUPTIONS):
        source = swappable if kind == "mg_mcg_swap" else pool
        quota = per + (1 if i < args.n % len(CORRUPTIONS) else 0)
        for rec in [rng.choice(source) for _ in range(quota)]:
            base_n += 1
            base_flagged += bool({f.code for f in validate(_entry(rec, when), lex)} & CATCH)
            bad = corrupt(rec, kind, lex)
            codes = {f.code for f in validate(_entry(bad, when), lex)}
            caught = bool(codes & CATCH)
            results[kind][0] += caught
            results[kind][1] += 1
            if not caught:
                misses.append({"corruption": kind, "original": rec, "corrupted": bad, "flags": sorted(codes)})
    caught = sum(c for c, _ in results.values())
    rate = lambda n, d: {"count": n, "denominator": d, "rate": round(n / d, 4) if d else 0.0}  # noqa: E731
    m = {"n": args.n, "seed": args.seed, "pool_size": len(pool), "catch_rate": rate(caught, args.n),
         "by_corruption": {k: rate(*v) for k, v in results.items()},
         "false_flag_rate": rate(base_flagged, base_n), "target": 0.95, "created": datetime.now().astimezone().isoformat()}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(m, indent=2) + "\n")
    (out / "errors.jsonl").write_text("".join(json.dumps(x) + "\n" for x in misses))
    lines = ["# Seeded-error test", "", f"{args.n} corrupted dev records (seed {args.seed}); target ≥ 95 % flagged.", "",
             "| Corruption | Flagged |", "|---|---|"]
    lines += [f"| {k} | {v['count']}/{v['denominator']} ({v['rate']:.1%}) |" for k, v in m["by_corruption"].items()]
    lines += [f"| **All** | **{caught}/{args.n} ({m['catch_rate']['rate']:.1%})** |", "",
              f"False flags on the uncorrupted originals: {base_flagged}/{base_n}.", "", "## Misses (first 10)", ""]
    lines += [f"- {x['corruption']}: {x['original']['drug']} {x['corrupted']['dose_value']:g} {x['corrupted']['dose_unit']} "
              f"{x['corrupted']['route']} → flags {x['flags'] or 'none'}" for x in misses[:10]]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print(f"seeded errors: {caught}/{args.n} flagged ({m['catch_rate']['rate']:.1%}); false flags {base_flagged}/{base_n} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
