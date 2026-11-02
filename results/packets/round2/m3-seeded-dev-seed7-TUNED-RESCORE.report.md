# Seeded-error test — standard

200 corrupted **dev** records (seed 7, pool 297); commit at start `0f8f983-dirty`. 'no_reference_range' (not range-checked) and 'weight_based_dose' (informational) are not counted as a catch.

| | Value |
|---|---|
| **Catch rate, new-flag definition** (a catching flag the base did not have) | **193/200 (96.5%; 95% CI 93.0%-98.3%)** |
| Catch rate, existing definition (any catching flag) | 197/200 (98.5%; 95% CI 95.7%-99.5%) |
| Base records already flagged before corruption | 19/200 (9.5%; 95% CI 6.2%-14.4%) |
| **False-flag rate** (uncorrupted originals flagged) | **19/200 (9.5%; 95% CI 6.2%-14.4%)** |

| Corruption | New-flag | Existing |
|---|---|---|
| dose_x10 | 48/50 (96.0%; 95% CI 86.5%-98.9%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| dose_div10 | 46/50 (92.0%; 95% CI 81.2%-96.9%) | 47/50 (94.0%; 95% CI 83.8%-97.9%) |
| mg_mcg_swap | 49/50 (98.0%; 95% CI 89.5%-99.7%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| wrong_route | 50/50 (100.0%; 95% CI 92.9%-100.0%) | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | New-flag | Existing |
|---|---|---|
| cited | 172/179 (96.1%; 95% CI 92.2%-98.1%) | 176/179 (98.3%; 95% CI 95.2%-99.4%) |
| illustrative | 21/21 (100.0%; 95% CI 84.5%-100.0%) | 21/21 (100.0%; 95% CI 84.5%-100.0%) |

## Residual misses, existing definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_div10 | cited | no flag | 2 |
| dose_div10 | cited | only non-catching: weight_based_dose | 1 |

## Residual misses, new-flag definition (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_x10 | cited | only flags the base already had: dose_out_of_range | 2 |
| dose_div10 | cited | no flag | 2 |
| dose_div10 | cited | only non-catching: weight_based_dose | 1 |
| dose_div10 | cited | only flags the base already had: dose_below_range | 1 |
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
| dose_div10 | magnesium sulfate 0.4 g IV (from 4 g) | none |
| dose_div10 | hydrocortisone 20 mg IV (from 200 mg) | none |
| dose_div10 | ringer lactate 50 ml IV (from 500 ml) | weight_based_dose |
| dose_div10 | atropine 0.05 mg IV (from 0.5 mg) | dose_below_range |
| mg_mcg_swap | atropine 0.5 mcg IV (from 0.5 mg) | dose_below_range |

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
