"""python -m scripts.e2e_latency --tag r5-e2e-latency [--runs 30]

End-to-end latency: from the end of a 10-second dictation (the upload leaves the client) to the confirm-screen payload
(the JSON the capture screen renders), through a real HTTP server on localhost — decode, ASR on the GPU, extraction
(default extractor: rules), validation, FHIR-lite, audit append. One warm-up run (model load) is reported apart.
Not included: the browser's own audio encoding and the screen paint. Writes timings.csv (raw), metrics.json, report.md.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np

from eval.runlog import log_run
from jatayu import config

DICTATION = ("At ten forty gave adrenaline zero point three milligrams I M. Then ondansetron four milligrams I V, "
             "aspirin three hundred milligrams by mouth, and started a twelve lead E C G.")
SECONDS = 10.0


def dictation_wav() -> tuple[bytes, float]:
    """The dictation spoken by a Piper voice, padded with silence (or trimmed) to exactly 10 s at 16 kHz."""
    from datagen.tts import synthesize
    from datagen.voices import voice_by_id

    with wave.open(io.BytesIO(synthesize(voice_by_id("lessac"), DICTATION))) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    speech_s = len(pcm) / 16000
    if speech_s > SECONDS:
        raise ValueError(f"dictation is {speech_s:.1f} s of speech; shorten it to fit {SECONDS:.0f} s")
    n = int(SECONDS * 16000)
    pcm = np.concatenate([pcm, np.zeros(max(0, n - len(pcm)), dtype="<i2")])[:n]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm.tobytes())  # noqa: E702
    return buf.getvalue(), speech_s


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    return s[max(0, math.ceil(q * len(s)) - 1)]  # nearest rank


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    import httpx
    import uvicorn

    from jatayu.api import create_app

    start = log_run(args.out, runner="scripts.e2e_latency", split="none (synthetic dictation)", tag=args.tag,
                    runs=args.runs, extractor=config.DEFAULT_EXTRACTOR)
    wav, speech_s = dictation_wav()
    tmp = Path(tempfile.mkdtemp())
    app = create_app(db_path=tmp / "j.sqlite", audio_dir=tmp / "audio", recordings_dir=tmp / "rec")
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{port}"
    rows = []
    with httpx.Client(timeout=120) as c:
        inc = c.post(f"{base}/api/incidents", json={"label": "latency"}).json()["id"]
        for run in range(args.runs + 1):  # run 0 = warm-up (loads Whisper)
            t0 = time.perf_counter()
            r = c.post(f"{base}/api/utterances", data={"incident_id": inc},
                       files={"audio": ("dictation.wav", wav, "audio/wav")})
            payload = r.json()
            dt = time.perf_counter() - t0
            r.raise_for_status()
            rows.append({"run": run, "warmup": run == 0, "seconds": round(dt, 4),
                         "asr_latency_s": round(payload["asr"]["latency_s"], 4), "entries": len(payload["entries"]),
                         "transcript": payload["utterance"]["raw_transcript"]})
    server.should_exit = True
    timed = [r["seconds"] for r in rows if not r["warmup"]]
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "timings.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    m = {"commit": start["commit"], "gpu": gpu, "extractor": config.DEFAULT_EXTRACTOR, "asr_model": config.ASR_MODEL_DIR.name,
         "audio_s": SECONDS, "speech_s": round(speech_s, 2), "runs": len(timed), "warmup_s": rows[0]["seconds"],
         "p50_s": round(statistics.median(timed), 3), "p95_s": round(pct(timed, 0.95), 3),
         "mean_s": round(statistics.fmean(timed), 3), "min_s": min(timed), "max_s": max(timed),
         "asr_p50_s": round(statistics.median(r["asr_latency_s"] for r in rows if not r["warmup"]), 3),
         "entries_per_run": sorted({r["entries"] for r in rows})}
    (out / "metrics.json").write_text(json.dumps(m, indent=2) + "\n")
    L = [f"# End-to-end latency (`{args.tag}`, commit `{start['commit']}`)", "",
         f"{len(timed)} runs of a {SECONDS:.0f}-second dictation ({speech_s:.1f} s of Piper speech + silence), extractor "
         f"**{m['extractor']}**, ASR {m['asr_model']} on {gpu}. Timed from the moment the upload leaves the client to the "
         "parsed confirm-screen payload, through a real HTTP server on localhost.", "",
         "| p50 | p95 | mean | min | max | ASR part, p50 | warm-up run (model load) |", "|---|---|---|---|---|---|---|",
         f"| **{m['p50_s']} s** | **{m['p95_s']} s** | {m['mean_s']} s | {m['min_s']} s | {m['max_s']} s | "
         f"{m['asr_p50_s']} s | {m['warmup_s']} s |", "",
         "Not included: the browser's audio encoding and the screen paint. Raw timings: `timings.csv`.",
         f"Transcript of the last run: “{rows[-1]['transcript']}” ({rows[-1]['entries']} entries)."]
    (out / "report.md").write_text("\n".join(L) + "\n")
    print(json.dumps(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
