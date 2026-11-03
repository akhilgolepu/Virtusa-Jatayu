"""python -m scripts.import_real --split dev|test --speaker S01 --refs refs.tsv [--root data]

Imports real recordings: refs.tsv has one line per clip, "<path to audio file><TAB><reference text>" (what the
speaker was asked to say, written as on the prompt card). Each clip is decoded to 16 kHz mono WAV and stored as
data/real/<split>/<speaker>/<sha8>.wav; data/real/<split>/manifest.jsonl gets {id, speaker, path, sha256, reference,
duration_s, source, imported}, and data/real/<split>/manifest.sha256 lists every clip's SHA-256.

Real TEST clips are sealed: importing them is allowed, evaluating them is not (eval/real_wer.py refuses) until the
evaluator says so. Re-importing the same audio is a no-op (same SHA-256)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from jatayu import config

SPLITS = ("dev", "test")


def import_clips(split: str, speaker: str, refs: Path, root: Path) -> list[dict]:
    from jatayu.audio import SAMPLE_RATE, decode_to_16k

    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}")
    if not speaker.replace("-", "").replace("_", "").isalnum():
        raise ValueError("speaker id: letters, digits, - and _ only (no names)")
    base = root / "real" / split
    (base / speaker).mkdir(parents=True, exist_ok=True)
    manifest = base / "manifest.jsonl"
    rows = [json.loads(l) for l in manifest.read_text().splitlines() if l.strip()] if manifest.exists() else []
    seen = {r["sha256"] for r in rows}
    added = []
    with open(refs, encoding="utf-8", newline="") as fh:
        for src, reference in csv.reader(fh, delimiter="\t"):
            samples, wav = decode_to_16k(Path(src).read_bytes())
            sha = hashlib.sha256(wav).hexdigest()
            if sha in seen:
                continue
            rel = Path(speaker) / f"{sha[:8]}.wav"
            (base / rel).write_bytes(wav)
            row = {"id": f"real-{split}-{speaker}-{sha[:8]}", "speaker": speaker, "path": str(rel), "sha256": sha,
                   "reference": reference.strip(), "duration_s": round(len(samples) / SAMPLE_RATE, 3),
                   "source": Path(src).name, "imported": datetime.now().astimezone().isoformat()}
            rows.append(row)
            added.append(row)
            seen.add(sha)
    manifest.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (base / "manifest.sha256").write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in rows), encoding="utf-8")
    return added


def load_real(split: str, root: Path = config.DATA_DIR, sealed_ok: bool = False) -> list[dict]:
    """Real clips with their manifest checked. Test is sealed until the evaluator releases it."""
    if split == "test" and not sealed_ok:
        raise PermissionError("real test recordings are sealed until the evaluator says so")
    base = root / "real" / split
    manifest = base / "manifest.jsonl"
    if not manifest.exists():
        return []
    rows = [json.loads(l) for l in manifest.read_text().splitlines() if l.strip()]
    for r in rows:
        if hashlib.sha256((base / r["path"]).read_bytes()).hexdigest() != r["sha256"]:
            raise ValueError(f"real {split} clip changed since import: {r['path']}")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", choices=SPLITS, required=True)
    ap.add_argument("--speaker", required=True, help="an anonymous id such as S01 (never a name)")
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    args = ap.parse_args(argv)
    added = import_clips(args.split, args.speaker, args.refs, args.root)
    print(f"imported {len(added)} new clip(s) into {args.root / 'real' / args.split}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
