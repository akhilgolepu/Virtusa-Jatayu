"""python -m datagen.audio_manifest --splits test final_test [--freeze]

SHA-256 of every rendered clip (clean and noisy) of a held-out split, in data/audio/manifests/<split>.audio.sha256.
--freeze writes each manifest's own hash into eval/frozen.sha256 (next to the split hashes), so a later speech run on
test can prove it heard exactly the audio that was frozen. Building a manifest reads files; it evaluates nothing."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from datagen.splits import _hash_file, frozen_hashes
from jatayu import config


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_path(split: str, root: Path) -> Path:
    return root / "audio" / "manifests" / f"{split}.audio.sha256"


def build(split: str, root: Path) -> Path:
    lines = []
    for sub in ("tts", "noisy"):
        index = root / "audio" / sub / f"{split}.jsonl"
        lines.append(f"{_sha(index)}  {sub}/{split}.jsonl")
        for r in (json.loads(l) for l in index.read_text().splitlines() if l.strip()):
            lines.append(f"{_sha(root / 'audio' / sub / r['path'])}  {sub}/{r['path']}")
    out = manifest_path(split, root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def freeze(split: str, root: Path) -> None:
    hf = _hash_file(root)
    m = manifest_path(split, root)
    rel = f"audio/manifests/{m.name}"
    kept = [l for l in hf.read_text().splitlines() if l.strip() and not l.endswith(f"  {rel}")]
    hf.write_text("\n".join([*kept, f"{_sha(m)}  {rel}"]) + "\n", encoding="utf-8")


def verify(split: str, root: Path = config.DATA_DIR) -> None:
    """Raise unless the manifest matches its frozen hash and every clip matches the manifest."""
    m = manifest_path(split, root)
    frozen = frozen_hashes(root).get(m.name)
    if frozen is None:
        raise ValueError(f"no frozen audio manifest for {split}")
    if _sha(m) != frozen:
        raise ValueError(f"{split} audio manifest modified since it was frozen")
    for line in m.read_text().splitlines():
        h, rel = line.split("  ", 1)
        if _sha(root / "audio" / rel) != h:
            raise ValueError(f"{split} audio changed since it was frozen: {rel}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--splits", nargs="+", default=["test", "final_test"])
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args(argv)
    for split in args.splits:
        m = build(split, args.root)
        n = len(m.read_text().splitlines())
        if args.freeze:
            freeze(split, args.root)
        print(f"{split}: {n} files hashed -> {m}{' (frozen)' if args.freeze else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
