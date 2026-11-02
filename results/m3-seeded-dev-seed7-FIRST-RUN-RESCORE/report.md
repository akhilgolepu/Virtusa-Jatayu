# Seeded-error test — standard

200 corrupted **dev** records (seed 7, pool 297); commit at start `0f8f983-dirty`. 'no_reference_range' (not range-checked) and 'weight_based_dose' (informational) are not counted as a catch.

| | Value |
|---|---|
| **Catch rate, new-flag definition** (a catching flag the base did not have) | **159/200 (79.5%; 95% CI 73.4%-84.5%)** |
| Catch rate, existing definition (any catching flag) | 163/200 (81.5%; 95% CI 75.5%-86.3%) |
| Base records already flagged before corruption | 19/200 (9.5%; 95% CI 6.2%-14.4%) |
| **False-flag rate** (uncorrupted originals flagged) | **19/200 (9.5%; 95% CI 6.2%-14.4%)** |

| Corruption | New-flag | Existing |
|---|---|---|
| dose_x10 | 42/50 (84.0%; 95% CI 71.5%-91.7%) | 44/50 (88.0%; 95% CI 76.2%-94.4%) |
| dose_div10 | 21/50 (42.0%; 95% CI 29.4%-55.8%) | 22/50 (44.0%; 95% CI 31.2%-57.7%) |
| mg_mcg_swap | 46/50 (92.0%; 95% CI 81.2%-96.9%) | 47/50 (94.0%; 95% CI 83.8%-97.9%) |
| wrong_route | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | New-flag | Existing |
|---|---|---|
| cited | 152/179 (84.9%; 95% CI 78.9%-89.4%) | 156/179 (87.2%; 95% CI 81.5%-91.3%) |
| none | 7/21 (33.3%; 95% CI 17.2%-54.6%) | 7/21 (33.3%; 95% CI 17.2%-54.6%) |

## Residual misses, existing definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_div10 | cited | no flag | 22 |
| dose_x10 | none | only non-catching: no_reference_range | 6 |
| dose_div10 | none | only non-catching: no_reference_range | 6 |
| mg_mcg_swap | none | only non-catching: no_reference_range | 2 |
| mg_mcg_swap | cited | no flag | 1 |

## Residual misses, new-flag definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_div10 | cited | no flag | 22 |
| dose_x10 | none | only non-catching: no_reference_range | 6 |
| dose_div10 | none | only non-catching: no_reference_range | 6 |
| dose_x10 | cited | only flags the base already had: dose_out_of_range | 2 |
| mg_mcg_swap | none | only non-catching: no_reference_range | 2 |
| dose_div10 | cited | only flags the base already had: dose_below_range | 1 |
| mg_mcg_swap | cited | no flag | 1 |
| mg_mcg_swap | cited | only flags the base already had: dose_below_range | 1 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
| dose_out_of_range | cited | 10 |
| dose_below_range | cited | 9 |

## Residual misses (dev records, first 15)

| Corruption | Corrupted record | Flags |
|---|---|---|
| dose_x10 | hydrocortisone 2000 mg IV (from 200 mg) | dose_out_of_range |
| dose_x10 | ketorolac 600 mg IM (from 60 mg) | dose_out_of_range |
| dose_x10 | furosemide 400 mg IV (from 40 mg) | no_reference_range |
| dose_x10 | furosemide 400 mg IV (from 40 mg) | no_reference_range |
| dose_x10 | ketamine 500 mg IN (from 50 mg) | no_reference_range |
| dose_x10 | norepinephrine 100 mcg IV (from 10 mcg) | no_reference_range |
| dose_x10 | oxygen 150 L/min INH (from 15 L/min) | no_reference_range |
| dose_x10 | furosemide 800 mg IV (from 80 mg) | no_reference_range |
| dose_div10 | norepinephrine 0.4 mcg IV (from 4 mcg) | no_reference_range |
| dose_div10 | diphenhydramine 2.5 mg IV (from 25 mg) | none |
| dose_div10 | magnesium sulfate 0.4 g IV (from 4 g) | none |
| dose_div10 | fentanyl 2.5 mcg IV (from 25 mcg) | none |
| dose_div10 | norepinephrine 1 mcg IV (from 10 mcg) | no_reference_range |
| dose_div10 | fentanyl 10 mcg IN (from 100 mcg) | none |
| dose_div10 | fentanyl 2.5 mcg IV (from 25 mcg) | none |

## False flags (dev records)

| Record | Rule fired | Why |
|---|---|---|
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. |
| salbutamol 2 puffs INH | dose_below_range | 2 puffs is below the published adult dose. Source: Airway Respiratory Irritants p.314; Respiratory Distress p.191. |
| atropine 0.5 mg IV | dose_below_range | 0.5 mg is below the published adult dose. Source: Acetylcholinesterase Inhibitors p.265 Table 1; Acetylcholinesterase Inhibitors p.265 Table 2. |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. |
| atropine 0.5 mg IV | dose_below_range | 0.5 mg is below the published adult dose. Source: Acetylcholinesterase Inhibitors p.265 Table 1; Acetylcholinesterase Inhibitors p.265 Table 2. |
| atropine 0.5 mg IV | dose_below_range | 0.5 mg is below the published adult dose. Source: Acetylcholinesterase Inhibitors p.265 Table 1; Acetylcholinesterase Inhibitors p.265 Table 2. |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. |
| ipratropium 250 mcg NEB | dose_below_range | 250 mcg is below the published adult dose. Source: Respiratory Distress pp.191-192. |
| ipratropium 250 mcg NEB | dose_below_range | 250 mcg is below the published adult dose. Source: Respiratory Distress pp.191-192. |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. |
| salbutamol 2 puffs INH | dose_below_range | 2 puffs is below the published adult dose. Source: Airway Respiratory Irritants p.314; Respiratory Distress p.191. |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. |
