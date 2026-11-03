# m3-seeded-test-seed2027-HARDER-RESCORE

Evaluator round 2, step 2: validator-only re-score of the original seeded run on the **same records and corruptions**
(same seed, same pool, same random stream), adding the **new-flag** catch definition: a corruption counts only if the
corrupted record gets a catching flag its uncorrupted base did not have. The existing definition is reproduced
exactly (FIRST-RUN 163, TUNED 197, FRESH 189, HARDER 139 of 200), which checks the re-score.
Validator: frozen, unchanged since 97fa1c6 (the validator that produced the original run).
Logged in results/run_log.jsonl. Data: the pre-regeneration splits (superseded by evaluator round 2, step 3).
