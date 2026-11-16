"""python -m scripts.recording_sheets [--parts 3] [--root data]

Writes data/recordings/recording_sheets.md: the sentences to read aloud, split into balanced parts, one per speaker,
in the same order the /record?part=N page shows them. The file stays in data/ (git-ignored, never committed): most
sentences are from the sealed TEST split. Speakers read them; nobody uses them to tune anything. Prints counts only."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from jatayu import config
from jatayu.corpus import CorpusStore, assign_parts

CONDITIONS = {"quiet": "a quiet room", "fan": "a fan or AC running near you", "street": "outdoors, or traffic noise",
              "siren-playback": "a siren sound playing in the background (phone speaker)",
              "fast": "speak quickly, as in a busy handover", "mumbled": "speak less clearly, as if tired or masked"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parts", type=int, default=3)
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    args = ap.parse_args(argv)
    store = CorpusStore(args.root / "recordings")
    prompts = store.prompts()
    part = assign_parts(prompts, args.parts)
    out = store.root / "recording_sheets.md"
    L = ["# Recording sheets — Scribe108 (synthetic sentences)", "",
         "**Do not commit, share or post this file.** Most sentences belong to the sealed test set: read them aloud, "
         "never use them to tune anything. All content is synthetic; no real patient.", "",
         "How to record: `docs/recording_guide.md`. Each speaker opens `http://localhost:8000/record?part=N&parts="
         f"{args.parts}` and reads **their part only**, in this order (the page shows the same order).", "",
         "Conditions: " + "; ".join(f"**{k}** = {v}" for k, v in CONDITIONS.items()) + ".", ""]
    for k in range(1, args.parts + 1):
        mine = [p for pid, p in prompts.items() if part[pid] == k]
        c = Counter(p.get("split") for p in mine)
        L += [f"## Part {k} — speaker S0{k} ({len(mine)} sentences)", "",
              f"Open `http://localhost:8000/record?part={k}&parts={args.parts}`. Afterwards: "
              f"`python -m scripts.import_real --from-recordings --speaker S0{k} --part {k} --parts {args.parts}`.", "",
              "| # | Condition | Lang | Sentence | Done |", "|---|---|---|---|---|"]
        L += [f"| {i} | {p.get('condition_hint', '')} | {p.get('lang', '')} | {p['text']} | ☐ |"
              for i, p in enumerate(mine, 1)]
        L.append("")
        print(f"part {k}: {len(mine)} sentences (test {c['test']}, dev {c['dev']}, "
              f"hinglish {sum(p.get('lang') == 'hinglish' for p in mine)})")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
