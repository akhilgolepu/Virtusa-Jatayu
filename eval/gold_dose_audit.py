"""python -m eval.gold_dose_audit --tag T [--root data]

Aggregate-only audit of GOLD doses (no pipeline, no predictions): for dev, test and final_test, counts per drug the
gold medication records whose dose is outside the lexicon's range (datagen.doses.in_cited_range) and those the
validator would flag (a catching flag on the gold record itself). Deliberate out_of_range_case anomalies are counted
separately. Writes results/<T>/metrics.json + report.md; no record is printed or written."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from datagen.doses import in_cited_range
from datagen.splits import load_split
from eval.runlog import log_run
from eval.seeded_errors import CATCH
from jatayu import config
from jatayu.lexicon import Lexicon
from jatayu.models import Field, MedicationEntry
from jatayu.validate import validate

SPLITS = ("dev", "test", "final_test")


def audit(utts, lex: Lexicon) -> dict:
    when = datetime(2026, 11, 1, 10, 0).astimezone()
    f = lambda v: Field(value=v, span=None, confidence=1.0, source="rules")  # noqa: E731
    per_drug: dict[str, Counter] = defaultdict(Counter)
    for u in utts:
        for e in u.entries:
            if e.kind != "medication" or e.context == "measurement" or not (e.drug and e.dose_value and e.dose_unit):
                continue
            c = per_drug[e.drug.value]
            if e.anomaly:
                c["out_of_range_case"] += 1
                continue
            route = e.route.value if e.route else None
            c["gold_doses"] += 1
            c["outside_range"] += not in_cited_range(lex, e.drug.value, route, e.dose_unit.value, e.dose_value.value)
            entry = MedicationEntry(drug=f(e.drug.value), dose_value=f(e.dose_value.value),
                                    dose_unit=f(e.dose_unit.value), route=f(route), time=f(when))
            for code in sorted({fl.code for fl in validate(entry, lex)} & CATCH):
                c[f"validator:{code}"] += 1
            c["validator_flagged"] += bool({fl.code for fl in validate(entry, lex)} & CATCH)
    total = Counter()
    for c in per_drug.values():
        total.update(c)
    return {"total": dict(total), "per_drug": {d: dict(c) for d, c in sorted(per_drug.items())}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    lex = Lexicon.load()
    res = {}
    for split in SPLITS:
        start = log_run(args.out, runner="eval.gold_dose_audit (gold labels only; no pipeline; aggregate only)",
                        split=split, tag=args.tag)
        utts = load_split(split, final=split != "dev", sealed_ok=split == "final_test", root=args.root)
        res[split] = audit(utts, lex)
    m = {"tag": args.tag, "commit_at_start": start["commit"], "created": datetime.now().astimezone().isoformat(),
         "weight_kg": [lex.weight_kg.min, lex.weight_kg.max] if lex.weight_kg else None, "splits": res}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(m, indent=2) + "\n")
    lines = [f"# Gold dose audit — `{args.tag}`", "", "Aggregate only: gold labels, no pipeline, no individual record. "
             "'Outside range' = outside the lexicon range for the drug (+ route when spoken; per-kg rows x 45-130 kg). "
             "'Validator flagged' = the validator raises a catching flag on the gold record itself "
             "(includes its own N/5 decimal-slip floor).", "",
             "| Split | Gold doses | Outside range | Validator flagged | Deliberate out_of_range_case |", "|---|---|---|---|---|"]
    for s, r in res.items():
        t = r["total"]
        lines.append(f"| {s} | {t.get('gold_doses', 0)} | {t.get('outside_range', 0)} | {t.get('validator_flagged', 0)} | "
                     f"{t.get('out_of_range_case', 0)} |")
    for s, r in res.items():
        rows = [(d, c) for d, c in r["per_drug"].items() if c.get("outside_range") or c.get("validator_flagged")]
        lines += ["", f"## {s}: drugs with any gold dose outside range or flagged", "",
                  "| Drug | Gold doses | Outside range | Validator flagged (by rule) |", "|---|---|---|---|"]
        lines += [f"| {d} | {c.get('gold_doses', 0)} | {c.get('outside_range', 0)} | {c.get('validator_flagged', 0)} "
                  f"({', '.join(f'{k[10:]} {v}' for k, v in c.items() if k.startswith('validator:')) or '-'}) |"
                  for d, c in rows] or ["| (none) | | | |"]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
