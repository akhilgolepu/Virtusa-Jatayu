"""python -m eval.run --split dev|test|offtemplate_dev --tag m3-dev [--extractor hybrid] [--mode text|audio|noisy]
                   [--limit N] [--transcripts results/<tag>/transcripts.jsonl]

Runs the pipeline on a frozen split and writes results/<tag>/metrics.json, report.md and errors.jsonl.
Every number on a slide must trace to one of these files. final_test is refused unless --sealed-ok (Stage 3 S7).
Audio modes on dev save transcripts.jsonl; --transcripts reuses one, so several extractors score the SAME ASR output.
Noisy mode also scores the clean clips of the same utterances (snr "clean"): a paired noise curve.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from datagen.splits import _path, frozen_hashes, load_split
from eval.asr_text import asr_norm, drugs_heard, word_errors
from eval.metrics import Scorer
from eval.runlog import log_run
from jatayu import config

SNRS = (20, 10, 5)
TEXT_LABEL = "template-generated; extractor and generator share a lexicon; not a headline number"
SPEECH_LABEL = "synthetic speech (Piper)"
OFFTEMPLATE_LABEL = "hand-written off-template dev sentences (eval/offtemplate_dev.yaml); dev only"
SEALED = ("test", "final_test")  # real recordings are not wired into the harness yet


def _extractor(name: str):
    from jatayu.extract.hybrid import HybridExtractor
    from jatayu.extract.llm import LlmExtractor
    from jatayu.extract.rules import RulesExtractor
    from jatayu.lexicon import Lexicon
    from jatayu.llm import LlmRunner

    lex = Lexicon.load()
    rules = RulesExtractor(lex)
    if name == "rules":
        return lex, rules
    runner = LlmRunner(config.LLM_MODEL_PATH)
    return lex, (LlmExtractor(lex, lambda: runner) if name == "llm" else HybridExtractor(lex, lambda: runner, rules))


def _extract(x, lex, text: str, capture: datetime):
    from jatayu.validate import validate_all

    if hasattr(x, "extract_with_warnings"):
        entries, _ = x.extract_with_warnings(text, capture)
    else:
        entries = x.extract(text, capture)
    return validate_all(entries, lex, [])


def _norm_text(s: str) -> str:
    return " ".join(re.sub(r"[^\w\s.]", " ", s.lower()).replace(" .", " ").split())


def _leakage(root: Path) -> dict:
    fam = {s: {u.family for u in load_split(s, root=root)} for s in ("train", "dev")}
    test = load_split("test", final=True, root=root)
    final = load_split("final_test", final=True, sealed_ok=True, root=root)  # family/pattern ids only, no scoring
    pattern = lambda u: u.id.rsplit("-", 1)[0]  # noqa: E731
    return {"test_families_in_train_or_dev": len({u.family for u in test} & (fam["train"] | fam["dev"])),
            "test_patterns_in_final_test": len({pattern(u) for u in test} & {pattern(u) for u in final})}


def _audio_rows(root: Path, split: str, mode: str) -> list[dict]:
    sub = "tts" if mode == "audio" else "noisy"
    path = root / "audio" / sub / f"{split}.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _load(args, root: Path):
    if args.split == "offtemplate_dev":
        from eval.offtemplate import load

        return load()
    return load_split(args.split, final=args.split in ("test", "final_test"), sealed_ok=args.sealed_ok, root=root)


def _cached(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    return {r["path"]: r for r in map(json.loads, path.read_text().splitlines()) if r}


def run(args, start: dict) -> dict:
    root = Path(args.root)
    utts = _load(args, root)
    by_id = {u.id: u for u in utts}
    lex, x = _extractor(args.extractor)
    scorers: dict[str, Scorer] = defaultdict(Scorer)
    latencies: list[float] = []
    evaluated: set[str] = set()
    transcripts: list[dict] = []
    asr_stats = {"wer_num": 0, "wer_den": 0, "raw_num": 0, "raw_den": 0, "drug_hits": 0, "drug_total": 0,
                 "surface_hits": 0, "surface_total": 0, "by_accent": defaultdict(lambda: [0, 0])}

    if args.mode == "text":
        for u in utts[: args.limit or None]:
            t0 = time.perf_counter()
            preds = _extract(x, lex, u.text, datetime.fromisoformat(u.capture_time))
            latencies.append(time.perf_counter() - t0)
            evaluated.add(u.id)
            scorers["all"].add(u, preds)
            scorers[f"category:{u.category}"].add(u, preds)
            scorers[f"lang:{u.lang}"].add(u, preds)
    else:
        from jatayu.asr import Transcriber
        from jatayu.audio import decode_to_16k

        from jatayu.asr_confidence import flag_low_confidence

        asr = Transcriber(model_dir=args.asr_model, lexicon=lex)
        cache = _cached(args.transcripts)
        if args.split in SEALED:  # the audio heard must be the audio that was frozen
            from datagen.audio_manifest import verify

            verify(args.split, root)
        rows = _audio_rows(root, args.split, args.mode)
        if args.limit:  # keep whole utterances across voices/SNRs so subsets stay comparable
            keep = sorted({r["utt_id"] for r in rows})[: args.limit]
            rows = [r for r in rows if r["utt_id"] in set(keep)]
        sub = "tts" if args.mode == "audio" else "noisy"
        rows = [{**r, "file": f"{sub}/{r['path']}"} for r in rows]
        if args.mode == "noisy":  # the clean clip of each utterance: same voice, same words (paired curve)
            ids = {r["utt_id"] for r in rows}
            rows = [{**r, "file": f"tts/{r['path']}", "snr_db": "clean"}
                    for r in _audio_rows(root, args.split, "audio") if r["utt_id"] in ids] + rows
        for r in rows:
            u = by_id.get(r["utt_id"])
            if u is None:
                continue
            t0 = time.perf_counter()
            if r["file"] in cache:
                hyp, words = cache[r["file"]]["text"], cache[r["file"]].get("words", [])
            else:
                samples, _ = decode_to_16k((root / "audio" / r["file"]).read_bytes())
                res = asr.transcribe(samples)
                hyp, words = res.text, res.words
            transcripts.append({"path": r["file"], "utt_id": u.id, "voice": r["voice"], "text": hyp, "words": words})
            preds = flag_low_confidence(_extract(x, lex, hyp, datetime.fromisoformat(u.capture_time)), words,
                                        args.asr_word_p)
            latencies.append(time.perf_counter() - t0)
            evaluated.add(u.id)
            raw_err, raw_words = word_errors(_norm_text(u.text), _norm_text(hyp))
            err, words = word_errors(asr_norm(u.text, lex), asr_norm(hyp, lex))
            asr_stats["raw_num"] += raw_err
            asr_stats["raw_den"] += raw_words
            asr_stats["wer_num"] += err
            asr_stats["wer_den"] += words
            asr_stats["by_accent"][r["accent"]][0] += err
            asr_stats["by_accent"][r["accent"]][1] += words
            ref_drugs, hyp_drugs = drugs_heard(u.text, lex), drugs_heard(hyp, lex)
            for e in u.entries:
                if e.drug is not None:
                    asr_stats["surface_total"] += 1
                    asr_stats["surface_hits"] += e.drug.surface.lower() in hyp.lower()
                    if e.drug.value in ref_drugs:
                        asr_stats["drug_total"] += 1
                        asr_stats["drug_hits"] += e.drug.value in hyp_drugs
            meta = {"asr_text": hyp, "voice": r["voice"], **({"snr_db": r["snr_db"]} if "snr_db" in r else {})}
            group = f"snr:{r['snr_db']}" if "snr_db" in r else "all"
            scorers[group].add(u, preds, meta)
            if group not in ("all", "snr:clean"):  # "all" in noisy mode = the noisy clips only
                scorers["all"].add(u, preds, meta)
            scorers[f"accent:{r['accent']}"].add(u, preds, meta)

    m = scorers["all"].metrics()
    out = {
        "config": {"split": args.split, "mode": args.mode, "extractor": args.extractor, "tag": args.tag,
                   "n_utterances": len(evaluated), "n_clips": len(latencies),
                   "split_sha256": frozen_hashes(root).get(_path(args.split, root).name) if args.split in ("test", "final_test") else None,
                   "commit_at_start": start["commit"], "started": start["timestamp"],
                   "created": datetime.now().astimezone().isoformat(),
                   "source_label": OFFTEMPLATE_LABEL if args.split == "offtemplate_dev" else
                   TEXT_LABEL if args.mode == "text" else SPEECH_LABEL,
                   "asr_model": Path(args.asr_model).name if args.mode != "text" else None,
                   "asr_prompt_aliases": config.ASR_PROMPT_ALIASES if args.mode != "text" else None,
                   "asr_word_p_threshold": args.asr_word_p if args.mode != "text" else None,
                   "llm_model": config.LLM_MODEL_PATH.name if args.extractor != "rules" else None},
        "metrics": m,
        "groups": {k: {"entity_f1": v.metrics()["entity"]["micro"]["f1"],
                       "record_exact_match": v.metrics()["record_exact_match"]["rate"],
                       "dangerous_error": v.metrics()["dangerous_error"],
                       "administration_status_error": v.metrics()["administration_status_error"]} for k, v in sorted(scorers.items()) if k != "all"},
        "latency_s": _lat(latencies),
        "leakage": _leakage(root),
    }
    if args.mode != "text":
        out["asr"] = {"wer": round(asr_stats["wer_num"] / max(asr_stats["wer_den"], 1), 4),
                      "wer_definition": "reference and hypothesis normalised the same way (eval/asr_text.py)",
                      "wer_raw": round(asr_stats["raw_num"] / max(asr_stats["raw_den"], 1), 4),
                      "drug_term_recall": round(asr_stats["drug_hits"] / max(asr_stats["drug_total"], 1), 4),
                      "drug_term_recall_den": asr_stats["drug_total"],
                      "drug_term_recall_surface": round(asr_stats["surface_hits"] / max(asr_stats["surface_total"], 1), 4),
                      "wer_by_accent": {a: round(n / max(d, 1), 4) for a, (n, d) in asr_stats["by_accent"].items()}}
    if args.mode == "noisy":
        out["noise_curve"] = {str(s): scorers[f"snr:{s}"].metrics()["entity"]["micro"]["f1"] for s in ("clean", *SNRS)}
        out["noise_curve_paired_on"] = f"the same {len(evaluated)} utterances (one voice each) at every condition"
    if args.transcripts:
        out["config"]["transcripts_from"] = str(args.transcripts)
    errors = scorers["all"].errors()
    return out, errors, transcripts


def _lat(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0, "p50": 0.0, "p95": 0.0}
    s = sorted(xs)
    return {"n": len(s), "p50": round(statistics.median(s), 4), "p95": round(s[min(len(s) - 1, int(0.95 * len(s)))], 4),
            "mean": round(statistics.fmean(s), 4)}


def _report(o: dict, errors: list[dict]) -> str:
    m, c = o["metrics"], o["config"]
    lines = [f"# Evaluation `{c['tag']}`", "",
             f"Split **{c['split']}** · mode **{c['mode']}** · extractor **{c['extractor']}** · "
             f"n = {c['n_utterances']} utterances · commit at start `{c['commit_at_start']}`",
             f"**Source: {c['source_label']}**",
             f"Split hash: `{c['split_sha256']}`" if c["split_sha256"] else "", "",
             "Decision-support demo, not a clinical device. Synthetic data (see README).", "",
             "| Metric | Value |", "|---|---|",
             f"| Entity F1 (micro) | {m['entity']['micro']['f1']:.3f} (P {m['entity']['micro']['precision']:.3f}, "
             f"R {m['entity']['micro']['recall']:.3f}) |",
             f"| Record exact match | {m['record_exact_match']['count']}/{m['record_exact_match']['denominator']} "
             f"= {m['record_exact_match']['rate']:.3f} |",
             f"| **Dangerous errors** | **{m['dangerous_error']['count']} of {m['dangerous_error']['denominator']}** "
             f"({m['dangerous_error']['rate']:.2%}; strict: weight_based_dose and low_asr_confidence do not catch) |",
             f"| Dangerous errors, lenient (weight_based_dose and low_asr_confidence count as catches) | "
             f"{m['dangerous_error_lenient']['count']} of {m['dangerous_error_lenient']['denominator']} |",
             f"| **Administration-status errors** (not given, recorded as given) | "
             f"**{m['administration_status_error']['count']} of {m['administration_status_error']['denominator']}** |",
             f"| Context errors (not-given / measurement emitted unflagged) | {m['context_error']['count']} of "
             f"{m['context_error']['denominator']} |",
             f"| Deliberate dose anomalies flagged | {m['anomaly_flagged']['count']} of {m['anomaly_flagged']['denominator']} |",
             f"| Accepted fields with a source quote | {m['source_quote_coverage']['count']} of "
             f"{m['source_quote_coverage']['denominator']} |",
             f"| Latency p50 / p95 (s) | {o['latency_s']['p50']} / {o['latency_s']['p95']} (n={o['latency_s']['n']}) |"]
    if "asr" in o:
        a = o["asr"]
        lines += [f"| WER (normalised: numbers, units, routes; same on both sides) | {a['wer']:.3f} |",
                  f"| WER raw (lowercase, punctuation stripped) | {a['wer_raw']:.3f} |",
                  f"| Drug-term recall (lexicon names in the reference) | {a['drug_term_recall']:.3f} "
                  f"(n={a['drug_term_recall_den']}) |"]
    if "noise_curve" in o:
        lines += ["", "## Noise curve (entity F1)", "", "| SNR dB | F1 |", "|---|---|"]
        lines += [f"| {s} | {f:.3f} |" for s, f in o["noise_curve"].items()]
    lines += ["", "## Per field", "", "| Field | P | R | F1 | gold |", "|---|---|---|---|---|"]
    lines += [f"| {f} | {v['precision']:.3f} | {v['recall']:.3f} | {v['f1']:.3f} | {v['gold']} |"
              for f, v in m["entity"]["per_field"].items() if v["gold"] or v["pred"]]
    lines += ["", "## Groups", "", "| Group | Entity F1 | Exact match | Dangerous |", "|---|---|---|---|"]
    lines += [f"| {g} | {v['entity_f1']:.3f} | {v['record_exact_match']:.3f} | "
              f"{v['dangerous_error']['count']}/{v['dangerous_error']['denominator']} |" for g, v in o["groups"].items()]
    lines += ["", "## Leakage checks", "", f"- test families in train/dev: {o['leakage']['test_families_in_train_or_dev']}",
              f"- test patterns in final_test: {o['leakage']['test_patterns_in_final_test']}", "",
              "## Five worst failures", ""]
    if c["split"] in SEALED:
        lines.append("Not shown: test and final_test outputs are aggregate only.")
        errors = []
    for e in errors[:5]:
        lines.append(f"- `{e['id']}` ({e['kind']}{', DANGEROUS' if e['dangerous'] else ''}): “{e['input']}”"
                     + (f" → ASR “{e['asr_text']}”" if e.get("asr_text") else "")
                     + f"  \n  output {e.get('output')}  \n  expected {e.get('expected')}")
    return "\n".join(l for l in lines if l is not None) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", choices=["dev", "test", "final_test", "offtemplate_dev"], required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--extractor", choices=["rules", "llm", "hybrid"], default="hybrid")
    ap.add_argument("--mode", choices=["text", "audio", "noisy"], default="text")
    ap.add_argument("--limit", type=int, default=0, help="first N utterances (by id in audio modes)")
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    ap.add_argument("--sealed-ok", action="store_true", help="allow final_test (Stage 3 S7 only)")
    ap.add_argument("--transcripts", type=Path, help="reuse ASR transcripts (a transcripts.jsonl from a dev run)")
    ap.add_argument("--asr-model", type=Path, default=config.ASR_MODEL_DIR)
    ap.add_argument("--asr-word-p", type=float, default=config.ASR_WORD_PROB_THRESHOLD,
                    help="flag drug/dose/unit words Whisper heard below this probability (low_asr_confidence)")
    args = ap.parse_args(argv)
    if args.split == "final_test" and not args.sealed_ok:
        raise PermissionError("final_test is sealed until Stage 3 S7; pass --sealed-ok only then")
    start = log_run(args.out, runner="eval.run", split=args.split, tag=args.tag, mode=args.mode,
                    extractor=args.extractor, limit=args.limit)
    if args.split == "offtemplate_dev" and args.mode != "text":
        raise ValueError("offtemplate_dev is text only")
    o, errors, transcripts = run(args, start)
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    if transcripts and args.split == "dev":  # never written for test/final_test (aggregate outputs only there)
        (out / "transcripts.jsonl").write_text("".join(json.dumps(t) + "\n" for t in transcripts), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(o, indent=2, default=str) + "\n", encoding="utf-8")
    if args.split not in SEALED:  # individual test/final_test records are never written
        (out / "errors.jsonl").write_text("".join(json.dumps(e, default=str) + "\n" for e in errors), encoding="utf-8")
    (out / "report.md").write_text(_report(o, errors), encoding="utf-8")
    m = o["metrics"]
    print(f"{args.tag}: entity F1 {m['entity']['micro']['f1']:.3f} · exact {m['record_exact_match']['rate']:.3f} · "
          f"dangerous {m['dangerous_error']['count']}/{m['dangerous_error']['denominator']} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
