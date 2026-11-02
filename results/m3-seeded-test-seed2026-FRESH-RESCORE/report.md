# Seeded-error test — standard

200 corrupted **test** records (seed 2026, pool 191); commit at start `0f8f983-dirty`. 'no_reference_range' (not range-checked) and 'weight_based_dose' (informational) are not counted as a catch.

| | Value |
|---|---|
| **Catch rate, new-flag definition** (a catching flag the base did not have) | **186/200 (93.0%; 95% CI 88.6%-95.8%)** |
| Catch rate, existing definition (any catching flag) | 189/200 (94.5%; 95% CI 90.4%-96.9%) |
| Base records already flagged before corruption | 16/200 (8.0%; 95% CI 5.0%-12.6%) |
| **False-flag rate** (uncorrupted originals flagged) | **16/200 (8.0%; 95% CI 5.0%-12.6%)** |

| Corruption | New-flag | Existing |
|---|---|---|
| dose_x10 | 48/50 (96.0%; 95% CI 86.5%-98.9%) | 49/50 (98.0%; 95% CI 89.5%-99.7%) |
| dose_div10 | 38/50 (76.0%; 95% CI 62.6%-85.7%) | 40/50 (80.0%; 95% CI 67.0%-88.8%) |
| mg_mcg_swap | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| wrong_route | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | New-flag | Existing |
|---|---|---|
| cited | 172/186 (92.5%; 95% CI 87.8%-95.5%) | 175/186 (94.1%; 95% CI 89.7%-96.7%) |
| illustrative | 14/14 (100.0%; 95% CI 78.5%-100.0%) | 14/14 (100.0%; 95% CI 78.5%-100.0%) |

## Residual misses, existing definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_div10 | cited | only non-catching: weight_based_dose | 10 |
| dose_x10 | cited | only non-catching: weight_based_dose | 1 |

## Residual misses, new-flag definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_div10 | cited | only non-catching: weight_based_dose | 10 |
| dose_div10 | cited | only flags the base already had: dose_below_range | 2 |
| dose_x10 | cited | only flags the base already had: dose_out_of_range | 1 |
| dose_x10 | cited | only non-catching: weight_based_dose | 1 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
| dose_below_range | cited | 8 |
| dose_out_of_range | cited | 8 |
