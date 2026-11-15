"""python -m eval.required_fields --tag r12-required-fields   (dev speech only; evaluator round 12, item 2)

How many REQUIRED fields (drug, dose, unit, route) a responder has to fill in per note on the saved dev speech
transcripts (rules NER + validator + low_asr_confidence, as the pipeline runs them; deterministic, no model loaded).
One note = one dev speech clip (one dictated utterance).

  - fields to fill: for every medication entry recorded, its empty required fields (a recorded entry always has a
    drug; dose, unit and route can be empty). A concentration entry (concentration_not_dose) counts dose and unit;
  - records with no entry at all: a gold medication the recogniser lost completely, so nothing appears on the confirm
    screen to fill in — reported apart (the responder would have to re-dictate or type it), not mixed into the count.
Mean, p90 and max per note, and the totals per field. Dev only."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.flag_counts import SPEECH
from eval.runlog import log_run
from jatayu import config

REQUIRED = ("drug", "dose_value", "dose_unit", "route")


def _stats(xs: list[int]) -> dict:
    s = sorted(xs)
    return {"notes": len(s), "mean": round(statistics.fmean(s), 3), "p90": s[min(len(s) - 1, int(0.9 * len(s)))],
            "max": s[-1], "notes_with_any": sum(1 for x in s if x)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from jatayu.asr_confidence import flag_low_confidence
    from jatayu.extract.rules import RulesExtractor
    from jatayu.lexicon import Lexicon
    from jatayu.models import MedicationEntry
    from jatayu.validate import validate_all

    start = log_run(args.out, runner="eval.required_fields", split="dev", tag=args.tag)
    lex = Lexicon.load()
    x = RulesExtractor(lex)
    dev = {u.id: u for u in load_split("dev")}
    rows = [r for r in map(json.loads, SPEECH.read_text().splitlines()) if r.get("path", "").startswith("tts/")]
    per_note, lost_per_note, by_field = [], [], Counter()
    entries = 0
    for r in rows:
        u = dev[r["utt_id"]]
        preds = flag_low_confidence(validate_all(x.extract(r["text"], datetime.fromisoformat(u.capture_time)), lex, []),
                                    r.get("words", []), config.ASR_WORD_PROB_THRESHOLD)
        meds = [p for p in preds if isinstance(p, MedicationEntry)]
        n = 0
        for p in meds:
            entries += 1
            for f in REQUIRED:
                if getattr(p, f).value is None:
                    n += 1
                    by_field[f] += 1
        per_note.append(n)
        recorded = {p.drug.value for p in meds}
        gold = [g for g in u.entries if g.kind == "medication" and g.context in ("given", "not_given")]
        # gold medications with nothing recorded for them: same drug absent and no spare recorded entry to stand in
        lost = max(0, sum(1 for g in gold if g.drug.value not in recorded)
                   - sum(1 for p in meds if p.drug.value not in {g.drug.value for g in gold}))
        lost_per_note.append(lost)
    res = {"commit": start["commit"], "clips": len(rows), "medication_entries": entries,
           "fields_to_fill_per_note": _stats(per_note), "fields_to_fill_by_field": {f: by_field[f] for f in REQUIRED},
           "records_with_no_entry_per_note": _stats(lost_per_note), "records_with_no_entry_total": sum(lost_per_note)}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(res, indent=2) + "\n")
    a, b = res["fields_to_fill_per_note"], res["records_with_no_entry_per_note"]
    L = [f"# Required fields to fill per note, dev speech (`{args.tag}`, commit `{start['commit']}`)", "",
         f"{len(rows)} dev speech clips (synthetic speech, saved transcripts), rules NER; one note = one clip; "
         f"{entries} medication entries recorded. Required fields: drug, dose, unit, route.", "",
         "| Per note | Mean | p90 | Max | Notes with any |", "|---|---|---|---|---|",
         f"| Empty required fields on the recorded entries | {a['mean']} | {a['p90']} | {a['max']} | {a['notes_with_any']} of {a['notes']} |",
         f"| Medication records with no entry at all (apart: nothing on screen to fill) | {b['mean']} | {b['p90']} | {b['max']} | {b['notes_with_any']} of {b['notes']} |",
         "", "| Field | Empty on a recorded entry (total) |", "|---|---|"]
    L += [f"| {f} | {by_field[f]} |" for f in REQUIRED]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
