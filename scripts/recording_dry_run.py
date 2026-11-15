"""python -m scripts.recording_dry_run --tag r6-recording-dry-run

Dry run of the real-recording path with a DUMMY clip, in a throwaway folder (data/real is never touched):
  1. the app's /record page and prompt list load (real prompts: counts only, no text);
  2. a dummy clip is uploaded through the recording API for one dummy DEV prompt (transcribed, checked) and one dummy
     TEST prompt (must be saved sealed: not transcribed, no WER);
  3. `python -m scripts.import_real --from-recordings` (the real command) imports both into <tmp>/real/{dev,test};
  4. load_real("dev") returns the clip; load_real("test") must refuse (sealed); a re-import adds nothing.
No real recording exists or is read; no transcript of a real clip is produced."""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tempfile
import wave
from collections import Counter
from pathlib import Path

import numpy as np

from eval.runlog import log_run
from jatayu import config


def dummy_wav(seconds: float = 2.0, rate: int = 22050) -> bytes:
    t = np.arange(int(seconds * rate)) / rate
    pcm = (0.2 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm.tobytes())  # noqa: E702
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from fastapi.testclient import TestClient

    from jatayu.api import create_app
    from scripts.import_real import load_real

    start = log_run(args.out, runner="scripts.recording_dry_run", split="none (dummy clip)", tag=args.tag)
    checks: dict[str, object] = {}

    # 1. the real page and prompt list (counts only)
    real = TestClient(create_app())
    page = real.get("/record")
    checks["record_page_status"] = page.status_code
    prompts = real.get("/api/corpus/prompts?status=all").json()
    checks["real_prompts_by_split"] = dict(Counter(p.get("split", "?") for p in prompts)) if prompts and "split" in prompts[0] else len(prompts)
    checks["real_prompt_status_counts"] = dict(Counter(p["status"] for p in prompts))

    # 2. dummy prompts + upload through the recording API
    tmp = Path(tempfile.mkdtemp())
    rec = tmp / "recordings"
    rec.mkdir()
    dummy = [{"prompt_id": "dry-dev", "split": "dev", "text": "gave 4 mg ondansetron IV", "entries": []},
             {"prompt_id": "dry-test", "split": "test", "text": "gave 2 mg morphine IV", "entries": []}]
    (rec / "prompts.jsonl").write_text("".join(json.dumps(p) + "\n" for p in dummy))
    app = TestClient(create_app(db_path=tmp / "j.sqlite", audio_dir=tmp / "audio", recordings_dir=rec))
    for p in dummy:
        row = app.post("/api/corpus/recordings", data={"prompt_id": p["prompt_id"], "condition": "quiet"},
                       files={"audio": ("dummy.wav", dummy_wav(), "audio/wav")}).json()
        checks[f"upload_{p['split']}"] = {"status": row.get("status"), "transcribed": row.get("asr_text") is not None,
                                           "wer_reported": row.get("wer") is not None}

    # 3. the real import command
    cmd = [sys.executable, "-m", "scripts.import_real", "--from-recordings", "--speaker", "DRY01", "--root", str(tmp)]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=config.ROOT)
    checks["import_command"] = " ".join(cmd[1:]).replace(str(tmp), "<tmp>")
    checks["import_output"] = out.stdout.strip() or out.stderr.strip()[-300:]
    again = subprocess.run(cmd, capture_output=True, text=True, cwd=config.ROOT)
    checks["reimport_output"] = again.stdout.strip()

    # 4. sealing
    checks["load_real_dev_clips"] = len(load_real("dev", tmp))
    try:
        load_real("test", tmp)
        checks["load_real_test"] = "NOT SEALED (returned clips)"
    except PermissionError as exc:
        checks["load_real_test"] = f"refused: {exc}"
    checks["real_data_dir_untouched"] = not (config.DATA_DIR / "real").exists()

    ok = (checks["record_page_status"] == 200 and checks["upload_test"]["status"] == "sealed"
          and not checks["upload_test"]["transcribed"] and checks["upload_dev"]["transcribed"]
          and checks["load_real_dev_clips"] == 1 and str(checks["load_real_test"]).startswith("refused")
          and "0 dev and 0 test" in checks["reimport_output"])
    checks["all_ok"] = ok
    o = args.out / args.tag
    o.mkdir(parents=True, exist_ok=True)
    (o / "metrics.json").write_text(json.dumps({"commit": start["commit"], **checks}, indent=2) + "\n")
    L = [f"# Real-recording dry run (`{args.tag}`, commit `{start['commit']}`)", "",
         "Dummy 2-second tone, throwaway folder; `data/real/` not touched; no real clip exists or was read.", "",
         "| Check | Result |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in checks.items()]
    (o / "report.md").write_text("\n".join(L) + "\n")
    print(json.dumps(checks, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
