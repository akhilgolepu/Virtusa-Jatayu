"""python -m scripts.start_demo [--check-only] [--no-browser] [--port 8000] [--out results/<tag>/preflight.json]
(or ./start_demo.sh, which activates the anpr env and the CUDA library path first)

One command for the demo: a PRE-FLIGHT that fails loudly, then the server, then the browser.
Pre-flight (every item must pass; any FAIL prints in capitals and exits 1 without starting anything):
  gpu      nvidia-smi answers, torch sees CUDA, CTranslate2 (Whisper) sees a CUDA device
  models   the Whisper model, the LLM file (hybrid), the read-back voice, the lexicon, the word list, the built UI
  config   default extractor on the demo path (rules or hybrid), LLM-only experimental switch OFF, ASR device cuda
  offline  HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE are 1, and the ASR + voice checks below run with outbound sockets blocked
  asr      Whisper loads on the GPU and transcribes the fixture clip ("adrenaline") — network blocked
  voice    the read-back voice speaks a test sentence — network blocked
  audit    the demo database's hash chain verifies (if the database exists)
  port     the port is free on 127.0.0.1
The server binds to 127.0.0.1 only. The LLM itself is not loaded here (it loads on the first hybrid utterance); its file
is checked, and scripts/setup_check.py remains the full G0 check that also runs it."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from jatayu import config

FIXTURE = config.ROOT / "tests/fixtures/adrenaline.wav"
RED, GREEN, RESET = "\033[1;31m", "\033[32m", "\033[0m"


@contextmanager
def no_network():
    real = socket.socket.connect

    def guard(self, addr):
        if self.family == socket.AF_UNIX or (isinstance(addr, tuple) and addr[0] in ("127.0.0.1", "localhost", "::1")):
            return real(self, addr)
        raise OSError("network blocked by the demo pre-flight")

    socket.socket.connect = guard
    try:
        yield
    finally:
        socket.socket.connect = real


def check_gpu() -> dict:
    if shutil.which("nvidia-smi") is None:
        return {"pass": False, "detail": "nvidia-smi not found: no NVIDIA driver visible"}
    smi = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=20)
    if smi.returncode != 0:
        return {"pass": False, "detail": f"nvidia-smi failed: {smi.stderr.strip()[:200]}"}
    import ctranslate2
    import torch

    name, total, used = [x.strip() for x in smi.stdout.strip().splitlines()[0].split(",")]
    ok = torch.cuda.is_available() and ctranslate2.get_cuda_device_count() > 0
    return {"pass": ok, "detail": f"{name}, {used}/{total} MiB used; torch CUDA {torch.cuda.is_available()}, "
                                  f"CTranslate2 CUDA devices {ctranslate2.get_cuda_device_count()}"}


def check_models() -> dict:
    need = {"whisper": config.ASR_MODEL_DIR / "model.bin", "llm (hybrid)": config.LLM_MODEL_PATH,
            "read-back voice": config.READBACK_VOICE, "voice config": Path(str(config.READBACK_VOICE) + ".json"),
            "word list": config.ROOT / "jatayu/lexicon/common_words.txt",
            "built UI": config.ROOT / "jatayu/web/dist/index.html", "fixture clip": FIXTURE}
    missing = [k for k, p in need.items() if not p.exists() or p.stat().st_size == 0]
    from jatayu.lexicon import Lexicon

    n = len(Lexicon.load().drug_names())
    return {"pass": not missing and n > 0, "detail": f"missing: {', '.join(missing)}" if missing else
            f"all present; lexicon {n} drugs", "files": {k: str(p.relative_to(config.ROOT)) for k, p in need.items()}}


def check_config() -> dict:
    problems = []
    if config.DEFAULT_EXTRACTOR not in config.DEMO_EXTRACTORS:
        problems.append(f"default extractor {config.DEFAULT_EXTRACTOR!r} is not on the demo path {config.DEMO_EXTRACTORS}")
    if config.EXPERIMENTAL:
        problems.append("JATAYU_EXPERIMENTAL=1: LLM-only would be offered; unset it for the demo")
    if config.ASR_DEVICE != "cuda":
        problems.append(f"JATAYU_ASR_DEVICE={config.ASR_DEVICE!r}, expected cuda")
    return {"pass": not problems, "detail": "; ".join(problems) or
            f"extractor {config.DEFAULT_EXTRACTOR}, LLM-only off, ASR {config.ASR_DEVICE}/{config.ASR_COMPUTE_TYPE}"}


def check_offline_env() -> dict:
    bad = [k for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE") if os.environ.get(k) != "1"]
    return {"pass": not bad, "detail": f"not set to 1: {', '.join(bad)}" if bad else
            "HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1; ASR and voice checks run with outbound sockets blocked"}


def check_asr() -> dict:
    from jatayu.asr import Transcriber
    from jatayu.audio import decode_to_16k

    samples, _ = decode_to_16k(FIXTURE.read_bytes())
    t0 = time.perf_counter()
    res = Transcriber().transcribe(samples)
    ok = "adrenaline" in res.text.lower() and res.device == "cuda"
    return {"pass": ok, "detail": f"{res.device}: “{res.text.strip()}” ({time.perf_counter() - t0:.1f} s incl. load)"}


def check_voice() -> dict:
    import io
    import wave

    from jatayu.readback import synthesize_readback

    with wave.open(io.BytesIO(synthesize_readback("Epinephrine, zero point three milligrams. Confirm?"))) as w:
        seconds = w.getnframes() / w.getframerate()
    return {"pass": seconds > 1.0, "detail": f"{seconds:.1f} s of speech from {config.READBACK_VOICE.name}"}


def check_audit() -> dict:
    if not config.DB_PATH.exists():
        return {"pass": True, "detail": "no demo database yet (a new one is created)"}
    from jatayu.audit import AuditLog

    v = AuditLog(config.DB_PATH).verify()
    return {"pass": v.ok, "detail": f"chain verified, {v.checked} rows" if v.ok else
            f"CHAIN BROKEN at seq {v.first_bad_seq}: {v.reason}"}


def check_port(port: int) -> dict:
    with socket.socket() as s:
        free = s.connect_ex(("127.0.0.1", port)) != 0
    return {"pass": free, "detail": f"127.0.0.1:{port} free" if free else f"something already listens on 127.0.0.1:{port}"}


def preflight(port: int) -> dict:
    results = {}
    plan = [("gpu", check_gpu), ("models", check_models), ("config", check_config), ("offline", check_offline_env),
            ("asr", check_asr), ("voice", check_voice), ("audit", check_audit), ("port", lambda: check_port(port))]
    for name, fn in plan:
        try:
            if name in ("asr", "voice"):
                with no_network():
                    results[name] = fn()
            else:
                results[name] = fn()
        except Exception as exc:  # a crash is a FAIL with its reason
            results[name] = {"pass": False, "detail": f"{type(exc).__name__}: {exc}"}
        r = results[name]
        print(f"{GREEN}PASS{RESET}  {name:8s} {r['detail']}" if r["pass"] else
              f"{RED}FAIL  {name.upper():8s} {r['detail']}{RESET}", flush=True)
    return results


def open_browser(url: str) -> None:
    """Windows browser from WSL (wslview / explorer.exe), else the Python default."""
    for cmd in (["wslview", url], ["explorer.exe", url], ["xdg-open", url]):
        if shutil.which(cmd[0]):
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    import webbrowser

    webbrowser.open(url)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--check-only", action="store_true", help="run the pre-flight only")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--out", type=Path, help="write the pre-flight result as JSON")
    args = ap.parse_args(argv)
    print(f"Scribe108 demo pre-flight — {config.DISCLAIMER}", flush=True)
    results = preflight(args.port)
    ok = all(r["pass"] for r in results.values())
    if args.out:
        from eval.runlog import commit

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"created": datetime.now().astimezone().isoformat(), "commit": commit(),
                                        "all_pass": ok, "checks": results}, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print(f"{RED}PRE-FLIGHT FAILED: {', '.join(k for k, r in results.items() if not r['pass'])}. "
              f"The demo was NOT started.{RESET}", flush=True)
        return 1
    print(f"{GREEN}Pre-flight passed.{RESET}", flush=True)
    if args.check_only:
        return 0
    url = f"http://localhost:{args.port}"
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "jatayu.api:app", "--host", "127.0.0.1",
                               "--port", str(args.port)], cwd=config.ROOT)
    try:
        for _ in range(120):  # the app imports the model stack: allow up to a minute
            if server.poll() is not None:
                print(f"{RED}SERVER EXITED (code {server.returncode}){RESET}", flush=True)
                return 1
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/health", timeout=1) as r:
                    if json.load(r).get("ok"):
                        break
            except OSError:
                time.sleep(0.5)
        else:
            print(f"{RED}SERVER DID NOT ANSWER /api/health{RESET}", flush=True)
            server.terminate()
            return 1
        print(f"Demo running at {url} (Ctrl-C to stop)", flush=True)
        if not args.no_browser:
            open_browser(url)
        return server.wait()
    except KeyboardInterrupt:
        server.terminate()
        server.wait(timeout=10)
        return 0


if __name__ == "__main__":
    sys.exit(main())
