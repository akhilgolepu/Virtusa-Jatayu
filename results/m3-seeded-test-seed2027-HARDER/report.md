# Seeded-error test — harder

200 corrupted **test** records (seed 2027, pool 191); commit at start `bce5504-dirty`. 'no_reference_range' (not range-checked) is not counted as a catch.

| | Value |
|---|---|
| **Catch rate** | **139/200 (69.5%; 95% CI 62.8%-75.5%)** |
| **False-flag rate** (uncorrupted originals flagged) | **15/200 (7.5%; 95% CI 4.6%-12.0%)** |

| Corruption | Flagged |
|---|---|
| dose_x2 | 20/50 (40.0%; 95% CI 27.6%-53.8%) |
| dose_x5 | 40/50 (80.0%; 95% CI 67.0%-88.8%) |
| digit_slip | 29/50 (58.0%; 95% CI 44.2%-70.6%) |
| mg_to_g | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | Flagged |
|---|---|
| cited | 134/189 (70.9%; 95% CI 64.1%-76.9%) |
| illustrative | 5/11 (45.5%; 95% CI 21.3%-72.0%) |

## Residual misses (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x2 | cited | no flag | 26 |
| digit_slip | cited | no flag | 19 |
| dose_x5 | cited | no flag | 4 |
| dose_x5 | cited | only non-catching: weight_based_dose | 4 |
| dose_x2 | cited | only non-catching: weight_based_dose | 2 |
| dose_x2 | illustrative | no flag | 2 |
| dose_x5 | illustrative | no flag | 2 |
| digit_slip | illustrative | no flag | 2 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
| dose_out_of_range | cited | 11 |
| dose_below_range | cited | 4 |
