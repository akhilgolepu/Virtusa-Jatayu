# Seeded-error test — harder

200 corrupted **dev** records (seed 12, pool 299); commit at start `cbb435c-dirty`. 'no_reference_range' (not range-checked) and 'weight_based_dose' (informational) are not counted as a catch.

| | Value |
|---|---|
| **Catch rate, new-flag definition** (a catching flag the base did not have) | **171/200 (85.5%; 95% CI 80.0%-89.7%)** |
| Catch rate, existing definition (any catching flag) | 172/200 (86.0%; 95% CI 80.5%-90.1%) |
| Base records already flagged before corruption | 2/200 (1.0%; 95% CI 0.3%-3.6%) |
| **False-flag rate** (uncorrupted originals flagged) | **2/200 (1.0%; 95% CI 0.3%-3.6%)** |

| Corruption | New-flag | Existing |
|---|---|---|
| dose_x2 | 41/50 (82.0%; 95% CI 69.2%-90.2%) | 41/50 (82.0%; 95% CI 69.2%-90.2%) |
| dose_x5 | 49/50 (98.0%; 95% CI 89.5%-99.7%) | 49/50 (98.0%; 95% CI 89.5%-99.7%) |
| digit_slip | 31/50 (62.0%; 95% CI 48.1%-74.1%) | 32/50 (64.0%; 95% CI 50.1%-75.9%) |
| mg_to_g | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | New-flag | Existing |
|---|---|---|
| cited | 163/186 (87.6%; 95% CI 82.1%-91.6%) | 164/186 (88.2%; 95% CI 82.7%-92.1%) |
| illustrative | 8/14 (57.1%; 95% CI 32.6%-78.6%) | 8/14 (57.1%; 95% CI 32.6%-78.6%) |

## Residual misses, existing definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| digit_slip | cited | no flag | 13 |
| dose_x2 | cited | no flag | 7 |
| digit_slip | illustrative | no flag | 4 |
| dose_x2 | illustrative | no flag | 2 |
| dose_x5 | cited | no flag | 1 |
| digit_slip | cited | only non-catching: weight_based_dose | 1 |

## Residual misses, new-flag definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| digit_slip | cited | no flag | 13 |
| dose_x2 | cited | no flag | 7 |
| digit_slip | illustrative | no flag | 4 |
| dose_x2 | illustrative | no flag | 2 |
| dose_x5 | cited | no flag | 1 |
| digit_slip | cited | only flags the base already had: dose_below_range | 1 |
| digit_slip | cited | only non-catching: weight_based_dose | 1 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
| dose_below_range | cited | 2 |

## Residual misses (dev records, first 15)

| Corruption | Corrupted record | Flags |
|---|---|---|
| dose_x2 | diphenhydramine 40 mg PO (from 20 mg) | none |
| dose_x2 | norepinephrine 10 mcg IV (from 5 mcg) | none |
| dose_x2 | normal saline 1500 ml IV (from 750 ml) | none |
| dose_x2 | nitroglycerin 0.8 mg SL (from 0.4 mg) | none |
| dose_x2 | nitroglycerin 0.8 mg SL (from 0.4 mg) | none |
| dose_x2 | norepinephrine 20 mcg IV (from 10 mcg) | none |
| dose_x2 | fentanyl 100 mcg IM (from 50 mcg) | none |
| dose_x2 | naloxone 1.2 mg IN (from 0.6 mg) | none |
| dose_x2 | dexamethasone 8 mg IM (from 4 mg) | none |
| dose_x5 | diazepam 10 mg IV (from 2 mg) | none |
| digit_slip | amiodarone 201 mg IO (from 200 mg) | none |
| digit_slip | midazolam 3 mg IO (from 4 mg) | none |
| digit_slip | furosemide 28 mg IV (from 25 mg) | none |
| digit_slip | dextrose 1 g IV (from 4 g) | dose_below_range |
| digit_slip | ondansetron 7 mg IV (from 4 mg) | none |

## False flags (dev records)

| Record | Rule fired | Why |
|---|---|---|
| naloxone 0.6 mg IN | dose_below_range | 0.6 mg is below the published adult dose. Source: Opioid Poisoning/Overdose p.304. |
| dextrose 4 g IV | dose_below_range | 4 g is below the published adult dose. Source: Hypoglycemia p.85; Hypoglycemia pp.85-86. |
