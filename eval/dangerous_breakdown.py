"""python -m eval.dangerous_breakdown --tag r3-dangerous-breakdown results/<dev run> [...]   (dev runs only)

Every dangerous error (strict definition) in the given dev runs, categorised by the field that is wrong and by why
no catching flag fired. The reason is found by re-running the validator on the values the record carries:
  - "only non-catching flags": the record had flags, but only ones that do not count (weight_based_dose, ...)
  - "valid dose for the recorded drug and route": the wrong value is itself inside the cited range
  - "no cited range for the recorded route"
For speech runs, the origin is "ASR" when the gold value never reached the transcript, else "extraction".
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from eval.asr_text import asr_norm
from eval.metrics import DANGER_FIELDS, NON_CATCHING
from eval.runlog import log_run
from jatayu import config


def _entry(out: dict):
    from jatayu.models import Field, MedicationEntry

    f = lambda v: Field(value=v, span=None, confidence=1.0, source="rules")  # noqa: E731
    return MedicationEntry(drug=f(out.get("drug")), dose_value=f(out.get("dose_value")), dose_unit=f(out.get("dose_unit")),
                           route=f(out.get("route")), time=f(datetime.now().astimezone()))


def why(row: dict, lex) -> str:
    from jatayu.validate import validate

    flags = set(row["flags"])
    if flags & NON_CATCHING - {"time_not_stated"}:
        return "only non-catching flags: " + ", ".join(sorted(flags & NON_CATCHING - {"time_not_stated"}))
    codes = {f.code for f in validate(_entry(row["output"]), lex)}
    if not codes:
        return "valid dose for the recorded drug and route (inside the cited range)"
    if codes == {"no_reference_range"}:
        return "no cited range for the recorded route"
    return "validator flags it when re-run alone: " + ", ".join(sorted(codes))


def origin(row: dict, lex) -> str:
    if not row.get("asr_text"):
        return "extraction (typed text)"
    exp, hyp = row["expected"], asr_norm(row["asr_text"], lex).split()
    for f in [f for f in DANGER_FIELDS if f in row["wrong_fields"]]:
        v = exp.get(f)
        if v is None:
            continue
        token = f"{v:g}" if isinstance(v, float) else str(v).lower()
        if token not in hyp:
            return f"ASR ({f} '{token}' not in the transcript)"
    return "extraction (the gold values are in the transcript)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from jatayu.lexicon import Lexicon

    lex = Lexicon.load()
    start = log_run(args.out, runner="eval.dangerous_breakdown", split="dev", tag=args.tag, runs=[str(r) for r in args.runs])
    rows, summary = [], {}
    for run in args.runs:
        m = json.loads((run / "metrics.json").read_text())
        assert m["config"]["split"] in ("dev", "offtemplate_dev"), "dev runs only"
        dangerous = [r for r in map(json.loads, (run / "errors.jsonl").read_text().splitlines()) if r.get("dangerous")]
        for r in dangerous:
            rows.append({"run": run.name, "id": r["id"], "input": r["input"], "asr_text": r.get("asr_text"),
                         "fields": [f for f in DANGER_FIELDS if f in r["wrong_fields"]], "flags": r["flags"],
                         "output": r["output"], "expected": r["expected"], "why_no_flag": why(r, lex),
                         "origin": origin(r, lex)})
        summary[run.name] = {"dangerous": m["metrics"]["dangerous_error"], "listed": len(dangerous)}
    by_field = Counter("+".join(r["fields"]) for r in rows)
    by_why = Counter(r["why_no_flag"] for r in rows)
    by_origin = Counter(r["origin"].split(" (")[0] for r in rows)
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "runs": summary, "by_field": by_field,
                                                  "by_why_no_flag": by_why, "by_origin": by_origin, "rows": rows},
                                                 indent=2, default=str) + "\n", encoding="utf-8")
    L = [f"# Dangerous errors, categorised (`{args.tag}`, dev, commit `{start['commit']}`)", "",
         "Strict definition (weight_based_dose does not catch). Every dangerous record in the runs below.", "",
         "| Run | Dangerous |", "|---|---|"]
    L += [f"| {k} | {v['dangerous']['count']}/{v['dangerous']['denominator']} |" for k, v in summary.items()]
    L += ["", "| Wrong field | n |", "|---|---|"] + [f"| {k} | {v} |" for k, v in by_field.most_common()]
    L += ["", "| Why no catching flag fired | n |", "|---|---|"] + [f"| {k} | {v} |" for k, v in by_why.most_common()]
    L += ["", "| Origin | n |", "|---|---|"] + [f"| {k} | {v} |" for k, v in by_origin.most_common()]
    L += ["", "## Every record (dev)", ""]
    for r in rows:
        L += [f"- **{r['run']}** `{r['id']}` — {'+'.join(r['fields'])}; {r['why_no_flag']}; {r['origin']}  ",
              f"  input “{r['input']}”" + (f" → ASR “{r['asr_text']}”" if r["asr_text"] else "") + "  ",
              f"  recorded {r['output']} · expected {r['expected']} · flags {r['flags']}"]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(rows)} dangerous records → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
