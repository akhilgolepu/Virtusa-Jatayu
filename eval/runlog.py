"""Append-only run log (results/run_log.jsonl): one line per evaluation run, so test and final_test run counts are
auditable. Written at the START of a run, so an interrupted run still counts."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from jatayu import config


def commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=config.ROOT)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                               text=True, cwd=config.ROOT).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except OSError:
        return "unknown"


def log_run(out_dir: Path, **fields) -> dict:
    row = {"timestamp": datetime.now().astimezone().isoformat(), "commit": commit(), **fields}
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "run_log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row
