# Seeded-error test — standard

200 corrupted **dev** records (seed 11, pool 299); commit at start `cbb435c-dirty`. 'no_reference_range' (not range-checked) and 'weight_based_dose' (informational) are not counted as a catch.

| | Value |
|---|---|
| **Catch rate, new-flag definition** (a catching flag the base did not have) | **198/200 (99.0%; 95% CI 96.4%-99.7%)** |
| Catch rate, existing definition (any catching flag) | 198/200 (99.0%; 95% CI 96.4%-99.7%) |
| Base records already flagged before corruption | 4/200 (2.0%; 95% CI 0.8%-5.0%) |
| **False-flag rate** (uncorrupted originals flagged) | **4/200 (2.0%; 95% CI 0.8%-5.0%)** |

| Corruption | New-flag | Existing |
|---|---|---|
| dose_x10 | 49/50 (98.0%; 95% CI 89.5%-99.7%) | 49/50 (98.0%; 95% CI 89.5%-99.7%) |
| dose_div10 | 49/50 (98.0%; 95% CI 89.5%-99.7%) | 49/50 (98.0%; 95% CI 89.5%-99.7%) |
| mg_mcg_swap | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| wrong_route | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | New-flag | Existing |
|---|---|---|
| cited | 176/178 (98.9%; 95% CI 96.0%-99.7%) | 176/178 (98.9%; 95% CI 96.0%-99.7%) |
| illustrative | 22/22 (100.0%; 95% CI 85.1%-100.0%) | 22/22 (100.0%; 95% CI 85.1%-100.0%) |

## Residual misses, existing definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x10 | cited | no flag | 1 |
| dose_div10 | cited | no flag | 1 |

## Residual misses, new-flag definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x10 | cited | no flag | 1 |
| dose_div10 | cited | no flag | 1 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
| dose_below_range | cited | 2 |
| possible_mg_mcg_confusion | cited | 2 |

## Residual misses (dev records, first 15)

| Corruption | Corrupted record | Flags |
|---|---|---|
| dose_x10 | epinephrine 10 mcg IV (from 1 mcg) | none |
| dose_div10 | magnesium sulfate 0.6 g IV (from 6 g) | none |

## False flags (dev records)

| Record | Rule fired | Why |
|---|---|---|
| dextrose 4 g IV | dose_below_range | 4 g is below the published adult dose. Source: Hypoglycemia p.85; Hypoglycemia pp.85-86. |
| epinephrine 1 mcg IV | possible_mg_mcg_confusion | 1 mcg is outside the range but would fit if mg and mcg were swapped. Source: Bradycardia p.36; Cardiac Arrest p.121 Pearl 11. |
| dextrose 3 g IV | dose_below_range | 3 g is below the published adult dose. Source: Hypoglycemia p.85; Hypoglycemia pp.85-86. |
| epinephrine 1 mcg IV | possible_mg_mcg_confusion | 1 mcg is outside the range but would fit if mg and mcg were swapped. Source: Bradycardia p.36; Cardiac Arrest p.121 Pearl 11. |
