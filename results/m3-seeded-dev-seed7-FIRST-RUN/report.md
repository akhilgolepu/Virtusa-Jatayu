# Seeded-error test

200 corrupted dev records (seed 7); target ≥ 95 % flagged.

| Corruption | Flagged |
|---|---|
| dose_x10 | 44/50 (88.0%) |
| dose_div10 | 22/50 (44.0%) |
| mg_mcg_swap | 47/50 (94.0%) |
| wrong_route | 50/50 (100.0%) |
| **All** | **163/200 (81.5%)** |

False flags on the uncorrupted originals: 19/200.

## Misses (first 10)

- dose_x10: furosemide 400 mg IV → flags ['no_reference_range']
- dose_x10: furosemide 400 mg IV → flags ['no_reference_range']
- dose_x10: ketamine 500 mg IN → flags ['no_reference_range']
- dose_x10: norepinephrine 100 mcg IV → flags ['no_reference_range']
- dose_x10: oxygen 150 L/min INH → flags ['no_reference_range']
- dose_x10: furosemide 800 mg IV → flags ['no_reference_range']
- dose_div10: norepinephrine 0.4 mcg IV → flags ['no_reference_range']
- dose_div10: diphenhydramine 2.5 mg IV → flags none
- dose_div10: magnesium sulfate 0.4 g IV → flags none
- dose_div10: fentanyl 2.5 mcg IV → flags none
