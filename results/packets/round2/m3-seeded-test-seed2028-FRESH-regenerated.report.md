# Seeded-error test — standard

200 corrupted **test** records (seed 2028, pool 193); commit at start `2cbb9a7`. 'no_reference_range' (not range-checked) and 'weight_based_dose' (informational) are not counted as a catch.

| | Value |
|---|---|
| **Catch rate, new-flag definition** (a catching flag the base did not have) | **198/200 (99.0%; 95% CI 96.4%-99.7%)** |
| Catch rate, existing definition (any catching flag) | 198/200 (99.0%; 95% CI 96.4%-99.7%) |
| Base records already flagged before corruption | 0/200 (0.0%; 95% CI 0.0%-1.9%) |
| **False-flag rate** (uncorrupted originals flagged) | **0/200 (0.0%; 95% CI 0.0%-1.9%)** |

| Corruption | New-flag | Existing |
|---|---|---|
| dose_x10 | 49/50 (98.0%; 95% CI 89.5%-99.7%) | 49/50 (98.0%; 95% CI 89.5%-99.7%) |
| dose_div10 | 49/50 (98.0%; 95% CI 89.5%-99.7%) | 49/50 (98.0%; 95% CI 89.5%-99.7%) |
| mg_mcg_swap | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| wrong_route | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | New-flag | Existing |
|---|---|---|
| cited | 179/180 (99.4%; 95% CI 96.9%-99.9%) | 179/180 (99.4%; 95% CI 96.9%-99.9%) |
| illustrative | 19/20 (95.0%; 95% CI 76.4%-99.1%) | 19/20 (95.0%; 95% CI 76.4%-99.1%) |

## Residual misses, existing definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x10 | illustrative | no flag | 1 |
| dose_div10 | cited | no flag | 1 |

## Residual misses, new-flag definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x10 | illustrative | no flag | 1 |
| dose_div10 | cited | no flag | 1 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
