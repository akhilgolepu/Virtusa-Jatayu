# Runs made while `f2r eval` ignored its options

The first M3 batch (`scripts/run_m3_evals.sh`, before commit 263fc6b "fix(cli): f2r eval/setup-check pass their
options through") failed on its **first** command: argparse rejected `--split` (`f2r: error: unrecognized arguments`)
and the script, running with `set -e`, exited with code 2. **It wrote no results/<tag>/ folder.**
Its log file (results/m3-evals.log) was deleted when the batch was re-run; this note replaces it.

No invalid results folders exist. Every folder present was written after 263fc6b; folders superseded for other
reasons are marked `_SUPERSEDED` with a NOTE.md.
