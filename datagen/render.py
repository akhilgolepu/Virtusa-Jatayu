"""python -m datagen.render [--splits train dev test] [--root data]

Renders every synthetic utterance with Piper into <root>/audio/tts/<split>/ (resumable)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from datagen.splits import load_split
from datagen.tts import render_split
from jatayu import config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--splits", nargs="+", default=["dev", "test", "train"])
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    args = ap.parse_args(argv)
    for split in args.splits:
        t0 = time.perf_counter()
        utts = load_split(split, final=(split == "test"), root=args.root)  # rendering builds the test set
        rows = render_split(split, utts, args.root / "audio" / "tts")
        hours = sum(r["duration_s"] for r in rows) / 3600
        print(f"{split}: {len(rows)} clips, {hours:.2f} h audio, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
