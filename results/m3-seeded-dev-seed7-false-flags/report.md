# Seeded-error test — standard

200 corrupted **dev** records (seed 7, pool 297); commit at start `bce5504-dirty`. 'no_reference_range' (not range-checked) is not counted as a catch.

| | Value |
|---|---|
| **Catch rate** | **197/200 (98.5%; 95% CI 95.7%-99.5%)** |
| **False-flag rate** (uncorrupted originals flagged) | **19/200 (9.5%; 95% CI 6.2%-14.4%)** |

| Corruption | Flagged |
|---|---|
| dose_x10 | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| dose_div10 | 47/50 (94.0%; 95% CI 83.8%-97.9%) |
| mg_mcg_swap | 50/50 (100.0%; 95% CI 92.9%-100.0%) |
| wrong_route | 50/50 (100.0%; 95% CI 92.9%-100.0%) |

| Range class (original drug + route) | Flagged |
|---|---|
| cited | 176/179 (98.3%; 95% CI 95.2%-99.4%) |
| illustrative | 21/21 (100.0%; 95% CI 84.5%-100.0%) |

## Residual misses (aggregate)

| Corruption | Range class | Outcome | Count |
|---|---|---|---|
| dose_div10 | cited | no flag | 2 |
| dose_div10 | cited | only non-catching: weight_based_dose | 1 |

## False flags by rule (aggregate)

| Rule fired | Range class | Count |
|---|---|---|
| dose_out_of_range | cited | 10 |
| dose_below_range | cited | 9 |

## Residual misses (dev records, first 15)

| Corruption | Corrupted record | Flags |
|---|---|---|
| dose_div10 | magnesium sulfate 0.4 g IV (from 4 g) | none |
| dose_div10 | hydrocortisone 20 mg IV (from 200 mg) | none |
| dose_div10 | ringer lactate 50 ml IV (from 500 ml) | weight_based_dose |

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
