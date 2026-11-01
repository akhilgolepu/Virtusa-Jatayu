# Seeded-error test — harder

200 corrupted **test** records (seed 2027, pool 191); commit at start `bce5504-dirty`. 'no_reference_range' (not range-checked) is not counted as a catch.

| | Value |
|---|---|
| **Catch rate** | **139/200 (69.5%)** |
| **False-flag rate** (uncorrupted originals flagged) | **15/200 (7.5%)** |

| Corruption | Flagged |
|---|---|
| dose_x2 | 20/50 (40.0%) |
| dose_x5 | 40/50 (80.0%) |
| digit_slip | 29/50 (58.0%) |
| mg_to_g | 50/50 (100.0%) |

| Range class (original drug + route) | Flagged |
|---|---|
| cited | 134/189 (70.9%) |
| illustrative | 5/11 (45.5%) |

## Residual misses (first 15)

| Corruption | Range class | Corrupted record | Flags |
|---|---|---|---|
| dose_x2 | cited | normal saline 500 ml IV (was 250 ml) | none |
| dose_x2 | cited | adenosine 12 mg IV (was 6 mg) | none |
| dose_x2 | cited | normal saline 2000 ml IV (was 1000 ml) | none |
| dose_x2 | cited | ringer lactate 2000 ml IV (was 1000 ml) | none |
| dose_x2 | cited | naloxone 1.6 mg IV (was 0.8 mg) | none |
| dose_x2 | cited | salbutamol 5 mg NEB (was 2.5 mg) | none |
| dose_x2 | cited | dextrose 100 ml IV (was 50 ml) | none |
| dose_x2 | cited | ketamine 100 mg IV (was 50 mg) | weight_based_dose |
| dose_x2 | cited | normal saline 500 ml IV (was 250 ml) | none |
| dose_x2 | cited | ketamine 200 mg IM (was 100 mg) | weight_based_dose |
| dose_x2 | illustrative | norepinephrine 20 mcg IV (was 10 mcg) | none |
| dose_x2 | cited | midazolam 10 mg IM (was 5 mg) | none |
| dose_x2 | cited | methylprednisolone 80 mg IV (was 40 mg) | none |
| dose_x2 | cited | normal saline 2000 ml IV (was 1000 ml) | none |
| dose_x2 | cited | fentanyl 100 mcg IN (was 50 mcg) | none |

## False flags on uncorrupted originals

| Record | Rule fired | Why | Range class |
|---|---|---|---|
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
| ketorolac 60 mg IM | dose_out_of_range | 60 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| ketorolac 30 mg IV | dose_out_of_range | 30 mg is outside the published adult dose range. Source: Pain Management p.94. | cited |
| hydrocortisone 200 mg IV | dose_out_of_range | 200 mg is outside the published adult dose range. Source: Shock p.109. | cited |
| glucagon 0.5 mg IM | dose_below_range | 0.5 mg is below the published adult dose. Source: Hypoglycemia p.85. | cited |
