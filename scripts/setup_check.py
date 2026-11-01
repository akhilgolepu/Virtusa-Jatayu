"""Gate G0 setup check: proves the stack runs on this machine, offline, and records measured numbers.

Usage: python -m scripts.setup_check [--out results/g0/setup_check.json]
Prints PASS/FAIL per item, writes the JSON, exits 1 if any check fails. Every number in the JSON is measured here.
"""
from __future__ import annotations

import argparse
import io
import json
import platform
import socket
import subprocess
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

from jatayu import config

FIXTURE = config.ROOT / "tests/fixtures/adrenaline.wav"


def _nvidia_smi() -> dict:
    q = "name,driver_version,memory.total,memory.used"
    out = subprocess.run(["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=20)
    name, driver, total, used = [x.strip() for x in out.stdout.strip().split(",")]
    cuda = subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout
    cuda_ver = cuda.split("CUDA Version:")[1].split()[0] if "CUDA Version:" in cuda else "unknown"
    return {"name": name, "driver": driver, "cuda": cuda_ver, "vram_total_mib": int(total), "vram_used_mib": int(used)}


def _vram_used() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True)
    return int(out.stdout.strip())


def check_gpu() -> dict:
    info = _nvidia_smi()
    import torch

    return {"pass": torch.cuda.is_available(), "detail": f"{info['name']} driver {info['driver']}", **info,
            "torch": torch.__version__, "torch_cuda": torch.version.cuda}


def check_asr() -> dict:
    from jatayu.asr import Transcriber
    from jatayu.audio import decode_to_16k

    samples, _ = decode_to_16k(FIXTURE.read_bytes())
    t = Transcriber()
    t0 = time.perf_counter()
    first = t.transcribe(samples)
    load_and_first = time.perf_counter() - t0
    warm = [t.transcribe(samples).latency_s for _ in range(3)]
    ok = "adrenaline" in first.text.lower()
    return {"pass": ok, "detail": first.text, "device": first.device, "model": config.ASR_MODEL_DIR.name,
            "load_plus_first_s": round(load_and_first, 3), "latency_s": round(sorted(warm)[1], 3),
            "audio_s": round(first.duration_s, 2)}


def check_llm() -> dict:
    from jatayu.llm import LlmRunner

    before = _vram_used()
    r = LlmRunner(config.LLM_MODEL_PATH)
    t0 = time.perf_counter()
    llm = r._load()
    load_s = time.perf_counter() - t0
    schema = {"type": "object", "properties": {"entries": {"type": "array", "items": {"type": "object", "properties": {
        "drug": {"type": "string"}, "dose": {"type": "string"}, "unit": {"type": "string"}, "route": {"type": "string"},
        "time": {"type": "string"}}, "required": ["drug", "dose", "unit", "route", "time"]}}}, "required": ["entries"]}
    msgs = [{"role": "system", "content": "Extract every medication as JSON, quoting the transcript exactly."},
            {"role": "user", "content": "Transcript: gave 0.3 mg adrenaline IM two minutes ago, then 4 mg ondansetron "
                                        "IV at 10 42 and 300 mg aspirin by mouth just now"}]
    t0 = time.perf_counter()
    out = llm.create_chat_completion(messages=msgs, temperature=0, max_tokens=160,
                                     response_format={"type": "json_object", "schema": schema})
    gen_s = time.perf_counter() - t0
    peak = _vram_used()
    parsed = json.loads(out["choices"][0]["message"]["content"])
    tokens = out["usage"]["completion_tokens"]
    r.close()
    return {"pass": len(parsed.get("entries", [])) >= 2, "detail": f"{len(parsed['entries'])} entries",
            "model": config.LLM_MODEL_PATH.name, "load_s": round(load_s, 2), "gen_s": round(gen_s, 2),
            "tokens": tokens, "tokens_per_s": round(tokens / gen_s, 1), "peak_vram_mib": peak,
            "vram_added_mib": peak - before}


def check_tts() -> dict:
    from jatayu.readback import synthesize_readback

    t0 = time.perf_counter()
    wav = synthesize_readback("Epinephrine, zero point three milligrams, intramuscular, at 14:32. Confirm?")
    with wave.open(io.BytesIO(wav)) as w:
        seconds = w.getnframes() / w.getframerate()
    return {"pass": seconds > 1.0, "detail": f"{seconds:.1f} s of speech", "voice": config.READBACK_VOICE.name,
            "synth_s": round(time.perf_counter() - t0, 2)}


def check_offline() -> dict:
    """Re-run ASR + TTS with every non-local socket blocked: nothing may need the internet at run time."""
    real = socket.socket.connect

    def guard(self, addr):
        if self.family == socket.AF_UNIX:
            return real(self, addr)
        raise OSError("network blocked by setup_check")

    socket.socket.connect = guard
    try:
        asr, tts = check_asr(), check_tts()
        try:
            socket.create_connection(("1.1.1.1", 443), timeout=2)
            blocked = False
        except OSError:
            blocked = True
    finally:
        socket.socket.connect = real
    return {"pass": asr["pass"] and tts["pass"] and blocked, "sockets_blocked": blocked,
            "detail": "ASR and TTS re-run with outbound sockets blocked"}


CHECKS = {"gpu": check_gpu, "asr": check_asr, "llm": check_llm, "tts": check_tts, "offline": check_offline}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results/g0/setup_check.json")
    args = ap.parse_args(argv)
    results = {}
    for name, fn in CHECKS.items():
        try:
            results[name] = fn()
        except Exception as exc:  # a crash is a FAIL with its reason, never a missing key
            results[name] = {"pass": False, "detail": f"{type(exc).__name__}: {exc}"}
        print(f"{'PASS' if results[name]['pass'] else 'FAIL'}  {name:8s} {results[name]['detail']}")
    data = {"created": datetime.now().astimezone().isoformat(), "host": platform.platform(),
            "python": sys.version.split()[0], "all_pass": all(c["pass"] for c in results.values()), "checks": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0 if data["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
