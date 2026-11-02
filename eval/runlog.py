"""Append-only run log (results/run_log.jsonl): one line per evaluation run, so test and final_test run counts are
auditable. Written at the START of a run, so an interrupted run still counts.

Every row records whether the working tree was dirty. A run on test or final_test is REFUSED on a dirty tree, so
every sealed-split number traces to a commit. Paths under results/ do not make the tree dirty: they are outputs, and
every run appends to this log."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from jatayu import config

SEALED = ("test", "final_test")
OUTPUTS = "results/"


class DirtyTreeError(RuntimeError):
    pass


def dirty_paths() -> list[str]:
    """Modified or untracked (not ignored) paths outside results/."""
    out = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=config.ROOT).stdout
    paths = [line[3:].split(" -> ")[-1].strip('"') for line in out.splitlines() if line.strip()]
    return [p for p in paths if not p.startswith(OUTPUTS)]


def commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=config.ROOT)
        return out.stdout.strip() + ("-dirty" if dirty_paths() else "")
    except OSError:
        return "unknown"


def log_run(out_dir: Path, **fields) -> dict:
    dirty = dirty_paths()
    if fields.get("split") in SEALED and dirty:
        raise DirtyTreeError(f"refusing to run on {fields['split']} with a dirty working tree; commit or stash first: "
                             + ", ".join(dirty[:10]))
    row = {"timestamp": datetime.now().astimezone().isoformat(), "commit": commit(), "dirty": bool(dirty),
           "dirty_paths": dirty[:20], **fields}
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "run_log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row
