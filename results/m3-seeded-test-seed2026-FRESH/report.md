# Seeded-error test — standard

200 corrupted **test** records (seed 2026, pool 191); commit at start `bce5504-dirty`. 'no_reference_range' (not range-checked) is not counted as a catch.

| | Value |
|---|---|
| **Catch rate** | **189/200 (94.5%; 95% CI 90.4%-96.9%)** |
| **False-flag rate** (uncorrupted originals flagged) | **16/200 (8.0%; 95% CI 5.0%-12.6%)** |

| Corruption | Flagged |
|---|---|
| dose_x10 | 49/50 (98.0%; 95% CI 89.5%-99.7%) |
| dose_div10 | 40/50 (80.0%; 95% CI 67.0%-88.8%) |
| mg_mcg_swap | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| wrong_route | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | Flagged |
|---|---|
| cited | 175/186 (94.1%; 95% CI 89.7%-96.7%) |
| illustrative | 14/14 (100.0%; 95% CI 78.5%-100.0%) |

## Residual misses (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_div10 | cited | only non-catching: weight_based_dose | 10 |
| dose_x10 | cited | only non-catching: weight_based_dose | 1 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
| dose_below_range | cited | 8 |
| dose_out_of_range | cited | 8 |
