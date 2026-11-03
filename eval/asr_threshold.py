"""python -m eval.asr_threshold --tag r4-asr-threshold --transcripts results/<dev audio run>/transcripts.jsonl   (dev only)

Chooses the low_asr_confidence threshold on DEV speech. Each matched given-medication record (rules extractor on the
saved transcript) is labelled correct (drug, dose, unit, route all right) or wrong, and gets the lowest Whisper word
probability over its drug / dose / unit words. For each threshold: share of wrong records flagged (catch) and share
of correct records flagged (false alarm). Criterion, fixed before looking: the largest catch - false alarm (Youden J);
ties go to the lower threshold (fewer flags)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.metrics import DANGER_FIELDS, _overlap, gold_values, pred_values, same
from eval.runlog import log_run
from jatayu import config

GRID = [round(0.05 * k, 2) for k in range(1, 20)]


def records(rows: list[dict], lex) -> list[tuple[bool, float]]:
    """(is_correct, lowest word probability over drug/dose/unit) per matched given-medication record."""
    from jatayu.asr_confidence import CHECKED, lowest
    from jatayu.extract.rules import RulesExtractor
    from jatayu.models import MedicationEntry
    from jatayu.validate import validate_all

    by_id = {u.id: u for u in load_split("dev")}
    x = RulesExtractor(lex)
    out = []
    for r in rows:
        u = by_id[r["utt_id"]]
        cap = datetime.fromisoformat(u.capture_time)
        preds = [(p, pred_values(p)) for p in validate_all(x.extract(r["text"], cap), lex, [])]
        free = list(range(len(preds)))
        for g in u.entries:
            if g.kind != "medication" or g.context != "given":
                continue
            gv = gold_values(g, cap)
            best, score = None, -1
            for i in free:
                s = _overlap(gv, preds[i][1])
                if s > score:
                    best, score = i, s
            if best is None or score < 0:
                continue
            free.remove(best)
            p, pv = preds[best]
            if not isinstance(p, MedicationEntry):
                continue
            ps = [w["p"] for f in CHECKED if getattr(p, f).span and (w := lowest(r.get("words", []), getattr(p, f).span))]
            if ps:
                out.append((all(same(f, gv[f], pv[f]) for f in DANGER_FIELDS), min(ps)))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--transcripts", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from jatayu.lexicon import Lexicon

    start = log_run(args.out, runner="eval.asr_threshold", split="dev", tag=args.tag, transcripts=str(args.transcripts))
    rows = [json.loads(l) for l in args.transcripts.read_text().splitlines() if l.strip()]
    if not any(r.get("words") for r in rows):
        raise ValueError("these transcripts carry no word probabilities")
    recs = records([r for r in rows if r["path"].startswith("tts/")], Lexicon.load())
    good = [p for ok, p in recs if ok]
    bad = [p for ok, p in recs if not ok]
    sweep = []
    for t in GRID:
        catch = sum(p < t for p in bad) / max(len(bad), 1)
        alarm = sum(p < t for p in good) / max(len(good), 1)
        sweep.append({"threshold": t, "catch_wrong": round(catch, 4), "flag_rate_correct": round(alarm, 4),
                      "youden_j": round(catch - alarm, 4)})
    chosen = max(sweep, key=lambda s: (s["youden_j"], -s["threshold"]))
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "transcripts": str(args.transcripts),
                                                  "n_correct": len(good), "n_wrong": len(bad), "chosen": chosen,
                                                  "sweep": sweep}, indent=2) + "\n")
    L = [f"# low_asr_confidence threshold (`{args.tag}`, dev, commit `{start['commit']}`)", "",
         f"{len(good)} correct and {len(bad)} wrong matched given-medication records (rules extractor on "
         f"`{args.transcripts}`). Criterion fixed in advance: max(catch - false alarm), ties → lower threshold.", "",
         f"**Chosen: p < {chosen['threshold']}** — flags {chosen['catch_wrong']:.1%} of wrong records and "
         f"{chosen['flag_rate_correct']:.1%} of correct records.", "",
         "| Threshold | Wrong records flagged | Correct records flagged | J |", "|---|---|---|---|"]
    L += [f"| {s['threshold']} | {s['catch_wrong']:.3f} | {s['flag_rate_correct']:.3f} | {s['youden_j']:.3f} |" for s in sweep]
    (out / "report.md").write_text("\n".join(L) + "\n")
    print(f"chosen {chosen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
