"""python -m eval.flag_counts --tag <tag>   (dev only)

Flags raised by the rules NER + validator on every dev input (deterministic): the dev template sentences, the
off-template dev sentences, and the saved dev speech transcripts. Used for before/after regression counts."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.runlog import log_run
from jatayu import config

SPEECH = config.ROOT / "results/r4-dev-audio-rules-no-asr-flag/transcripts.jsonl"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from eval.offtemplate import load
    from jatayu.extract.rules import RulesExtractor
    from jatayu.lexicon import Lexicon
    from jatayu.validate import validate_all

    start = log_run(args.out, runner="eval.flag_counts", split="dev", tag=args.tag)
    lex = Lexicon.load()
    x = RulesExtractor(lex)
    dev = {u.id: u for u in load_split("dev")}
    speech = [(dev[r["utt_id"]], r["text"]) for r in map(json.loads, SPEECH.read_text().splitlines())
              if r.get("path", "").startswith("tts/")]
    sets = {"dev text": [(u, u.text) for u in dev.values()], "off-template": [(u, u.text) for u in load()],
            "dev speech (saved transcripts)": speech}
    res = {}
    for name, items in sets.items():
        c, entries = Counter(), 0
        for u, text in items:
            for e in validate_all(x.extract(text, datetime.fromisoformat(u.capture_time)), lex, []):
                entries += 1
                c.update(f.code for f in e.flags)
        res[name] = {"inputs": len(items), "entries": entries, "flags": sum(c.values()), "by_code": dict(c.most_common())}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "results": res}, indent=2) + "\n")
    print(json.dumps({k: {kk: v[kk] for kk in ("inputs", "entries", "flags")} for k, v in res.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
