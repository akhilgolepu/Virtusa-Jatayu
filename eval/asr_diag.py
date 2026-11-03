"""python -m eval.asr_diag --tag r3-asr-diag [--n 100] [--seed 3]   (dev only)

Speech diagnosis: on a fixed random subset of dev clips, change ONE ASR setting at a time (VAD, vocabulary prompt,
beam size, model size) and report raw WER, normalised WER (eval/asr_text.py, same function on both sides), drug-term
recall and entity F1. Extraction is the rules extractor so the only thing that changes between rows is the transcript.
Also checks that every clip reaches Whisper as 16 kHz mono and writes 10 random (reference, transcript) pairs.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import wave
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.asr_text import asr_norm, drugs_heard, word_errors
from eval.metrics import Scorer
from eval.run import _audio_rows, _norm_text
from eval.runlog import log_run
from jatayu import config

BASE = {"model": "small.en", "beam": 5, "vad": True, "prompt": True, "aliases": False, "hotwords": False}
VARIANTS = [("baseline", {}), ("vad off", {"vad": False}), ("prompt off", {"prompt": False}),
            ("beam 1", {"beam": 1}), ("beam 10", {"beam": 10}), ("medium.en", {"model": "medium.en"}),
            # round 4: vocabulary coverage and larger models
            ("prompt+aliases", {"aliases": True}), ("hotwords", {"hotwords": True}),
            ("large-v3-turbo", {"model": "large-v3-turbo"}), ("distil-large-v3", {"model": "distil-large-v3"}),
            ("large-v3-turbo+hotwords", {"model": "large-v3-turbo", "hotwords": True})]
MODEL_DIRS = {"small.en": "faster-whisper-small.en", "medium.en": "faster-whisper-medium.en",
              "large-v3-turbo": "faster-whisper-large-v3-turbo", "distil-large-v3": "faster-distil-whisper-large-v3"}


class VramPeak:
    """Polls nvidia-smi while a block runs: (MiB used before, peak MiB used)."""

    def __enter__(self):
        import threading

        self.before = self.peak = _vram()
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._poll, daemon=True)
        self._t.start()
        return self

    def _poll(self):
        while not self._stop.wait(0.2):
            self.peak = max(self.peak, _vram())

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()


def _vram() -> int:
    import subprocess

    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True)
    return int(out.stdout.strip().splitlines()[0])


VARIANTS_D = dict(VARIANTS)


def coresident(root: Path, rows: list[dict], lex, models: set[str]) -> dict:
    """Load Qwen first, then each ASR model, transcribe a few clips: does the pair fit on the 8 GB card?"""
    from jatayu.asr import Transcriber
    from jatayu.audio import decode_to_16k
    from jatayu.llm import LlmRunner

    llm = LlmRunner(config.LLM_MODEL_PATH)
    llm.complete_json("Reply with JSON.", "ok", {"type": "object", "properties": {"ok": {"type": "boolean"}}})
    out = {}
    for name in sorted(models):
        asr = Transcriber(model_dir=config.MODELS_DIR / "asr" / MODEL_DIRS[name], lexicon=lex, word_confidence=False)
        try:
            with VramPeak() as v:
                for r in rows:
                    asr.transcribe(decode_to_16k((root / "audio" / "tts" / r["path"]).read_bytes())[0])
            out[name] = {"vram_peak_mib": v.peak, "fits": v.peak < 8151 and asr.device == "cuda", "device": asr.device}
        except Exception as exc:
            out[name] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
        asr.unload()
    llm.close()
    return out


def subset(root: Path, n: int, seed: int) -> list[dict]:
    rows = _audio_rows(root, "dev", "audio")
    return sorted(random.Random(seed).sample(rows, n), key=lambda r: r["path"])


def resample_check(root: Path, rows: list[dict]) -> dict:
    from jatayu.audio import decode_to_16k

    files, decoded, mismatch = defaultdict(int), defaultdict(int), 0
    for r in rows:
        p = root / "audio" / "tts" / r["path"]
        with wave.open(str(p)) as w:
            files[f"{w.getframerate()} Hz, {w.getnchannels()} ch, {8 * w.getsampwidth()} bit"] += 1
            frames, rate = w.getnframes(), w.getframerate()
        samples, _ = decode_to_16k(p.read_bytes())
        decoded[f"{samples.ndim}-D float32"] += 1
        mismatch += abs(len(samples) / 16000 - frames / rate) > 0.01
    return {"file_format": dict(files), "decoded_to_whisper": dict(decoded), "sample_rate_given_to_whisper": 16000,
            "clips_with_duration_mismatch_over_10ms": mismatch}


def evaluate(root: Path, rows: list[dict], cfg: dict, lex, rules, by_id) -> tuple[dict, list[dict]]:
    from jatayu.asr import Transcriber
    from jatayu.audio import decode_to_16k
    from jatayu.validate import validate_all

    asr = Transcriber(model_dir=config.MODELS_DIR / "asr" / MODEL_DIRS[cfg["model"]], lexicon=lex,
                      beam_size=cfg["beam"], vad_filter=cfg["vad"], use_prompt=cfg["prompt"],
                      prompt_aliases=cfg["aliases"], hotwords=cfg["hotwords"], word_confidence=False)
    vram = VramPeak().__enter__()
    t_load = time.perf_counter()
    asr._load()
    load_s = time.perf_counter() - t_load
    scorer = Scorer()
    by_group = defaultdict(lambda: {"err": 0, "words": 0, "hits": 0, "den": 0})
    raw = [0, 0]
    norm = [0, 0]
    voice = defaultdict(lambda: [0, 0])
    drug = {"hits": 0, "den": 0, "hits_surface": 0, "den_surface": 0}
    out, lat = [], []
    for r in rows:
        u = by_id[r["utt_id"]]
        samples, _ = decode_to_16k((root / "audio" / "tts" / r["path"]).read_bytes())
        t0 = time.perf_counter()
        hyp = asr.transcribe(samples).text
        lat.append(time.perf_counter() - t0)
        for acc, (a, b) in ((raw, (_norm_text(u.text), _norm_text(hyp))), (norm, (asr_norm(u.text, lex), asr_norm(hyp, lex)))):
            e, n = word_errors(a, b)
            acc[0] += e
            acc[1] += n
        e, n = word_errors(asr_norm(u.text, lex), asr_norm(hyp, lex))
        voice[r["voice"]][0] += e
        voice[r["voice"]][1] += n
        grp = by_group["Indian-accented (L2-ARCTIC/VCTK)" if r["accent"] == "in" else "US/GB"]
        grp["err"] += e
        grp["words"] += n
        ref_drugs, hyp_drugs = drugs_heard(u.text, lex), drugs_heard(hyp, lex)
        for g in u.entries:
            if g.drug is None:
                continue
            drug["den_surface"] += 1
            drug["hits_surface"] += g.drug.surface.lower() in hyp.lower()
            if g.drug.value in ref_drugs:  # denominator: drug names the lexicon recognises in the reference
                drug["den"] += 1
                drug["hits"] += g.drug.value in hyp_drugs
                grp["den"] += 1
                grp["hits"] += g.drug.value in hyp_drugs
        cap = datetime.fromisoformat(u.capture_time)
        scorer.add(u, validate_all(rules.extract(hyp, cap), lex, []))
        out.append({"utt_id": u.id, "voice": r["voice"], "reference": u.text, "transcript": hyp})
    vram.__exit__(None, None, None)
    dropped = asr.prompt_and_dropped()[1] if cfg["prompt"] else []
    asr.unload()
    m = scorer.metrics()
    return {"config": cfg, "wer_raw": round(raw[0] / raw[1], 4), "wer_normalised": round(norm[0] / norm[1], 4),
            "drug_term_recall": round(drug["hits"] / max(drug["den"], 1), 4), "drug_term_recall_den": drug["den"],
            "drug_term_recall_surface": round(drug["hits_surface"] / max(drug["den_surface"], 1), 4),
            "entity_f1_rules": m["entity"]["micro"]["f1"],
            "per_field_f1_rules": {f: v["f1"] for f, v in m["entity"]["per_field"].items() if v["gold"]},
            "wer_normalised_by_voice": {v: round(a / b, 4) for v, (a, b) in sorted(voice.items())},
            "by_accent_group": {k: {"wer_normalised": round(g["err"] / max(g["words"], 1), 4),
                                    "drug_term_recall": round(g["hits"] / max(g["den"], 1), 4), "drug_den": g["den"]}
                                for k, g in sorted(by_group.items())},
            "latency_mean_s": round(sum(lat) / len(lat), 3), "load_s": round(load_s, 2),
            "vram_before_mib": vram.before, "vram_peak_mib": vram.peak, "vram_added_mib": vram.peak - vram.before,
            "prompt_names_dropped": len(dropped),
            "hotword_tokens": asr._count_tokens(asr.hotword_text) if cfg["hotwords"] else 0}, out


def report(o: dict) -> str:
    L = [f"# ASR diagnosis `{o['tag']}` (dev, {o['n_clips']} clips, seed {o['seed']}, commit `{o['commit']}`)", "",
         "Synthetic speech (Piper). Extraction = rules extractor on the transcript (deterministic), so differences "
         "between rows come from the ASR setting alone. One setting changed per row against the baseline "
         f"({o['baseline']}).", "",
         "| Setting | WER raw | WER normalised | Drug-term recall | Entity F1 (rules) | s/clip |", "|---|---|---|---|---|---|"]
    for name, r in o["rows"].items():
        L.append(f"| {name} | {r['wer_raw']:.3f} | {r['wer_normalised']:.3f} | {r['drug_term_recall']:.3f} "
                 f"(n={r['drug_term_recall_den']}) | {r['entity_f1_rules']:.3f} | {r['latency_mean_s']} |")
    L += ["", "## By accent group (normalised WER / drug-term recall)", "",
          "| Setting | US/GB WER | US/GB recall | Indian-accented WER | Indian-accented recall |", "|---|---|---|---|---|"]
    for name, r in o["rows"].items():
        g = r.get("by_accent_group", {})
        us, ind = g.get("US/GB", {}), g.get("Indian-accented (L2-ARCTIC/VCTK)", {})
        L.append(f"| {name} | {us.get('wer_normalised', 0):.3f} | {us.get('drug_term_recall', 0):.3f} (n={us.get('drug_den', 0)}) | "
                 f"{ind.get('wer_normalised', 0):.3f} | {ind.get('drug_term_recall', 0):.3f} (n={ind.get('drug_den', 0)}) |")
    L += ["", "## Cost (ASR alone; VRAM from nvidia-smi, includes the Windows desktop's share)", "",
          "| Setting | load s | s/clip | VRAM before | VRAM peak | added | prompt names dropped | hotword tokens |",
          "|---|---|---|---|---|---|---|---|"]
    for name, r in o["rows"].items():
        if "load_s" in r:
            L.append(f"| {name} | {r['load_s']} | {r['latency_mean_s']} | {r['vram_before_mib']} | {r['vram_peak_mib']} | "
                     f"{r['vram_added_mib']} | {r['prompt_names_dropped']} | {r['hotword_tokens']} |")
    if o.get("coresident"):
        L += ["", "## With Qwen3-4B loaded first (co-resident, as the hybrid runs)", "",
              "| Model | VRAM peak MiB | fits in 8151 MiB |", "|---|---|---|"]
        L += [f"| {k} | {v.get('vram_peak_mib', '—')} | {v.get('fits', v.get('error'))} |" for k, v in o["coresident"].items()]
    b = o["rows"]["baseline"]
    L += ["", "WER raw = lowercase, punctuation stripped (the definition used in round 2). WER normalised = the "
          "pipeline's number normaliser + unit/route words mapped to lexicon codes, on reference AND hypothesis.",
          "Drug-term recall = gold drugs whose name the lexicon recognises in the reference and that also appear "
          f"in the transcript; the round-2 surface-string recall on the baseline is {b['drug_term_recall_surface']:.3f}.",
          "", "## Per field, baseline (entity F1, rules extractor)", "", "| Field | F1 |", "|---|---|"]
    L += [f"| {f} | {v:.3f} |" for f, v in b["per_field_f1_rules"].items()]
    L += ["", "## Normalised WER by voice", "", "| Voice | " + " | ".join(o["rows"]) + " |",
          "|---|" + "---|" * len(o["rows"])]
    for v in b["wer_normalised_by_voice"]:
        L.append(f"| {v} | " + " | ".join(f"{r['wer_normalised_by_voice'].get(v, 0):.3f}" for r in o["rows"].values()) + " |")
    L += ["", "## Audio reaching Whisper", ""] + [f"- {k}: {v}" for k, v in o["resample"].items()]
    L += ["", "## 10 random (reference, transcript) pairs, baseline", ""]
    for p in o["pairs"]:
        L += [f"- `{p['utt_id']}` ({p['voice']})  ", f"  REF: {p['reference']}  ", f"  ASR: {p['transcript']}"]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--variants", default="baseline,vad off,prompt off,beam 1,beam 10,medium.en")
    ap.add_argument("--coresident", action="store_true", help="also measure VRAM with the LLM loaded first")
    ap.add_argument("--root", type=Path, default=config.DATA_DIR)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from jatayu.extract.rules import RulesExtractor
    from jatayu.lexicon import Lexicon

    start = log_run(args.out, runner="eval.asr_diag", split="dev", tag=args.tag, n=args.n, seed=args.seed)
    lex = Lexicon.load()
    rules = RulesExtractor(lex)
    by_id = {u.id: u for u in load_split("dev", root=args.root)}
    rows = subset(args.root, args.n, args.seed)
    o = {"tag": args.tag, "n_clips": len(rows), "seed": args.seed, "commit": start["commit"], "baseline": BASE,
         "resample": resample_check(args.root, rows), "rows": {}}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    wanted = args.variants.split(",")
    for name, change in VARIANTS:
        if name not in wanted:
            continue
        o["rows"][name], transcripts = evaluate(args.root, rows, {**BASE, **change}, lex, rules, by_id)
        print(name, {k: o["rows"][name][k] for k in ("wer_raw", "wer_normalised", "drug_term_recall", "entity_f1_rules")},
              flush=True)
        (out / f"transcripts-{name.replace(' ', '_')}.jsonl").write_text(
            "".join(json.dumps(t) + "\n" for t in transcripts), encoding="utf-8")
        if name == "baseline":
            o["pairs"] = random.Random(args.seed + 1).sample(transcripts, 10)
    if args.coresident:
        o["coresident"] = coresident(args.root, rows[:10], lex, {VARIANTS_D[n]["model"] if "model" in VARIANTS_D[n] else BASE["model"]
                                                                  for n in wanted if n in VARIANTS_D})
    (out / "metrics.json").write_text(json.dumps(o, indent=2) + "\n", encoding="utf-8")
    (out / "report.md").write_text(report(o), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
