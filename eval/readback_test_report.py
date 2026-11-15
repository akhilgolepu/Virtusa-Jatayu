"""python -m eval.readback_test_report --tag <tag> [--store data/readback_test] [--label "..."]

Aggregates the read-back test (jatayu/readback_trial.py): catch rate per error type (wrong drug, in-range wrong dose,
wrong route) = "Needs correction" on a wrong record, and the false-alarm rate = "Needs correction" on a correct record,
each with a Wilson 95% interval. Aggregate only: no tester code, no trial, no answer is written to the report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.runlog import log_run
from jatayu import config

NAMES = {"wrong_drug": "Wrong but valid drug", "wrong_dose": "In-range wrong dose", "wrong_route": "Wrong route"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--store", type=Path, default=config.DATA_DIR / "readback_test")
    ap.add_argument("--label", default="human testers, synthetic records")
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from jatayu.readback_trial import TrialStore, aggregate

    start = log_run(args.out, runner="eval.readback_test_report", split="readback-test", tag=args.tag, label=args.label)
    res = aggregate(TrialStore(args.store))
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "label": args.label, **res}, indent=2) + "\n")

    def row(name, r):
        ci = f"{r['wilson95'][0]:.3f}-{r['wilson95'][1]:.3f}" if r["wilson95"] else "—"
        rate = f"{r['rate']:.3f}" if r["rate"] is not None else "—"
        return f"| {name} | {r['count']} of {r['denominator']} | {rate} | {ci} |"

    L = [f"# Read-back test — aggregate (`{args.tag}`, commit `{start['commit']}`)", "", f"**{args.label}.** "
         f"Testers: {res['testers']} ({res['testers_complete']} finished all 24). Each record was shown on a confirm-style "
         "card and spoken by the read-back; the tester answered Confirm or Needs correction.", "",
         "| Measure | Needs correction | Rate | Wilson 95% |", "|---|---|---|---|"]
    L += [row(f"Catch rate: {NAMES[k]}", v) for k, v in res["catch_rate"].items()]
    L += [row("Catch rate: all wrong records", res["catch_rate_all_errors"]),
          row("False-alarm rate: correct records", res["false_alarm_rate"])]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
