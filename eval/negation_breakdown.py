"""python -m eval.negation_breakdown --tag r5-negation-breakdown --transcripts results/<dev audio run>/transcripts.jsonl

Dev speech only, counts only. For every "not given" or "measurement" gold record that the default (rules) extractor
emits WITHOUT its context flag, why: the reference's cue word ("allergic", "refused", "home", "level", "serum"...)
never reached the transcript (ASR dropped or changed it), the cue was heard but the extractor did not use it
(extractor miss), or the reference has no cue word the extractor knows."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.asr_text import asr_norm
from eval.metrics import CONTEXT_FLAGS, _overlap, gold_values, pred_values
from eval.runlog import log_run
from jatayu import config


def classify(rows: list[dict], lex) -> dict[str, Counter]:
    from jatayu.extract.rules import HOME_MED_CUES, MEASUREMENT_CUES, NEGATION_CUES, RulesExtractor
    from jatayu.validate import validate_all

    cues = {"not_given": NEGATION_CUES | HOME_MED_CUES, "measurement": MEASUREMENT_CUES}
    by_id = {u.id: u for u in load_split("dev")}
    x = RulesExtractor(lex)
    out = {"not_given": Counter(), "measurement": Counter()}
    for r in rows:
        u = by_id[r["utt_id"]]
        cap = datetime.fromisoformat(u.capture_time)
        preds = [(p, pred_values(p)) for p in validate_all(x.extract(r["text"], cap), lex, [])]
        free = list(range(len(preds)))
        heard = set(asr_norm(r["text"], lex).split())
        for g in u.entries:
            gv = gold_values(g, cap)
            best, score = None, -1
            for i in free:
                s = _overlap(gv, preds[i][1])
                if s > score:
                    best, score = i, s
            match = preds[best][0] if best is not None and score >= 0 else None
            if match is not None:
                free.remove(best)
            if g.context == "given":
                continue
            c = out[g.context]
            c["records"] += 1
            if match is None:
                c["not recorded at all (drug not recognised; not an error in this metric)"] += 1
                continue
            if CONTEXT_FLAGS[g.context] in {f.code for f in match.flags}:
                c["flagged correctly"] += 1
                continue
            said = set(asr_norm(u.text, lex).split()) & cues[g.context]
            if not said:
                c["ERROR: no cue word the extractor knows in the reference"] += 1
            elif said & heard:
                c["ERROR: cue heard, extractor missed it"] += 1
            else:
                c["ERROR: ASR dropped or changed the cue word"] += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--transcripts", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from jatayu.lexicon import Lexicon

    start = log_run(args.out, runner="eval.negation_breakdown", split="dev", tag=args.tag, transcripts=str(args.transcripts))
    rows = [r for r in map(json.loads, args.transcripts.read_text().splitlines()) if r.get("path", "").startswith("tts/")]
    res = classify(rows, Lexicon.load())
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "transcripts": str(args.transcripts),
                                                  "counts": res}, indent=2) + "\n")
    L = [f"# Negation and context on dev speech (`{args.tag}`, commit `{start['commit']}`)", "",
         f"Rules extractor (default) on `{args.transcripts}` ({len(rows)} clean dev clips). Counts only.", ""]
    for ctx, title in (("not_given", "Not given (administration-status errors)"), ("measurement", "Measurements")):
        L += [f"## {title}", "", "| Outcome | Count |", "|---|---|"]
        L += [f"| {k} | {v} |" for k, v in sorted(res[ctx].items(), key=lambda kv: (kv[0] != "records", kv[0]))]
        L.append("")
    (out / "report.md").write_text("\n".join(L) + "\n")
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
