"""python -m eval.seeded_errors [--split dev|test] [--variant standard|harder] [--n 200] [--seed 7] [--tag T]

Seeded-error test (Field-to-Record M3): take correct gold medication records, corrupt each one way, and measure how
many the validator flags.
  standard: dose x10, dose /10, mg<->mcg swap, a route the drug is never given by
  harder:   dose x2, dose x5, a single-digit slip (0.3 -> 0.5), mg -> g
Only a real catch counts (out/below range, mg-mcg slip, unit or route not allowed). "no_reference_range" means the
dose was NOT range-checked, so it is never a catch. Also reports the false-flag rate on the uncorrupted originals
(with the rule that fired for each) and splits the catch rate by range class (cited / illustrative / none).
Use --split dev for tuning; the reported number comes from --split test, run once with the validator frozen.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.runlog import log_run
from eval.stats import wilson
from jatayu import config
from jatayu.lexicon import Lexicon
from jatayu.models import Field, MedicationEntry
from jatayu.validate import validate

VARIANTS = {"standard": ("dose_x10", "dose_div10", "mg_mcg_swap", "wrong_route"),
            "harder": ("dose_x2", "dose_x5", "digit_slip", "mg_to_g")}
CATCH = {"dose_out_of_range", "dose_below_range", "possible_mg_mcg_confusion", "unit_not_allowed", "route_not_allowed"}
SWAP = {"mg": "mcg", "mcg": "mg"}
NEEDS_UNIT = {"mg_mcg_swap": set(SWAP), "mg_to_g": {"mg"}}


def corrupt(rec: dict, kind: str, lexicon: Lexicon, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(0)
    out = dict(rec)
    v = rec["dose_value"]
    if kind in ("dose_x10", "dose_div10", "dose_x2", "dose_x5"):
        out["dose_value"] = round(v * {"dose_x10": 10, "dose_div10": 0.1, "dose_x2": 2, "dose_x5": 5}[kind], 6)
    elif kind == "mg_mcg_swap":
        out["dose_unit"] = SWAP[rec["dose_unit"]]
    elif kind == "mg_to_g":
        out["dose_unit"] = "g"
    elif kind == "wrong_route":
        allowed = set(lexicon.drug(rec["drug"]).routes)
        out["route"] = next(r for r in lexicon.route_codes() if r not in allowed)
    elif kind == "digit_slip":  # change one significant digit: 0.3 -> 0.5, 300 -> 500, 22.75 -> 22.95
        text = f"{v:g}"
        positions = [i for i, ch in enumerate(text) if ch.isdigit() and not (ch == "0" and text[:i].strip("0.") == "")]
        i = rng.choice(positions)
        new = rng.choice([d for d in "123456789" if d != text[i]])
        out["dose_value"] = float(text[:i] + new + text[i + 1:])
    return out


def range_class(rec: dict, lexicon: Lexicon) -> str:
    rows = lexicon.dose_ranges(rec["drug"], rec["route"])
    if not rows:
        return "none"
    return "cited" if any(not r.illustrative for r in rows) else "illustrative"


def _entry(rec: dict, when: datetime) -> MedicationEntry:
    f = lambda v: Field(value=v, span=None, confidence=1.0, source="rules")  # noqa: E731
    return MedicationEntry(drug=f(rec["drug"]), dose_value=f(rec["dose_value"]), dose_unit=f(rec["dose_unit"]),
                           route=f(rec["route"]), time=f(when))


def _records(root: Path, split: str) -> list[dict]:
    out = []
    for u in load_split(split, final=split == "test", root=root):
        for e in u.entries:
            if e.kind == "medication" and e.context == "given" and not e.anomaly and e.drug and e.dose_value \
                    and e.dose_unit and e.route:
                out.append({"drug": e.drug.value, "dose_value": float(e.dose_value.value), "dose_unit": e.dose_unit.value,
                            "route": e.route.value, "utt": u.id})
    return out


def _rate(n: int, d: int) -> dict:
    return {"count": n, "denominator": d, "rate": round(n / d, 4) if d else 0.0, "ci95": list(wilson(n, d))}


def _outcome(flags: list[str]) -> str:
    return "no flag" if not flags else "only non-catching: " + ", ".join(flags)


def aggregate_misses(misses: list[dict]) -> list[dict]:
    counts: dict[tuple, int] = defaultdict(int)
    for x in misses:
        counts[(x["corruption"], x["range_class"], _outcome(x["flags"]))] += 1
    return [{"corruption": c, "range_class": r, "outcome": o, "count": n}
            for (c, r, o), n in sorted(counts.items(), key=lambda kv: -kv[1])]


def aggregate_false_flags(false_flags: list[dict]) -> list[dict]:
    counts: dict[tuple, int] = defaultdict(int)
    for x in false_flags:
        counts[(", ".join(x["rules"]), x["range_class"])] += 1
    return [{"rule": r, "range_class": c, "count": n} for (r, c), n in sorted(counts.items(), key=lambda kv: -kv[1])]


def _pct(r: dict) -> str:
    lo, hi = r["ci95"]
    return f"{r['count']}/{r['denominator']} ({r['rate']:.1%}; 95% CI {lo:.1%}-{hi:.1%})"


def finalize(out: Path, m: dict, misses: list[dict], false_flags: list[dict]) -> None:
    """Write metrics.json + report.md. Record-level files and tables are written for dev only: a test-split run
    reports aggregates, so no individual test record is exposed."""
    for key in ("catch_rate", "false_flag_rate"):
        m[key] = _rate(m[key]["count"], m[key]["denominator"])
    m["by_corruption"] = {k: _rate(v["count"], v["denominator"]) for k, v in m["by_corruption"].items()}
    m["by_range_class"] = {k: _rate(v["count"], v["denominator"]) for k, v in m["by_range_class"].items()}
    m["miss_breakdown"] = aggregate_misses(misses)
    m["false_flags_by_rule"] = aggregate_false_flags(false_flags)
    record_level = m["split"] != "test"
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(m, indent=2) + "\n")
    for name, rows in (("errors.jsonl", misses), ("false_flags.jsonl", false_flags)):
        path = out / name
        if record_level:
            path.write_text("".join(json.dumps(x) + "\n" for x in rows))
        elif path.exists():
            path.unlink()
    lines = [f"# Seeded-error test — {m['variant']}", "",
             f"{m['n']} corrupted **{m['split']}** records (seed {m['seed']}, pool {m['pool_size']}); commit at start "
             f"`{m.get('commit_at_start')}`. 'no_reference_range' (not range-checked) is not counted as a catch.", "",
             "| | Value |", "|---|---|",
             f"| **Catch rate** | **{_pct(m['catch_rate'])}** |",
             f"| **False-flag rate** (uncorrupted originals flagged) | **{_pct(m['false_flag_rate'])}** |", "",
             "| Corruption | Flagged |", "|---|---|"]
    lines += [f"| {k} | {_pct(v)} |" for k, v in m["by_corruption"].items()]
    lines += ["", "| Range class (original drug + route) | Flagged |", "|---|---|"]
    lines += [f"| {k} | {_pct(v)} |" for k, v in m["by_range_class"].items()]
    lines += ["", "## Residual misses (aggregate)", "", "| Corruption | Range class | Outcome | Count |", "|---|---|---|---|"]
    lines += [f"| {r['corruption']} | {r['range_class']} | {r['outcome']} | {r['count']} |" for r in m["miss_breakdown"]]
    lines += ["", "## False flags by rule (aggregate)", "", "| Rule fired | Range class | Count |", "|---|---|---|"]
    lines += [f"| {r['rule']} | {r['range_class']} | {r['count']} |" for r in m["false_flags_by_rule"]]
    if record_level:
        lines += ["", "## Residual misses (dev records, first 15)", "", "| Corruption | Corrupted record | Flags |", "|---|---|---|"]
        lines += [f"| {x['corruption']} | {x['corrupted']['drug']} {x['corrupted']['dose_value']:g} "
                  f"{x['corrupted']['dose_unit']} {x['corrupted']['route']} (from {x['original']['dose_value']:g} "
                  f"{x['original']['dose_unit']}) | {', '.join(x['flags']) or 'none'} |" for x in misses[:15]]
        lines += ["", "## False flags (dev records)", "", "| Record | Rule fired | Why |", "|---|---|---|"]
        lines += [f"| {x['record']['drug']} {x['record']['dose_value']:g} {x['record']['dose_unit']} "
                  f"{x['record']['route']} | {', '.join(x['rules'])} | {' '.join(x['why'])} |" for x in false_flags]
    (out / "report.md").write_text("\n".join(lines) + "\n")


def rerender(out: Path) -> None:
    """Rebuild metrics/report from a finished run's own files (no re-evaluation, no run-log entry)."""
    m = json.loads((out / "metrics.json").read_text())
    read = lambda n: [json.loads(l) for l in (out / n).read_text().splitlines() if l] if (out / n).exists() else []  # noqa: E731
    finalize(out, m, read("errors.jsonl"), read("false_flags.jsonl"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--variant", choices=list(VARIANTS), default="standard")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tag", default="m3-seeded")
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    ap.add_argument("--rerender", type=Path, help="rebuild an existing run folder's report from its files; no re-run")
    args = ap.parse_args(argv)
    if args.rerender:
        rerender(args.rerender)
        return 0
    start = log_run(args.out, runner="eval.seeded_errors", split=args.split, tag=args.tag, variant=args.variant,
                    seed=args.seed, n=args.n)
    lex = Lexicon.load()
    rng = random.Random(args.seed)
    pool = _records(args.root, args.split)
    when = datetime(2026, 11, 1, 10, 0).astimezone()
    kinds = VARIANTS[args.variant]
    per = args.n // len(kinds)
    by_kind = {k: [0, 0] for k in kinds}
    by_class: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    misses, false_flags = [], []
    base_n = 0
    for i, kind in enumerate(kinds):
        source = [r for r in pool if r["dose_unit"] in NEEDS_UNIT[kind]] if kind in NEEDS_UNIT else pool
        quota = per + (1 if i < args.n % len(kinds) else 0)
        for rec in [rng.choice(source) for _ in range(quota)]:
            base_n += 1
            base_flags = [f for f in validate(_entry(rec, when), lex) if f.code in CATCH]
            if base_flags:
                false_flags.append({"record": rec, "rules": [f.code for f in base_flags],
                                    "why": [f.message for f in base_flags], "range_class": range_class(rec, lex)})
            bad = corrupt(rec, kind, lex, rng)
            codes = {f.code for f in validate(_entry(bad, when), lex)}
            caught = bool(codes & CATCH)
            cls = range_class(rec, lex)
            by_kind[kind][0] += caught
            by_kind[kind][1] += 1
            by_class[cls][0] += caught
            by_class[cls][1] += 1
            if not caught:
                misses.append({"corruption": kind, "range_class": cls, "original": rec, "corrupted": bad,
                               "flags": sorted(codes)})
    caught = sum(c for c, _ in by_kind.values())
    m = {"split": args.split, "variant": args.variant, "n": args.n, "seed": args.seed, "pool_size": len(pool),
         "catch_rate": _rate(caught, args.n), "false_flag_rate": _rate(len(false_flags), base_n),
         "by_corruption": {k: _rate(*v) for k, v in by_kind.items()},
         "by_range_class": {k: _rate(*v) for k, v in sorted(by_class.items())},
         "not_counted_as_catch": ["no_reference_range"], "target": 0.95 if args.variant == "standard" else None,
         "commit_at_start": start["commit"], "created": datetime.now().astimezone().isoformat()}
    finalize(args.out / args.tag, m, misses, false_flags)
    out = args.out / args.tag
    print(f"seeded {args.variant} on {args.split}: {caught}/{args.n} flagged ({m['catch_rate']['rate']:.1%}); "
          f"false flags {len(false_flags)}/{base_n} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
