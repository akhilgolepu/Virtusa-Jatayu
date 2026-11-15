"""python -m scripts.readback_test_server [--port 8010] [--store data/readback_test]

Serves the read-back test harness (jatayu/readback_trial.py) at http://localhost:<port>/readback-test, on its own port
and with its own store: the demo app and its database are not involved. Bind 127.0.0.1 only. Testers use anonymous
codes (T01, T02, ...); the answer key stays in <store>/sessions/ on this machine. Aggregate the answers with
python -m eval.readback_test_report --tag <tag>."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jatayu import config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8010)
    ap.add_argument("--store", type=Path, default=config.DATA_DIR / "readback_test")
    args = ap.parse_args(argv)
    import uvicorn

    from jatayu.readback_trial import create_readback_app

    uvicorn.run(create_readback_app(args.store), host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
