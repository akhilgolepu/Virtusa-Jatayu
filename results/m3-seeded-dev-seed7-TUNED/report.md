# Seeded-error test

200 corrupted dev records (seed 7); target ≥ 95 % flagged.

| Corruption | Flagged |
|---|---|
| dose_x10 | 50/50 (100.0%) |
| dose_div10 | 47/50 (94.0%) |
| mg_mcg_swap | 50/50 (100.0%) |
| wrong_route | 50/50 (100.0%) |
| **All** | **197/200 (98.5%)** |

False flags on the uncorrupted originals: 19/200.

## Misses (first 10)

- dose_div10: magnesium sulfate 0.4 g IV → flags none
- dose_div10: hydrocortisone 20 mg IV → flags none
- dose_div10: ringer lactate 50 ml IV → flags ['weight_based_dose']
