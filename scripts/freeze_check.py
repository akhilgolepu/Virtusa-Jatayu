"""python -m scripts.freeze_check [--pytest] [--record-models] [--out results/<tag>/freeze_check.json]

The mechanical half of docs/freeze_checklist.md. Read-only (except --record-models): prints PASS / FAIL per item and
exits 1 if any fails. It never prints a test or final_test record, and never reads the real recordings (data/real,
data/recordings).

  tree       the working tree is clean (results/ excepted, as in eval/runlog.py) and HEAD is pushed to its upstream
  frozen     test.jsonl and final_test.jsonl match eval/frozen.sha256; every test / final_test audio clip matches its
             frozen manifest
  lock       every package the requirements pull in is installed at the version in requirements.lock
  models     the Whisper model, the LLM and the read-back voice match eval/models.sha256 (--record-models writes it)
  config     committed defaults are in force: no JATAYU_* override in the environment; extractor rules; LLM-only off
  run_log    no row of results/run_log.jsonl on test or final_test is from a dirty tree
  tests      (--pytest) the full suite passes, model tests included
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from jatayu import config

MODELS_FILE = config.ROOT / "eval" / "models.sha256"
MODEL_FILES = {"whisper": config.ASR_MODEL_DIR / "model.bin", "llm": config.LLM_MODEL_PATH,
               "voice": config.READBACK_VOICE}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=config.ROOT, capture_output=True, text=True).stdout.strip()


def check_tree() -> dict:
    from eval.runlog import dirty_paths

    dirty = dirty_paths()
    ahead = _git("rev-list", "--count", "@{upstream}..HEAD") or "no upstream"
    ok = not dirty and ahead == "0"
    return {"pass": ok, "detail": f"HEAD {_git('rev-parse', '--short', 'HEAD')} on {_git('branch', '--show-current')}; "
                                  f"dirty: {', '.join(dirty[:5]) or 'none'}; commits not pushed: {ahead}"}


def check_frozen() -> dict:
    from datagen.audio_manifest import verify
    from datagen.splits import FROZEN_SETS, _path, _sha256, frozen_hashes

    hashes = frozen_hashes(config.DATA_DIR)
    bad = [s for s in FROZEN_SETS if _sha256(_path(s, config.DATA_DIR)) != hashes[_path(s, config.DATA_DIR).name]]
    for s in FROZEN_SETS:
        try:
            verify(s, config.DATA_DIR)
        except ValueError as exc:
            bad.append(f"{s} audio: {exc}")
    return {"pass": not bad, "detail": "; ".join(bad) or "test + final_test text and audio match eval/frozen.sha256"}


def check_lock() -> dict:
    from scripts.make_lock import pins

    locked = dict(l.split("==", 1) for l in (config.ROOT / "requirements.lock").read_text().splitlines()
                  if l.strip() and not l.startswith("#"))
    now = pins()
    diff = sorted({n for n in locked.keys() | now.keys() if locked.get(n) != now.get(n)})
    return {"pass": not diff, "detail": f"{len(locked)} pins match the installed packages" if not diff else
            "differs: " + ", ".join(f"{n} lock {locked.get(n)} / installed {now.get(n)}" for n in diff[:6])}


def check_models(record: bool) -> dict:
    now = {k: _sha(p) for k, p in MODEL_FILES.items() if p.exists()}
    missing = [k for k in MODEL_FILES if k not in now]
    if record:
        MODELS_FILE.write_text("".join(f"{h}  {MODEL_FILES[k].relative_to(config.ROOT)}\n" for k, h in now.items()))
    if not MODELS_FILE.exists():
        return {"pass": False, "detail": "eval/models.sha256 missing: run with --record-models at the freeze"}
    pinned = {rel: h for h, rel in (l.split("  ", 1) for l in MODELS_FILE.read_text().splitlines() if l.strip())}
    bad = [k for k, h in now.items() if pinned.get(str(MODEL_FILES[k].relative_to(config.ROOT))) != h] + missing
    return {"pass": not bad, "detail": f"differ or missing: {', '.join(bad)}" if bad else
            "whisper, llm and voice match eval/models.sha256", "sha256": now}


def check_config() -> dict:
    overrides = sorted(k for k in os.environ if k.startswith("JATAYU_"))
    problems = [f"environment overrides {', '.join(overrides)}"] if overrides else []
    if config.DEFAULT_EXTRACTOR != "rules":
        problems.append(f"default extractor {config.DEFAULT_EXTRACTOR}")
    if config.EXPERIMENTAL:
        problems.append("LLM-only experimental switch on")
    snap = {"extractor": config.DEFAULT_EXTRACTOR, "asr_model": config.ASR_MODEL_DIR.name, "asr_device": config.ASR_DEVICE,
            "asr_compute": config.ASR_COMPUTE_TYPE, "asr_word_p": config.ASR_WORD_PROB_THRESHOLD,
            "asr_prompt_aliases": config.ASR_PROMPT_ALIASES, "llm": config.LLM_MODEL_PATH.name,
            "keep_models": config.KEEP_MODELS, "experimental": config.EXPERIMENTAL}
    return {"pass": not problems, "detail": "; ".join(problems) or ", ".join(f"{k}={v}" for k, v in snap.items()),
            "config": snap}


def check_run_log() -> dict:
    rows = [json.loads(l) for l in (config.ROOT / "results/run_log.jsonl").read_text().splitlines() if l.strip()]
    sealed = [r for r in rows if r.get("split") in ("test", "final_test")]
    dirty = [r["tag"] for r in sealed if r.get("dirty")]
    return {"pass": not dirty, "detail": f"{len(rows)} rows; {len(sealed)} on test/final_test, "
                                         f"{len(dirty)} of them dirty{': ' + ', '.join(dirty[:5]) if dirty else ''}"}


def check_tests() -> dict:
    out = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=config.ROOT, capture_output=True, text=True)
    tail = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-200:]
    return {"pass": out.returncode == 0 and "skipped" not in tail, "detail": tail}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pytest", action="store_true", help="also run the full test suite")
    ap.add_argument("--record-models", action="store_true", help="write eval/models.sha256 from the installed models")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    plan = {"tree": check_tree, "frozen": check_frozen, "lock": check_lock,
            "models": lambda: check_models(args.record_models), "config": check_config, "run_log": check_run_log}
    if args.pytest:
        plan["tests"] = check_tests
    results = {}
    for name, fn in plan.items():
        try:
            results[name] = fn()
        except Exception as exc:
            results[name] = {"pass": False, "detail": f"{type(exc).__name__}: {exc}"}
        print(f"{'PASS' if results[name]['pass'] else 'FAIL'}  {name:8s} {results[name]['detail']}", flush=True)
    ok = all(r["pass"] for r in results.values())
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"created": datetime.now().astimezone().isoformat(), "all_pass": ok,
                                        "checks": results}, indent=2) + "\n", encoding="utf-8")
    print("FREEZE CHECK PASSED" if ok else "FREEZE CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
