"""python -m eval.real_wer --tag r4-real-vs-piper --piper results/<dev speech run>   (real DEV clips only)

Compares speech recognition on real dev recordings (data/real/dev, imported by scripts/import_real.py) with the
Piper dev run given: normalised WER, raw WER and drug-term recall, overall and per speaker. Real test clips are
sealed and refused. Real clips have reference text only (no gold entries), so this is an ASR comparison."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from eval.asr_text import asr_norm, drugs_heard, word_errors
from eval.run import _norm_text
from eval.runlog import log_run
from jatayu import config


def score(rows: list[dict], lex) -> dict:
    agg = defaultdict(lambda: {"err": 0, "words": 0, "raw_err": 0, "raw_words": 0, "hits": 0, "den": 0, "clips": 0})
    for r in rows:
        for key in ("all", f"speaker:{r['speaker']}"):
            a = agg[key]
            e, n = word_errors(asr_norm(r["reference"], lex), asr_norm(r["transcript"], lex))
            re_, rn = word_errors(_norm_text(r["reference"]), _norm_text(r["transcript"]))
            ref_d, hyp_d = drugs_heard(r["reference"], lex), drugs_heard(r["transcript"], lex)
            a["err"] += e; a["words"] += n; a["raw_err"] += re_; a["raw_words"] += rn  # noqa: E702
            a["den"] += len(ref_d); a["hits"] += len(ref_d & hyp_d); a["clips"] += 1  # noqa: E702
    return {k: {"clips": a["clips"], "wer": round(a["err"] / max(a["words"], 1), 4),
                "wer_raw": round(a["raw_err"] / max(a["raw_words"], 1), 4),
                "drug_term_recall": round(a["hits"] / max(a["den"], 1), 4), "drug_den": a["den"]} for k, a in agg.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--piper", type=Path, required=True, help="a dev speech run folder (metrics.json)")
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from scripts.import_real import load_real

    clips = load_real(args.split, args.root)  # raises for test: sealed
    start = log_run(args.out, runner="eval.real_wer", split=f"real-{args.split}", tag=args.tag, n=len(clips))
    piper = json.loads((args.piper / "metrics.json").read_text())
    rows = []
    if clips:
        from jatayu.asr import Transcriber
        from jatayu.audio import decode_to_16k
        from jatayu.lexicon import Lexicon

        lex = Lexicon.load()
        asr = Transcriber(lexicon=lex)
        for c in clips:
            samples, _ = decode_to_16k((args.root / "real" / args.split / c["path"]).read_bytes())
            rows.append({**c, "transcript": asr.transcribe(samples).text})
        real = score(rows, lex)
    else:
        real = {}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    pa = piper["asr"]
    o = {"commit": start["commit"], "piper_run": str(args.piper), "piper": {k: pa.get(k) for k in
         ("wer", "wer_raw", "drug_term_recall", "drug_term_recall_den", "wer_by_accent")}, "real": real}
    (out / "metrics.json").write_text(json.dumps(o, indent=2) + "\n", encoding="utf-8")
    (out / "transcripts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    L = [f"# Real vs Piper speech, dev (`{args.tag}`, commit `{start['commit']}`)", "",
         f"Piper run: `{args.piper}` ({piper['config']['n_clips']} synthetic clips). Real: `data/real/dev` "
         f"({len(clips)} clips). Same ASR settings, same normalisation (eval/asr_text.py).", "",
         "| | Clips | WER normalised | WER raw | Drug-term recall |", "|---|---|---|---|---|",
         f"| Piper (synthetic) | {piper['config']['n_clips']} | {pa['wer']:.3f} | {pa.get('wer_raw', 0):.3f} | "
         f"{pa['drug_term_recall']:.3f} (n={pa.get('drug_term_recall_den', '—')}) |"]
    for k, v in sorted(real.items()):
        L.append(f"| real {k} | {v['clips']} | {v['wer']:.3f} | {v['wer_raw']:.3f} | {v['drug_term_recall']:.3f} (n={v['drug_den']}) |")
    if not clips:
        L += ["", "**No real dev recordings have been imported yet** (`python -m scripts.import_real --split dev ...`)."]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(clips)} real dev clips -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
