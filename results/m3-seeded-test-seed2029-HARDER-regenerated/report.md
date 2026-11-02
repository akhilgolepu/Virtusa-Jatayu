# Seeded-error test — harder

200 corrupted **test** records (seed 2029, pool 193); commit at start `2cbb9a7-dirty`. 'no_reference_range' (not range-checked) and 'weight_based_dose' (informational) are not counted as a catch.

| | Value |
|---|---|
| **Catch rate, new-flag definition** (a catching flag the base did not have) | **156/200 (78.0%; 95% CI 71.8%-83.2%)** |
| Catch rate, existing definition (any catching flag) | 156/200 (78.0%; 95% CI 71.8%-83.2%) |
| Base records already flagged before corruption | 0/200 (0.0%; 95% CI 0.0%-1.9%) |
| **False-flag rate** (uncorrupted originals flagged) | **0/200 (0.0%; 95% CI 0.0%-1.9%)** |

| Corruption | New-flag | Existing |
|---|---|---|
| dose_x2 | 34/50 (68.0%; 95% CI 54.2%-79.2%) | 34/50 (68.0%; 95% CI 54.2%-79.2%) |
| dose_x5 | 44/50 (88.0%; 95% CI 76.2%-94.4%) | 44/50 (88.0%; 95% CI 76.2%-94.4%) |
| digit_slip | 28/50 (56.0%; 95% CI 42.3%-68.8%) | 28/50 (56.0%; 95% CI 42.3%-68.8%) |
| mg_to_g | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | New-flag | Existing |
|---|---|---|
| cited | 152/186 (81.7%; 95% CI 75.5%-86.6%) | 152/186 (81.7%; 95% CI 75.5%-86.6%) |
| illustrative | 4/14 (28.6%; 95% CI 11.7%-54.6%) | 4/14 (28.6%; 95% CI 11.7%-54.6%) |

## Residual misses, existing definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x2 | cited | no flag | 13 |
| digit_slip | cited | no flag | 12 |
| digit_slip | illustrative | no flag | 5 |
| digit_slip | cited | only non-catching: weight_based_dose | 5 |
| dose_x5 | cited | only non-catching: weight_based_dose | 4 |
| dose_x2 | illustrative | no flag | 3 |
| dose_x5 | illustrative | no flag | 2 |

## Residual misses, new-flag definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x2 | cited | no flag | 13 |
| digit_slip | cited | no flag | 12 |
| digit_slip | illustrative | no flag | 5 |
| digit_slip | cited | only non-catching: weight_based_dose | 5 |
| dose_x5 | cited | only non-catching: weight_based_dose | 4 |
| dose_x2 | illustrative | no flag | 3 |
| dose_x5 | illustrative | no flag | 2 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
