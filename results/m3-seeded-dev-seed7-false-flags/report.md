# Seeded-error test — standard

200 corrupted **dev** records (seed 7, pool 297); commit at start `bce5504-dirty`. 'no_reference_range' (not range-checked) is not counted as a catch.

| | Value |
|---|---|
| **Catch rate** | **197/200 (98.5%)** |
| **False-flag rate** (uncorrupted originals flagged) | **19/200 (9.5%)** |

| Corruption | Flagged |
|---|---|
| dose_x10 | 50/50 (100.0%) |
| dose_div10 | 47/50 (94.0%) |
| mg_mcg_swap | 50/50 (100.0%) |
| wrong_route | 50/50 (100.0%) |

| Range class (original drug + route) | Flagged |
|---|---|
| cited | 176/179 (98.3%) |
| illustrative | 21/21 (100.0%) |

## Residual misses (first 15)

| Corruption | Range class | Corrupted record | Flags |
|---|---|---|---|
| dose_div10 | cited | magnesium sulfate 0.4 g IV (was 4 g) | none |
| dose_div10 | cited | hydrocortisone 20 mg IV (was 200 mg) | none |
| dose_div10 | cited | ringer lactate 50 ml IV (was 500 ml) | weight_based_dose |

## False flags on uncorrupted originals

| Record | Rule fired | Why | Range class |
|---|---|---|---|
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| salbutamol 2 puffs INH | dose_below_range | 2 puffs is below the published adult dose. Source: Airway Respiratory Irritants p.314; Respiratory Distress p.191. | cited |
| atropine 0.5 mg IV | dose_below_range | 0.5 mg is below the published adult dose. Source: Acetylcholinesterase Inhibitors p.265 Table 1; Acetylcholinesterase Inhibitors p.265 Table 2. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| atropine 0.5 mg IV | dose_below_range | 0.5 mg is below the published adult dose. Source: Acetylcholinesterase Inhibitors p.265 Table 1; Acetylcholinesterase Inhibitors p.265 Table 2. | cited |
| atropine 0.5 mg IV | dose_below_range | 0.5 mg is below the published adult dose. Source: Acetylcholinesterase Inhibitors p.265 Table 1; Acetylcholinesterase Inhibitors p.265 Table 2. | cited |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| ipratropium 250 mcg NEB | dose_below_range | 250 mcg is below the published adult dose. Source: Respiratory Distress pp.191-192. | cited |
| ipratropium 250 mcg NEB | dose_below_range | 250 mcg is below the published adult dose. Source: Respiratory Distress pp.191-192. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| salbutamol 2 puffs INH | dose_below_range | 2 puffs is below the published adult dose. Source: Airway Respiratory Irritants p.314; Respiratory Distress p.191. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
