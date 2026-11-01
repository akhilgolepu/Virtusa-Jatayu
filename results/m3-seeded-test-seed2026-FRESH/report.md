# Seeded-error test — standard

200 corrupted **test** records (seed 2026, pool 191); commit at start `bce5504-dirty`. 'no_reference_range' (not range-checked) is not counted as a catch.

| | Value |
|---|---|
| **Catch rate** | **189/200 (94.5%)** |
| **False-flag rate** (uncorrupted originals flagged) | **16/200 (8.0%)** |

| Corruption | Flagged |
|---|---|
| dose_x10 | 49/50 (98.0%) |
| dose_div10 | 40/50 (80.0%) |
| mg_mcg_swap | 50/50 (100.0%) |
| wrong_route | 50/50 (100.0%) |

| Range class (original drug + route) | Flagged |
|---|---|
| cited | 175/186 (94.1%) |
| illustrative | 14/14 (100.0%) |

## Residual misses (first 15)

| Corruption | Range class | Corrupted record | Flags |
|---|---|---|---|
| dose_x10 | cited | normal saline 2500 ml IV (was 250 ml) | weight_based_dose |
| dose_div10 | cited | ringer lactate 50 ml IV (was 500 ml) | weight_based_dose |
| dose_div10 | cited | ringer lactate 100 ml IV (was 1000 ml) | weight_based_dose |
| dose_div10 | cited | normal saline 25 ml IV (was 250 ml) | weight_based_dose |
| dose_div10 | cited | ringer lactate 100 ml IV (was 1000 ml) | weight_based_dose |
| dose_div10 | cited | ringer lactate 50 ml IV (was 500 ml) | weight_based_dose |
| dose_div10 | cited | normal saline 100 ml IV (was 1000 ml) | weight_based_dose |
| dose_div10 | cited | normal saline 25 ml IV (was 250 ml) | weight_based_dose |
| dose_div10 | cited | normal saline 50 ml IV (was 500 ml) | weight_based_dose |
| dose_div10 | cited | ringer lactate 100 ml IV (was 1000 ml) | weight_based_dose |
| dose_div10 | cited | ringer lactate 50 ml IV (was 500 ml) | weight_based_dose |

## False flags on uncorrupted originals

| Record | Rule fired | Why | Range class |
|---|---|---|---|
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ipratropium 250 mcg NEB | dose_below_range | 250 mcg is below the published adult dose. Source: Respiratory Distress pp.191-192. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
