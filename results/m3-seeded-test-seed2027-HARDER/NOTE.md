# Aggregate-only test result

Run once on test records with the validator frozen (see results/run_log.jsonl). The report was re-rendered from this
run's own files (`python -m eval.seeded_errors --rerender`, no re-evaluation) to add Wilson 95 % intervals and the
aggregate miss / false-flag breakdowns, and the per-record files (errors.jsonl, false_flags.jsonl) were removed so no
individual test record is exposed. Those files still exist in the local, unpushed commit 0f1b65e; history has not
been rewritten.
