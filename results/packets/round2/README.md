# Evidence packet — evaluator round 2 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device). Every number below was written by the harness;
the files next to this README are copies of the harness output (aggregate only for test). Test and final_test
records are never printed or written.

Commits: `d0e7147` (steps 1-2) · `2002447` (step 3) · `69d1a38` (step 4) · `9b2c5c6` (step 5) · packets/reruns after.
Local, unpushed; `3214196` kept as is.

## 1. Dangerous-error definition

`weight_based_dose` no longer counts as a catch (strict = headline); `dangerous_error_lenient` is a secondary row in
every new `metrics.json` / `report.md`. Code: `eval/metrics.py` (`NON_CATCHING`, `NON_CATCHING_LENIENT`,
`is_dangerous`). Offline re-score of the six existing pipeline runs from their `errors.jsonl` (`eval/rescore.py`):
`rescored_dangerous.md`. The lenient count reproduces every recorded count; strict equals lenient on all six.

## 2. Seeded-error catch metric

New-flag definition: caught only if the corrupted record gets a catching flag its base did not have
(`eval/seeded_errors.py::caught`, tests in `tests/test_seeded_errors.py`). Re-scored on the same records, validator
frozen, each logged in `run_log.jsonl`:

| Run (pre-regeneration data) | Existing | New-flag | Base already flagged |
|---|---|---|---|
| dev seed 7, first run (a422cea validator) | 163/200 (81.5%) | 159/200 (79.5%; 73.4-84.5) | 19/200 |
| dev seed 7, tuned on this set | 197/200 (98.5%) | 193/200 (96.5%; 93.0-98.3) | 19/200 |
| test seed 2026, fresh | 189/200 (94.5%) | 186/200 (93.0%; 88.6-95.8) | 16/200 |
| test seed 2027, harder | 139/200 (69.5%) | 130/200 (65.0%; 58.2-71.3) | 15/200 |

Reports: `m3-seeded-*-RESCORE.report.md`.

## 3. Generator dose-table bug

Diagnosis (aggregate, gold labels only): `m3-gold-dose-audit-PRE-regeneration.report.md` — gold doses outside the
lexicon range: dev 51/357, test 48/288, final_test 23/170. After: `m3-gold-dose-audit-POST-regeneration.report.md` —
0 in every split. Generator: `datagen/doses.py` (lexicon ranges only; `datagen/doses.yaml` deleted); test
`tests/datagen/test_generate.py::test_every_gold_dose_is_inside_its_cited_range`. Regenerated after verifying in
`run_log.jsonl` that no pipeline evaluation ever ran on test or final_test. New hashes `frozen.sha256`; superseded
hashes `frozen.sha256.superseded`.

## 4. Weight-based drugs (dev only)

Validator: DERIVED sanity range = cited per-kg dose × 45-130 kg (CDC NHANES 2015-2018 percentiles) for per-kg rows
with no cap (`jatayu/validate.py`, tests in `tests/test_validate.py`). Dev, new-flag definition: standard seed 11
195 → 198/200, harder seed 12 168 → 171/200; false flags unchanged 4 and 2 (`m4dev-*.report.md`).

## 5. Re-measure once (regenerated test, steps 1-4 frozen at `69d1a38`)

| | Fresh (seed 2028) | Harder (seed 2029) |
|---|---|---|
| Catch, new-flag | **198/200 (99.0%; 96.4-99.7)** | **156/200 (78.0%; 71.8-83.2)** |
| Catch, existing | 198/200 (99.0%) | 156/200 (78.0%) |
| Base already flagged | 0/200 | 0/200 |
| False-flag rate | 0/200 (0.0%; 0.0-1.9) | 0/200 (0.0%; 0.0-1.9) |

Per corruption and per range class (with 95% CIs) and the aggregate misses are in
`m3-seeded-test-seed2028-FRESH-regenerated.report.md` and `m3-seeded-test-seed2029-HARDER-regenerated.report.md`.
Caveat: 200 draws with replacement from 193 eligible records → 173 (fresh) and 186 (harder) distinct cases; the
Wilson intervals treat 200 as independent, so they are somewhat narrow.

## Protocol slip (disclosed)

The step-4 gold-dose audit (`results/m4dev-gold-dose-audit-AFTER-weight-range/`) also read test and final_test gold
labels with the step-4 validator before step 5 (aggregate counts only, identical to the POST audit). Logged; the
validator was not changed afterwards.

## Dev reruns on the regenerated data (run once each; `results/m3-dev-*`, commit `b1be174`)

Dev only. Text = template-generated, extractor and generator share a lexicon, not a headline number. Speech =
synthetic (Piper). Dangerous errors: strict (headline) / lenient, over given gold records.

| Run | Entity F1 | Exact | Dangerous strict / lenient | Context errors | WER |
|---|---|---|---|---|---|
| text, rules | 1.000 | 1.000 | 0/440 / 0/440 | 20/80 | — |
| text, hybrid | 0.988 | 0.927 | 5/440 / 5/440 | 20/80 | — |
| text, LLM only | 0.897 | 0.771 | 3/440 / 3/440 | 37/80 | — |
| speech, hybrid | 0.626 | 0.292 | 4/440 / 4/440 | 21/80 | 0.631 |
| noisy speech, hybrid (160 utt × 3 SNR) | 0.600 | 0.381 | 2/240 / 2/240 | 62/240 | 0.696 |

Noise curve (entity F1): 20 dB 0.636 · 10 dB 0.611 · 5 dB 0.550. Hybrid fell back to rules on LLM JSON failures 10
times (speech) and 5 times (noise) out of 480 clips each.
