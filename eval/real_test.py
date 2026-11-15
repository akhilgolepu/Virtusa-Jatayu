"""python -m eval.real_test --tag <freeze-tag>-real-test [--extractor rules] [--root data] [--release <file>]
python -m eval.real_test --freeze-manifest [--root data]   (once, after the last real test clip is imported)

Scores the REAL TEST recordings once, AGGREGATE ONLY. It refuses — before reading any clip — unless all three hold:
  1. the working tree is clean (eval/runlog.py: results/ excepted);
  2. the real test manifest (<root>/real/test/manifest.jsonl) has its SHA-256 frozen in the frozen-hash file
     (eval/frozen.sha256 for data/; <root>/frozen.sha256 for a scratch root), and the manifest still matches it;
  3. the evaluator's release file exists (default eval/real_test_release.json) and names that same manifest hash:
     {"release": "real-test", "manifest_sha256": "<hex>", "released_by": "...", "date": "..."}.
Then every clip is checked against the manifest (scripts/import_real.load_real), transcribed, extracted (default rules,
the demo extractor), validated, and scored against the gold entries of its prompt (prompts are test-split sentences).
Written: results/<tag>/metrics.json and report.md with clip and speaker counts, normalised and raw WER, drug-term
recall, entity P/R/F1, dangerous error (round-10 headline and the old matched-drug row), administration-status
errors. Never written or printed: a transcript, a per-clip or per-speaker result, an error list. One run_log row.
Do not run this until the evaluator's release file is in the repository (docs/freeze_checklist.md, D)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from eval.runlog import dirty_paths, log_run
from jatayu import config

RELEASE = config.ROOT / "eval" / "real_test_release.json"
MANIFEST_KEY = "real/test/manifest.jsonl"
CAPTURE = "2026-11-03T10:45:00+05:30"  # gold and extraction share one anchor when a row states no capture time


class RealTestRefused(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_file(root: Path) -> Path:
    from datagen.splits import _hash_file as hf

    return hf(root)


def _frozen(root: Path) -> dict[str, str]:
    f = _hash_file(root)
    if not f.exists():
        return {}
    return {rel: h for h, rel in (l.split(None, 1) for l in f.read_text().splitlines() if l.strip())}


def freeze_manifest(root: Path = config.DATA_DIR) -> str:
    """Write the real test manifest's hash into the frozen-hash file (freeze checklist B2). Refuses to change it."""
    m = root / "real" / "test" / "manifest.jsonl"
    if not m.exists():
        raise RealTestRefused(f"no real test manifest at {m}: import the clips first")
    h, frozen = _sha(m), _frozen(root)
    if MANIFEST_KEY in frozen and frozen[MANIFEST_KEY] != h:
        raise RealTestRefused("a different real test manifest hash is already frozen; it is never overwritten")
    if MANIFEST_KEY not in frozen:
        f = _hash_file(root)
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(f"{h}  {MANIFEST_KEY}\n")
    return h


def check_ready(root: Path, release: Path) -> str:
    """The three gates, in order; the manifest hash if all pass. Reads no clip."""
    dirty = dirty_paths()
    if dirty:
        raise RealTestRefused("the working tree is dirty: " + ", ".join(dirty[:10]))
    m = root / "real" / "test" / "manifest.jsonl"
    frozen = _frozen(root).get(MANIFEST_KEY)
    if frozen is None:
        raise RealTestRefused(f"the real test manifest hash is not frozen in {_hash_file(root)}")
    if not m.exists() or _sha(m) != frozen:
        raise RealTestRefused("the real test manifest is missing or changed since it was frozen")
    if not release.exists():
        raise RealTestRefused(f"no release file from the evaluator at {release}")
    rel = json.loads(release.read_text())
    if rel.get("release") != "real-test" or rel.get("manifest_sha256") != frozen:
        raise RealTestRefused("the release file does not release this real test manifest")
    return frozen


def score(root: Path, extractor: str, transcriber=None) -> dict:
    from datagen.schema import GoldUtterance
    from eval.asr_text import asr_norm, drugs_heard, word_errors
    from eval.metrics import Scorer
    from eval.run import _extract, _extractor, _norm_text
    from jatayu.asr_confidence import flag_low_confidence
    from jatayu.audio import decode_to_16k
    from scripts.import_real import load_real

    lex, x = _extractor(extractor)
    if transcriber is None:
        from jatayu.asr import Transcriber

        transcriber = Transcriber(lexicon=lex)
    rows = load_real("test", root, sealed_ok=True)  # every clip checked against the manifest (raises on a change)
    scorer, n = Scorer(), {"err": 0, "words": 0, "raw_err": 0, "raw_words": 0, "hits": 0, "den": 0}
    for r in rows:
        samples, _ = decode_to_16k((root / "real" / "test" / r["path"]).read_bytes())
        res = transcriber.transcribe(samples)
        capture = r.get("capture_time") or CAPTURE
        u = GoldUtterance(id=r["id"], family="real", category=r.get("category", "med_basic"), split="test",
                          lang=r.get("lang", "en"), text=r["reference"], capture_time=capture, entries=r.get("entries", []))
        preds = flag_low_confidence(_extract(x, lex, res.text, datetime.fromisoformat(capture)), res.words)
        scorer.add(u, preds)  # errors kept in memory only; never written
        e, w = word_errors(asr_norm(r["reference"], lex), asr_norm(res.text, lex))
        re_, rw = word_errors(_norm_text(r["reference"]), _norm_text(res.text))
        ref_d, hyp_d = drugs_heard(r["reference"], lex), drugs_heard(res.text, lex)
        n["err"] += e; n["words"] += w; n["raw_err"] += re_; n["raw_words"] += rw  # noqa: E702
        n["den"] += len(ref_d); n["hits"] += len(ref_d & hyp_d)  # noqa: E702
    m = scorer.metrics()
    return {"clips": len(rows), "speakers": len({r["speaker"] for r in rows}),
            "wer": round(n["err"] / max(n["words"], 1), 4), "wer_raw": round(n["raw_err"] / max(n["raw_words"], 1), 4),
            "drug_term_recall": round(n["hits"] / max(n["den"], 1), 4), "drug_term_den": n["den"],
            "entity": m["entity"]["micro"], "record_exact_match": m["record_exact_match"],
            "dangerous_error_r10": {k: m["dangerous_error_r10"][k] for k in ("count", "denominator", "rate",
                                                                           "uncaught_by_kind")},
            "dangerous_error_matched_drug_only": m["dangerous_error"],
            "administration_status_error": m["administration_status_error"]}


def main(argv: list[str] | None = None, transcriber=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag")
    ap.add_argument("--extractor", default="rules", choices=list(config.DEMO_EXTRACTORS))
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--release", type=Path, default=RELEASE)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    ap.add_argument("--freeze-manifest", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.freeze_manifest:
            print(f"real test manifest frozen: {freeze_manifest(args.root)}")
            return 0
        if not args.tag:
            ap.error("--tag is required")
        manifest = check_ready(args.root, args.release)
    except RealTestRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    start = log_run(args.out, runner="eval.real_test", split="real-test", tag=args.tag, extractor=args.extractor,
                    manifest_sha256=manifest)
    res = score(args.root, args.extractor, transcriber)
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "manifest_sha256": manifest,
                                                  "extractor": args.extractor, **res}, indent=2) + "\n")
    d, o, a, e = (res["dangerous_error_r10"], res["dangerous_error_matched_drug_only"],
                  res["administration_status_error"], res["entity"])
    L = [f"# Real test recordings — aggregate only (`{args.tag}`, commit `{start['commit']}`)", "",
         f"Manifest `{manifest[:16]}…` (frozen, released). Extractor: {args.extractor}. **Real speech, sealed test "
         "prompts; scored once.** No transcript or per-clip result is kept.", "",
         "| Measure | Value |", "|---|---|",
         f"| Clips / speakers | {res['clips']} / {res['speakers']} |",
         f"| WER normalised / raw | {res['wer']:.3f} / {res['wer_raw']:.3f} |",
         f"| Drug-term recall | {res['drug_term_recall']:.3f} (n={res['drug_term_den']}) |",
         f"| Entity F1 (P / R) | {e['f1']:.3f} ({e['precision']:.3f} / {e['recall']:.3f}) |",
         f"| **Dangerous errors (headline)** | **{d['count']} of {d['denominator']}** |",
         f"| Dangerous errors, matched-drug only (secondary) | {o['count']} of {o['denominator']} |",
         f"| Administration-status errors | {a['count']} of {a['denominator']} |"]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
