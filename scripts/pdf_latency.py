"""python -m scripts.pdf_latency --tag r7-pdf-latency [--runs 30]

Time to produce the PDF note (GET /api/incidents/<id>/note.pdf: validated FHIR-lite bundle + audit-chain check +
render) for a 10-entry and a 50-entry synthetic incident, through the API in-process. Raw timings in timings.csv."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import tempfile
import time
from pathlib import Path

from eval.runlog import log_run
from jatayu import config

SENTENCES = ["gave 0.3 mg adrenaline IM", "pushed 4 mg ondansetron IV", "aspirin 300 mg PO at 10 40",
             "fentanyl 50 mcg IN", "started CPR", "morphine 5 mg IV", "patient allergic to morphine",
             "salbutamol 5 mg neb", "naloxone 0.4 mg IV", "12 lead ecg done"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from fastapi.testclient import TestClient

    from jatayu.api import create_app

    start = log_run(args.out, runner="scripts.pdf_latency", split="none (synthetic incidents)", tag=args.tag, runs=args.runs)
    tmp = Path(tempfile.mkdtemp())
    c = TestClient(create_app(db_path=tmp / "j.sqlite", audio_dir=tmp / "a", recordings_dir=tmp / "r"))
    rows, summary = [], {}
    for n in (10, 50):
        inc = c.post("/api/incidents", json={"label": f"pdf {n}"}).json()["id"]
        for i in range(n):
            c.post("/api/utterances", data={"incident_id": inc, "text": SENTENCES[i % len(SENTENCES)]})
        times, size = [], 0
        for run in range(args.runs + 1):  # run 0 = warm-up
            t0 = time.perf_counter()
            r = c.get(f"/api/incidents/{inc}/note.pdf")
            dt = time.perf_counter() - t0
            r.raise_for_status()
            size = len(r.content)
            rows.append({"entries": n, "run": run, "warmup": run == 0, "seconds": round(dt, 5), "bytes": size})
            if run:
                times.append(dt)
        s = sorted(times)
        summary[str(n)] = {"p50_ms": round(statistics.median(s) * 1000, 1),
                           "p95_ms": round(s[max(0, math.ceil(0.95 * len(s)) - 1)] * 1000, 1),
                           "max_ms": round(s[-1] * 1000, 1), "pdf_kb": round(size / 1024, 1), "runs": len(s)}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "timings.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "summary": summary}, indent=2) + "\n")
    L = [f"# PDF note generation time (`{args.tag}`, commit `{start['commit']}`)", "",
         f"GET note.pdf through the API in-process (bundle build + schema validation + audit-chain verify + render), "
         f"{args.runs} timed runs after one warm-up. Synthetic incidents. Raw: `timings.csv`.", "",
         "| Entries | p50 | p95 | max | PDF size |", "|---|---|---|---|---|"]
    L += [f"| {n} | {v['p50_ms']} ms | {v['p95_ms']} ms | {v['max_ms']} ms | {v['pdf_kb']} KB |" for n, v in summary.items()]
    (out / "report.md").write_text("\n".join(L) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
