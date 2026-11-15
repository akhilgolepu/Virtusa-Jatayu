"""python -m eval.drug_identity --tag r9-drug-identity-before   (dev speech only; evaluator round 9, items 1 and 2)

Drug identity on the saved dev speech transcripts (the same ASR output as every dev speech run since round 4), rules
NER + validator + the low_asr_confidence flag, exactly as the pipeline runs them. Deterministic; no model is loaded.

1. Wrong drug recorded: an entry whose drug IS in the lexicon but is not a drug of that utterance's gold (another
   known drug, or a non-drug word, was recorded as a known drug). Each one is listed with how it was matched (by
   sound: a fuzzy or phonetic match; or an exact lexicon word the recogniser produced) and its flags.
   "Nothing stronger" is counted two ways:
     - identity: no flag about the drug's identity other than low_confidence / low_asr_confidence;
     - acknowledgement: no high-severity flag at all, so the entry can be confirmed without ticking anything.
   Correct drugs matched by sound are counted too: with the round-9 rule they also need acknowledgement (the cost).
2. drug_not_in_lexicon precision and recall against the hand labels in eval/unknown_drug_labels_dev.yaml (the 49
   entries the round-8 rule raised, labelled drug / junk / other). Precision = drug-labelled / flags raised; recall =
   drug-labelled entries still flagged / all 38 drug-labelled entries. A flag with no label is reported as such.
Dev only: nothing here reads test or final_test."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

from datagen.splits import load_split
from eval.flag_counts import SPEECH
from eval.runlog import log_run
from jatayu import config

LABELS = config.ROOT / "eval" / "unknown_drug_labels_dev.yaml"
WEAK = {"low_confidence", "low_asr_confidence"}
IDENTITY = {"low_confidence", "low_asr_confidence", "sound_alike_drug", "drug_not_in_lexicon"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from jatayu.asr_confidence import flag_low_confidence
    from jatayu.extract.rules import RulesExtractor
    from jatayu.lexicon import Lexicon
    from jatayu.models import MedicationEntry
    from jatayu.validate import validate_all

    start = log_run(args.out, runner="eval.drug_identity", split="dev", tag=args.tag, transcripts=str(SPEECH.relative_to(config.ROOT)))
    lex = Lexicon.load()
    x = RulesExtractor(lex)
    dev = {u.id: u for u in load_split("dev")}
    rows = [r for r in map(json.loads, SPEECH.read_text().splitlines()) if r.get("path", "").startswith("tts/")]
    labels = {(l["utt"], l["heard"]): l["label"] for l in yaml.safe_load(LABELS.read_text())["labels"]}

    wrong, sound_ok, unknown = [], [], []
    for r in rows:
        u = dev[r["utt_id"]]
        gold = {g.drug.value for g in u.entries if g.drug is not None}
        preds = flag_low_confidence(validate_all(x.extract(r["text"], datetime.fromisoformat(u.capture_time)), lex, []),
                                    r.get("words", []), config.ASR_WORD_PROB_THRESHOLD)
        for p in preds:
            if not isinstance(p, MedicationEntry) or p.drug.value is None:
                continue
            codes = [f.code for f in p.flags]
            row = {"utt": u.id, "heard": p.drug.raw, "recorded": p.drug.value, "confidence": round(p.drug.confidence, 3),
                   "match": "by sound" if p.drug.confidence < 1.0 else "exact word", "flags": codes,
                   "high": sorted({f.code for f in p.flags if f.severity == "high"})}
            if not lex.has_drug(p.drug.value):
                unknown.append({**row, "label": labels.get((u.id, (p.drug.raw or "").lower()), "unlabelled")})
            elif p.drug.value not in gold:
                wrong.append({**row, "gold_drugs": sorted(gold), "reference": u.text, "transcript": r["text"],
                              "identity_flags": sorted(set(codes) & IDENTITY),
                              "only_weak_identity": not (set(codes) & IDENTITY - WEAK),
                              "no_high_flag": not row["high"]})
            elif p.drug.confidence < 1.0:
                sound_ok.append(row)

    by_match = Counter(w["match"] for w in wrong)
    item1 = {"wrong_drug_entries": len(wrong), "by_match": dict(by_match),
             "only_weak_identity_flags": sum(w["only_weak_identity"] for w in wrong),
             "no_high_flag": sum(w["no_high_flag"] for w in wrong),
             "needs_sound_acknowledgement": sum("sound_alike_drug" in w["flags"] for w in wrong),
             "correct_by_sound": len(sound_ok),
             "correct_by_sound_needing_acknowledgement": sum("sound_alike_drug" in s["flags"] for s in sound_ok)}
    lab = Counter(u["label"] for u in unknown)
    true_total = sum(1 for v in labels.values() if v == "drug")
    item2 = {"flags_raised": len(unknown), "by_label": dict(lab), "drug_labels_total": true_total,
             "precision": round(lab["drug"] / len(unknown), 3) if unknown else None,
             "recall": round(lab["drug"] / true_total, 3) if true_total else None}

    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "clips": len(rows), "wrong_drug": item1,
                                                  "unknown_drug_flag": item2, "wrong_drug_cases": wrong,
                                                  "correct_by_sound": sound_ok, "unknown_drug_cases": unknown},
                                                 indent=2, default=str) + "\n")
    L = [f"# Drug identity on dev speech (`{args.tag}`, commit `{start['commit']}`)", "",
         f"{len(rows)} dev speech clips (synthetic speech, saved transcripts `{SPEECH.relative_to(config.ROOT)}`), rules "
         "NER + validator + low_asr_confidence. Dev only.", "",
         "## 1. Wrong drug recorded as a known drug", "",
         f"- Entries: **{len(wrong)}** ({', '.join(f'{v} {k}' for k, v in by_match.items()) or 'none'}).",
         f"- With no identity flag stronger than low_confidence / low_asr_confidence: **{item1['only_weak_identity_flags']}**.",
         f"- With no high-severity flag at all (confirmable without ticking anything): **{item1['no_high_flag']}**.",
         f"- Needing the sound-alike acknowledgement: **{item1['needs_sound_acknowledgement']}**.",
         f"- Correct drugs matched by sound: {item1['correct_by_sound']}, of which "
         f"{item1['correct_by_sound_needing_acknowledgement']} now need the acknowledgement.", "",
         "| Utterance | Heard | Recorded | Gold drug(s) | Match | Identity flags | High flags |", "|---|---|---|---|---|---|---|"]
    L += [f"| {w['utt']} | {w['heard']} | {w['recorded']} | {', '.join(w['gold_drugs'])} | {w['match']} "
          f"({w['confidence']}) | {', '.join(w['identity_flags']) or '—'} | {', '.join(w['high']) or '—'} |" for w in wrong]
    L += ["", "## 2. drug_not_in_lexicon flag, against the hand labels", "",
          f"Flags raised: **{len(unknown)}** — " + ", ".join(f"{k} {v}" for k, v in sorted(lab.items())) +
          f". Precision **{item2['precision']}**, recall **{item2['recall']}** (of {true_total} drug-labelled entries).", "",
          "| Utterance | Heard | Label |", "|---|---|---|"]
    L += [f"| {u['utt']} | {u['heard']} | {u['label']} |" for u in unknown]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps({"wrong_drug": item1, "unknown_drug_flag": item2}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
