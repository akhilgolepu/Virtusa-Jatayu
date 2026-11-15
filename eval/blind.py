"""python -m eval.blind --tag r7-blind-v1   (evaluator round 7, item 5)

The evaluator-authored blind off-template set (eval/offtemplate_blind_v1.yaml), run exactly as its header says:
  - the cases are converted to the repo's gold format by this script only (mechanical mapping, no gold fixed; every
    value that cannot be represented is counted in the conversion report);
  - rules, hybrid and LLM-only run ONCE each on the typed sentences, each run logged in results/run_log.jsonl;
  - the report gives aggregate numbers per tier (core, stretch) only: entity F1, exact match, dangerous errors,
    administration-status errors, flags raised. Individual errors go to errors-<extractor>.jsonl, not to the report.
Nothing in the pipeline (extractor, lexicon, validator, prompt, threshold) is changed by or for this set."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml

from datagen.schema import GoldEntry, GoldField, GoldTime, GoldUtterance
from eval.metrics import Scorer
from eval.runlog import log_run
from jatayu import config

PATH = config.ROOT / "eval" / "offtemplate_blind_v1.yaml"
CAPTURE = "2026-11-03T10:45:00+05:30"  # the file states no capture time; relative/clock gold times anchor here
STATUS = {"given": "given", "not_given": "not_given", "measurement": "measurement", "not_done": "not_given"}


def _f(v) -> GoldField:
    return GoldField(value=v, surface=str(v), span=(0, 0))  # scoring compares values; spans are not used


def convert(path: Path = PATH):
    """-> (GoldUtterances, per-case tier, conversion report). Mechanical only."""
    from jatayu.lexicon import Lexicon

    lex = Lexicon.load()
    report: Counter = Counter()
    utts, tiers = [], {}
    for c in yaml.safe_load(path.read_text(encoding="utf-8"))["cases"]:
        entries = []
        for e in c["expected"]:
            kind = "procedure" if e.get("procedure") and not e.get("drug") else "medication"
            drug = proc = dose = unit = route = None
            if kind == "medication":
                drug = lex.lookup_drug(str(e["drug"])) or str(e["drug"]).lower()
                report["drug: in lexicon" if lex.lookup_drug(str(e["drug"])) else "drug: NOT in lexicon (kept as written)"] += 1
            else:
                proc = lex.lookup_procedure(str(e["procedure"])) or str(e["procedure"]).lower()
                report["procedure: in lexicon" if lex.lookup_procedure(str(e["procedure"])) else "procedure: NOT in lexicon (kept as written)"] += 1
            d = e.get("dose")
            if isinstance(d, (int, float)):
                dose = float(d)
            elif d is not None:
                try:
                    dose = float(str(d))
                except ValueError:
                    report["dose: text, not one number -> no single gold dose"] += 1
            if e.get("unit"):
                unit = lex.canonical_unit(str(e["unit"])) or str(e["unit"])
                report["unit: mapped" if lex.canonical_unit(str(e["unit"])) else "unit: NOT in lexicon (kept)"] += 1
            if e.get("route"):
                r = str(e["route"])
                route = (lex.canonical_route(r) or (r.upper() if r.upper() in lex.route_codes() else None)
                         or next((lex.canonical_route(p) for p in r.split("/") if lex.canonical_route(p)), None))
                report["route: mapped" if route else "route: NOT mappable (kept as written)"] += 1
                route = route or r
            if "concentration" in e:
                report["concentration: no field in the repo's gold format (dropped)"] += 1
            t = e.get("time")
            if t is None:
                time = GoldTime()
            elif m := re.fullmatch(r"\s*-\s*(\d+)\s*min\w*\s*", str(t)):
                time = GoldTime(kind="relative", offset_s=-60 * int(m.group(1)), surface=str(t))
            elif m := re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(t)):
                time = GoldTime(kind="clock", hh=int(m.group(1)), mm=int(m.group(2)), surface=str(t))
            else:
                time = GoldTime()
                report["time: unparseable -> not stated"] += 1
            report[f"status: {e['status']}"] += 1
            entries.append(GoldEntry(kind=kind, context=STATUS[e["status"]], drug=_f(drug) if drug else None,
                                     procedure=_f(proc) if proc else None, dose_value=_f(dose) if dose is not None else None,
                                     dose_unit=_f(unit) if unit else None, route=_f(route) if route else None, time=time))
        utts.append(GoldUtterance(id=str(c["id"]), family="blind_v1", category="med_messy", split="dev", lang="en",
                                  text=str(c["utterance"]), capture_time=CAPTURE, entries=entries, tags=[c["tier"]]))
        tiers[str(c["id"])] = c["tier"]
    return utts, tiers, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from eval.run import _extract, _extractor

    utts, tiers, conv = convert()
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for name in ("rules", "hybrid", "llm"):  # ONCE each
        start = log_run(args.out, runner="eval.blind", split="offtemplate_blind_v1", tag=f"{args.tag}-{name}",
                        extractor=name, mode="text", note="evaluator-authored blind set; run once per protocol")
        lex, x = _extractor(name)
        scorers: dict[str, Scorer] = defaultdict(Scorer)
        flags: dict[str, Counter] = defaultdict(Counter)
        for u in utts:
            preds = _extract(x, lex, u.text, datetime.fromisoformat(u.capture_time))
            for tier in (tiers[u.id], "all"):
                scorers[tier].add(u, preds)
                for p in preds:
                    flags[tier].update(f.code for f in p.flags)
        results[name] = {"commit": start["commit"], "tiers": {}}
        for tier in ("core", "stretch", "all"):
            m = scorers[tier].metrics()
            results[name]["tiers"][tier] = {
                "utterances": sum(1 for t in tiers.values() if tier in (t, "all")),
                "entity_f1": m["entity"]["micro"]["f1"], "precision": m["entity"]["micro"]["precision"],
                "recall": m["entity"]["micro"]["recall"], "exact_match": m["record_exact_match"],
                "dangerous_error": m["dangerous_error"], "dangerous_error_lenient": m["dangerous_error_lenient"],
                "administration_status_error": m["administration_status_error"], "context_error": m["context_error"],
                "flags_raised": sum(flags[tier].values()), "flags_by_code": dict(flags[tier].most_common())}
        (out / f"errors-{name}.jsonl").write_text("".join(json.dumps(e, default=str) + "\n"
                                                         for e in scorers["all"].errors()), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps({"conversion": dict(conv), "results": results}, indent=2) + "\n")
    r = lambda d: f"{d['count']}/{d['denominator']}"  # noqa: E731
    L = [f"# Blind off-template set v1 — aggregate only (`{args.tag}`)", "",
         "Evaluator-authored, 32 typed sentences (28 core, 4 stretch). Run once per extractor, per the file's protocol; "
         "nothing in the pipeline was changed. **A sanity check from a single author, not a headline number.**", "",
         "## Conversion (script only, no gold fixed)", "", "| Mapping | Count |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(conv.items())]
    for tier in ("core", "stretch", "all"):
        L += ["", f"## Tier: {tier}", "",
              "| Extractor | Entity F1 (P / R) | Exact match | Dangerous (strict / lenient) | Admin-status errors | Context errors | Flags raised |",
              "|---|---|---|---|---|---|---|"]
        for name, res in results.items():
            t = res["tiers"][tier]
            L.append(f"| {name} (`{res['commit']}`) | {t['entity_f1']:.3f} ({t['precision']:.3f} / {t['recall']:.3f}) | "
                     f"{r(t['exact_match'])} | {r(t['dangerous_error'])} / {r(t['dangerous_error_lenient'])} | "
                     f"{r(t['administration_status_error'])} | {r(t['context_error'])} | {t['flags_raised']} |")
    L += ["", "## Flags raised, by code (all tiers)", "", "| Code | rules | hybrid | llm |", "|---|---|---|---|"]
    codes = sorted({c for res in results.values() for c in res["tiers"]["all"]["flags_by_code"]})
    L += [f"| {c} | " + " | ".join(str(results[n]["tiers"]["all"]["flags_by_code"].get(c, 0)) for n in results) + " |"
          for c in codes]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
