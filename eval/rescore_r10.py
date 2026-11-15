"""python -m eval.rescore_r10 [--out results/r10-rescore]   (dev runs only; offline, no model, no re-run)

Round 10 metric correction. Every existing dev run is re-scored from its own errors.jsonl (blind v1: errors-<x>.jsonl)
with the new headline DANGEROUS ERROR: a wrong drug, dose, unit, route or administration status recorded without a
flag that must be ticked on the confirm screen (severity high). The old metric (matched-drug only) is kept next to it.

What errors.jsonl allows (runs before round 10 stored less than the new scorer needs):
  - wrong dose / unit / route RECORDED on a matched record (an empty field shows "not stated" and is an omission,
    counted apart, not as dangerous): EXACT (the row stores the prediction's flag codes; a code's severity
    is fixed, field_missing is read from the output — eval/metrics.py::high_codes);
  - wrong drug: a missed gold medication paired, in the same clip, with an extra predicted medication. Extra rows stored
    no flags before round 10, so a wrong drug counts as CAUGHT only if a high flag follows for certain from the recorded
    values (drug not in the lexicon, dose or unit missing, unit / route not allowed, dose out of range: the validator run
    on the recorded values); otherwise it is counted as uncaught -> an UPPER BOUND;
  - status: not-given records recorded without possible_not_given come from metrics.json; those with a row are exact,
    the rest (all fields right, so no row was written) are counted as uncaught -> part of the upper bound.
A run scored by the round-10 scorer (rows carry high_flags) is exact throughout.
Denominator: given + not_given gold records (old denominator + the administration-status denominator)."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from eval.metrics import NON_CATCHING, high_codes, is_dangerous
from jatayu import config

DANGER = ("dose_value", "dose_unit", "route")


def _inferred_high(output: dict, lexicon) -> set[str]:
    """High flags certain from a recorded medication's values alone (validator + field_missing)."""
    from jatayu.models import Field, MedicationEntry
    from jatayu.validate import validate

    f = lambda v: Field(value=v, span=None, confidence=1.0, source="rules")  # noqa: E731
    e = MedicationEntry(drug=f(output.get("drug")), dose_value=f(output.get("dose_value")),
                        dose_unit=f(output.get("dose_unit")), route=f(output.get("route")),
                        time=f(datetime(2026, 1, 1).astimezone()), flags=[])
    out = {fl.code for fl in validate(e, lexicon) if fl.severity == "high"}
    if output.get("dose_value") is None or output.get("dose_unit") is None:
        out.add("field_missing")
    return out


def rescore_rows(rows: list[dict], given_den: int, admin: dict, lexicon) -> dict:
    exact = defaultdict(int)  # uncaught, exactly known
    bound = defaultdict(int)  # uncaught as far as errors.jsonl can tell (flags not stored)
    events = defaultdict(int)
    old = sum(is_dangerous(r["wrong_fields"], set(r["flags"]), NON_CATCHING) for r in rows
              if r.get("kind") == "wrong" and r.get("context") == "given" and "drug" in (r.get("expected") or {}))
    native = any("high_flags" in r for r in rows)
    clip = lambda r: (r["id"], r.get("voice"), r.get("snr_db"))  # noqa: E731
    lost, stray = defaultdict(list), defaultdict(list)
    status_rows_caught = status_rows_uncaught = 0
    for r in rows:
        exp, out = r.get("expected") or {}, r.get("output") or {}
        if r.get("kind") == "wrong" and r.get("context") == "given" and "drug" in exp:
            if any(f in r["wrong_fields"] and f not in out for f in DANGER):
                events["omitted dose/unit/route (shown as not stated; not counted)"] += 1
            if any(f in r["wrong_fields"] and f in out for f in DANGER):  # a value recorded, and wrong
                events["wrong dose/unit/route"] += 1
                if not high_codes(r["flags"], out):
                    exact["wrong dose/unit/route"] += 1
        elif r.get("kind") == "wrong" and r.get("context") == "not_given" and "possible_not_given" not in r["flags"]:
            if high_codes(r["flags"], out):
                status_rows_caught += 1
            else:
                status_rows_uncaught += 1
        elif r.get("kind") == "miss" and r.get("context") in ("given", "not_given") and "drug" in exp:
            lost[clip(r)].append(r)
        elif r.get("kind") == "extra_prediction" and "drug" in out:
            stray[clip(r)].append(r)
    for key, ls in lost.items():
        for g, p in zip(ls, stray.get(key, [])):
            events["wrong drug"] += 1
            if "high_flags" in p:  # round-10 rows: exact
                if not p["high_flags"]:
                    exact["wrong drug"] += 1
            elif not _inferred_high(p["output"], lexicon):
                bound["wrong drug"] += 1
    admin_count = admin.get("count", 0)
    events["status (not given recorded as given)"] = admin_count
    exact["status (not given recorded as given)"] = status_rows_uncaught
    if native:
        rest = 0  # round-10 rows exist for every status error
    else:
        rest = admin_count - status_rows_caught - status_rows_uncaught
    bound["status (not given recorded as given)"] = rest
    den = given_den + admin.get("denominator", 0)
    n_exact, n_bound = sum(exact.values()), sum(bound.values())
    return {"old_matched_drug_only": {"count": old, "denominator": given_den},
            "new": {"count": n_exact + n_bound, "denominator": den, "exact_part": n_exact, "bounded_part": n_bound,
                    "is_upper_bound": n_bound > 0},
            "uncaught_exact_by_kind": {k: v for k, v in exact.items() if v},
            "uncaught_bounded_by_kind": {k: v for k, v in bound.items() if v},
            "errors_by_kind": dict(events)}


def _runs(root: Path):
    for d in sorted(root.iterdir()):
        m = d / "metrics.json"
        if not m.exists():
            continue
        data = json.loads(m.read_text())
        if (d / "errors.jsonl").exists() and data.get("config", {}).get("split") in ("dev", "offtemplate_dev"):
            c = data["config"]
            rows = [json.loads(l) for l in (d / "errors.jsonl").read_text().splitlines() if l.strip()]
            yield d.name, f"{c['split']} · {c['mode']} · {c['extractor']}", rows, data["metrics"]
        elif "results" in data and "conversion" in data:  # blind v1: one file per extractor, tier "all"
            for x, res in data["results"].items():
                f = d / f"errors-{x}.jsonl"
                if f.exists():
                    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
                    t = res["tiers"]["all"]
                    yield f"{d.name}:{x}", f"blind v1 · text · {x}", rows, {
                        "dangerous_error": t["dangerous_error"], "administration_status_error": t["administration_status_error"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=config.ROOT / "results")
    ap.add_argument("--out", type=Path, default=config.ROOT / "results" / "r10-rescore")
    args = ap.parse_args(argv)
    from jatayu.lexicon import Lexicon

    lex = Lexicon.load()
    res = {}
    for name, what, rows, m in _runs(args.root):
        admin = m.get("administration_status_error") or {"count": 0, "denominator": 0}  # older runs: not measured
        r = rescore_rows(rows, m["dangerous_error"]["denominator"], admin, lex)
        r["status_measured"] = "administration_status_error" in m
        r["recorded_old"] = m["dangerous_error"]
        r["run"] = what
        res[name] = r
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rescored.json").write_text(json.dumps(res, indent=2) + "\n")
    L = ["# Dangerous error, round-10 definition, re-scored offline from errors.jsonl (dev runs only)", "",
         "New headline: a wrong drug, dose, unit, route or administration status recorded **without a flag the medic "
         "must tick** (severity high). Old: matched-drug records only (a wrong drug is invisible to it), strict. "
         "`≤` = upper bound: part of the count is records whose flags errors.jsonl did not store (see "
         "`eval/rescore_r10.py`). `_SUPERSEDED` runs are listed for completeness only (`results/INVALID_RUNS.md`).", "",
         "| Run | Kind | Old (matched-drug only) | New headline | Uncaught, exact | Uncaught, bounded | All such errors |",
         "|---|---|---|---|---|---|---|"]
    for name, r in res.items():
        o, n = r["old_matched_drug_only"], r["new"]
        L.append(f"| `{name}` | {r['run']} | {o['count']} / {o['denominator']} | {'≤ ' if n['is_upper_bound'] else ''}"
                 f"{n['count']} / {n['denominator']} | {r['uncaught_exact_by_kind'] or '—'} | "
                 f"{r['uncaught_bounded_by_kind'] or '—'} | {r['errors_by_kind']} |")
    (args.out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
