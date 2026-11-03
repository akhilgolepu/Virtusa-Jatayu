"""python -m eval.phonetic_sweep --tag r4-phonetic-sweep --transcripts results/<dev run>/transcripts.jsonl   (dev only)

Chooses the rules extractor's phonetic drug-match threshold on dev ASR transcripts: drug-field precision / recall /
F1 and entity F1 with phonetic matching off and at several thresholds (the transcripts are fixed, so only the
matcher changes)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.metrics import Scorer
from eval.runlog import log_run
from jatayu import config

THRESHOLDS = (None, 80, 84, 88, 92, 96)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--transcripts", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    import jatayu.extract.rules as rules_mod
    from jatayu.lexicon import Lexicon
    from jatayu.validate import validate_all

    start = log_run(args.out, runner="eval.phonetic_sweep", split="dev", tag=args.tag, transcripts=str(args.transcripts))
    lex = Lexicon.load()
    by_id = {u.id: u for u in load_split("dev")}
    rows = [json.loads(l) for l in args.transcripts.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r["path"].startswith("tts/")]
    res = {}
    for th in THRESHOLDS:
        rules_mod.PHONETIC_THRESHOLD = 101 if th is None else th  # 101 = never matches
        x = rules_mod.RulesExtractor(lex)
        sc = Scorer()
        for r in rows:
            u = by_id[r["utt_id"]]
            sc.add(u, validate_all(x.extract(r["text"], datetime.fromisoformat(u.capture_time)), lex, []))
        m = sc.metrics()
        d = m["entity"]["per_field"]["drug"]
        res["off" if th is None else str(th)] = {"drug_precision": d["precision"], "drug_recall": d["recall"],
                                                 "drug_f1": d["f1"], "entity_f1": m["entity"]["micro"]["f1"]}
        print(th, res["off" if th is None else str(th)], flush=True)
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "n_clips": len(rows),
                                                  "transcripts": str(args.transcripts), "rows": res}, indent=2) + "\n")
    L = [f"# Phonetic drug-match threshold (`{args.tag}`, dev, {len(rows)} clips, commit `{start['commit']}`)", "",
         f"Rules extractor on fixed dev ASR transcripts (`{args.transcripts}`); only the phonetic matcher changes.", "",
         "| Threshold | Drug P | Drug R | Drug F1 | Entity F1 |", "|---|---|---|---|---|"]
    L += [f"| {k} | {v['drug_precision']:.3f} | {v['drug_recall']:.3f} | {v['drug_f1']:.3f} | {v['entity_f1']:.3f} |"
          for k, v in res.items()]
    (out / "report.md").write_text("\n".join(L) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
