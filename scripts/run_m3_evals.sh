#!/usr/bin/env bash
# Reproduce the M3 evidence: ablation on dev (text), spoken dev, noise curve on dev, one test run.
# Usage: conda activate anpr && bash scripts/run_m3_evals.sh
set -euo pipefail
cd "$(dirname "$0")/.."
for x in rules hybrid llm; do
  python -m f2r.cli eval --split dev --tag "m3-dev-text-$x" --extractor "$x" --mode text
done
python -m f2r.cli eval --split dev --tag m3-dev-audio-hybrid --extractor hybrid --mode audio
python -m f2r.cli eval --split dev --tag m3-dev-noise-hybrid --extractor hybrid --mode noisy --limit 160
python -m f2r.cli eval --split test --tag m3-test-text-hybrid --extractor hybrid --mode text
