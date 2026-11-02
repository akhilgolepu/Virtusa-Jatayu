# NOTE — protocol slip, disclosed

This audit was meant for dev only (step 4: "do not measure it on test yet"), but `eval.gold_dose_audit` reads dev,
test and final_test, so it also computed the step-4 validator's flags on the **test and final_test gold labels**
(aggregate counts only; no records printed). Logged in results/run_log.jsonl. The counts are identical to
m3-gold-dose-audit-POST-regeneration (test 1, final_test 2 in-range gold doses flagged), and the validator was not
changed after this run (it was frozen on the dev seeded results above).
