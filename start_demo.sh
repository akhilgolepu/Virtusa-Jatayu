#!/usr/bin/env bash
# Scribe108 demo, one command: pre-flight checks (fail loudly), then the server on 127.0.0.1, then the browser.
#   ./start_demo.sh               start the demo
#   ./start_demo.sh --check-only  pre-flight only
# Decision-support demo, not a clinical device.
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${CONDA_DEFAULT_ENV:-}" != "anpr" ]]; then
  eval "$(conda shell.bash hook)"
  conda activate anpr
fi
source scripts/env.sh
exec python -m scripts.start_demo "$@"
