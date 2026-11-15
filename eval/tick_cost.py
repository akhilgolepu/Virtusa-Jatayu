"""python -m eval.tick_cost --tag r10-tick-cost   (dev speech only; IN-SAMPLE; evaluator round 10, item 2)

The cost of the round-9 sound_alike_drug tick on the saved dev speech transcripts (rules NER + validator +
low_asr_confidence, as the pipeline runs them). Deterministic; no model loaded.

1. Every drug matched by sound is classified by how the heard letters relate to the names of the drug recorded:
     canonical spelling variant  - within 2 letter edits (Levenshtein, letters only) of the generic (canonical) name
     alias/brand spelling variant - otherwise within 2 edits of a listed alias or brand name of that drug
     look-alike                  - neither (a different word that only sounds or looks close: "it prevents")
   for the correctly matched ones (drug = gold) and the wrongly matched ones (drug not in gold) alike.
2. Ticks per note (one note = one dev speech clip, one dictated utterance): the checkboxes the confirm screen asks for
   = for each entry, its distinct high-severity flag codes. Mean, p90, max, under the current rule and under each
   possible exemption (the sound flag dropped for that class), and which wrong drugs would still be flagged.
All of it is IN-SAMPLE: the classes and the 2-edit line were looked at on the same dev clips they are scored on."""
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

EDITS = 2
CLASSES = ("canonical spelling variant", "alias/brand spelling variant", "look-alike")


def _letters(s: str | None) -> str:
    return "".join(c for c in (s or "").lower() if c.isalpha())


def classify(heard: str, canon: str, lexicon) -> tuple[str, int, int]:
    from rapidfuzz.distance import Levenshtein

    h = _letters(heard)
    d_canon = Levenshtein.distance(h, _letters(canon))
    aliases = {_letters(a) for a in lexicon.drug(canon).aliases} - {_letters(canon)}
    d_alias = min((Levenshtein.distance(h, a) for a in aliases), default=99)
    if d_canon <= EDITS:
        return CLASSES[0], d_canon, d_alias
    if d_alias <= EDITS:
        return CLASSES[1], d_canon, d_alias
    return CLASSES[2], d_canon, d_alias


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

    start = log_run(args.out, runner="eval.tick_cost", split="dev", tag=args.tag)
    lex = Lexicon.load()
    x = RulesExtractor(lex)
    dev = {u.id: u for u in load_split("dev")}
    rows = [r for r in map(json.loads, SPEECH.read_text().splitlines()) if r.get("path", "").startswith("tts/")]
    notes, sound = [], []
    for r in rows:
        u = dev[r["utt_id"]]
        gold = {g.drug.value for g in u.entries if g.drug is not None}
        preds = flag_low_confidence(validate_all(x.extract(r["text"], datetime.fromisoformat(u.capture_time)), lex, []),
                                    r.get("words", []), config.ASR_WORD_PROB_THRESHOLD)
        entries = []
        for p in preds:
            high = {f.code for f in p.flags if f.severity == "high"}
            row = {"high": high, "sound": None}
            # every drug matched by sound: the round-9 flag, or (from round 10) the medium flag left on an exempt spelling
            by_sound = isinstance(p, MedicationEntry) and p.drug.confidence < 1.0 and lex.has_drug(p.drug.value)
            if by_sound:
                cls, dc, da = classify(p.drug.raw, p.drug.value, lex)
                row["sound"] = {"utt": u.id, "heard": p.drug.raw, "recorded": p.drug.value, "class": cls,
                                "edits_to_canonical": dc, "edits_to_nearest_alias": da,
                                "correct": p.drug.value in gold, "flag": "sound_alike_drug" if "sound_alike_drug" in high
                                else "low_confidence", "other_high": sorted(high - {"sound_alike_drug"})}
                sound.append(row["sound"])
            entries.append(row)
        notes.append(entries)

    def ticks(exempt: set[str], only_sound: bool = False) -> list[int]:
        out = []
        for entries in notes:
            n = 0
            for e in entries:
                high = set(e["high"])
                if e["sound"] and e["sound"]["class"] in exempt:
                    high.discard("sound_alike_drug")
                n += len(high & {"sound_alike_drug"}) if only_sound else len(high)
            out.append(n)
        return out

    options = {"current rule (every sound match below 0.95 ticked)": set(), "exempt canonical spelling variants": {CLASSES[0]},
               "exempt canonical + alias/brand spelling variants": {CLASSES[0], CLASSES[1]}}
    correct = [s for s in sound if s["correct"]]
    wrong = [s for s in sound if not s["correct"]]
    res = {"commit": start["commit"], "clips": len(notes), "edits": EDITS,
           "correct_by_class": dict(Counter(s["class"] for s in correct)),
           "wrong_by_class": dict(Counter(s["class"] for s in wrong)),
           "options": {}, "correct": correct, "wrong": wrong}
    for name, ex in options.items():
        res["options"][name] = {"all_ticks_per_note": _stats(ticks(ex)), "sound_ticks_per_note": _stats(ticks(ex, True)),
                                "wrong_still_sound_flagged": sum(1 for s in wrong if s["class"] not in ex
                                                                 and s["flag"] == "sound_alike_drug"),
                                "wrong_with_any_high_flag": sum(1 for s in wrong if s["class"] not in ex or s["other_high"]),
                                "correct_still_ticked": sum(1 for s in correct if s["class"] not in ex
                                                            and s["flag"] == "sound_alike_drug")}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(res, indent=2) + "\n")
    L = [f"# Tick cost of the sound-alike flag (`{args.tag}`, commit `{start['commit']}`) — IN-SAMPLE", "",
         f"{len(notes)} dev speech clips (synthetic speech, saved transcripts), rules NER. One note = one clip. "
         f"Classes use <= {EDITS} letter edits; chosen while looking at these same clips: **in-sample**.", "",
         f"Drugs matched by sound: {len(correct)} correct, {len(wrong)} wrong.", "",
         "| Class | Correct | Wrong |", "|---|---|---|"]
    L += [f"| {c} | {res['correct_by_class'].get(c, 0)} | {res['wrong_by_class'].get(c, 0)} |" for c in CLASSES]
    L += ["", "| Option | Ticks per note, all (mean / p90 / max) | Sound ticks per note (mean / p90 / max) | "
              "Correct matches still ticked | Wrong drugs still sound-flagged | Wrong drugs with any high flag |",
          "|---|---|---|---|---|---|"]
    for name, o in res["options"].items():
        a, s = o["all_ticks_per_note"], o["sound_ticks_per_note"]
        L.append(f"| {name} | {a['mean']} / {a['p90']} / {a['max']} | {s['mean']} / {s['p90']} / {s['max']} | "
                 f"{o['correct_still_ticked']} | {o['wrong_still_sound_flagged']} of {len(wrong)} | "
                 f"{o['wrong_with_any_high_flag']} of {len(wrong)} |")
    L += ["", "## Wrong drugs matched by sound", "", "| Utterance | Heard | Recorded | Class | Edits to canonical / nearest alias | Flag |",
          "|---|---|---|---|---|---|"]
    L += [f"| {s['utt']} | {s['heard']} | {s['recorded']} | {s['class']} | {s['edits_to_canonical']} / "
          f"{s['edits_to_nearest_alias']} | {s['flag']} |" for s in wrong]
    L += ["", "## Correct drugs matched by sound", "", "| Utterance | Heard | Recorded | Class | Edits to canonical / nearest alias | Flag |",
          "|---|---|---|---|---|---|"]
    L += [f"| {s['utt']} | {s['heard']} | {s['recorded']} | {s['class']} | {s['edits_to_canonical']} / "
          f"{s['edits_to_nearest_alias']} | {s['flag']} |" for s in correct]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:20]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
