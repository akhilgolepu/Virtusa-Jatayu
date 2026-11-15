# Blind off-template set v1 — aggregate only (`r11-blind-v1-rules`)

Evaluator-authored, 32 typed sentences (28 core, 4 stretch). Run once per extractor, per the file's protocol; nothing in the pipeline was changed. **A sanity check from a single author, not a headline number.**

## Conversion (script only, no gold fixed)

| Mapping | Count |
|---|---|
| concentration: no field in the repo's gold format (dropped) | 1 |
| dose: text, not one number -> no single gold dose | 4 |
| drug: NOT in lexicon (kept as written) | 4 |
| drug: in lexicon | 33 |
| procedure: in lexicon | 3 |
| route: mapped | 31 |
| status: given | 34 |
| status: measurement | 3 |
| status: not_done | 1 |
| status: not_given | 2 |
| time: unparseable -> not stated | 2 |
| unit: mapped | 28 |

## Tier: core

| Extractor | Entity F1 (P / R) | Exact match | Dangerous, headline (round 10) | Dangerous, matched-drug only (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|---|
| rules (`1515ea5`) | 0.906 (0.946 / 0.869) | 25/36 | 1/33 | 0/30 / 0/30 | 0/3 | 0/6 | 60 |

## Tier: stretch

| Extractor | Entity F1 (P / R) | Exact match | Dangerous, headline (round 10) | Dangerous, matched-drug only (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|---|
| rules (`1515ea5`) | 0.571 (0.615 / 0.533) | 0/4 | 0/4 | 0/4 / 0/4 | 0/0 | 0/0 | 11 |

## Tier: all

| Extractor | Entity F1 (P / R) | Exact match | Dangerous, headline (round 10) | Dangerous, matched-drug only (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|---|
| rules (`1515ea5`) | 0.870 (0.912 / 0.832) | 25/40 | 1/37 | 0/34 / 0/34 | 0/3 | 0/6 | 71 |

## Flags raised, by code (all tiers)

| Code | rules | hybrid | llm |
|---|---|---|---|
| ambiguous_dose | 2 |
| concentration_not_dose | 1 |
| dose_below_range | 1 |
| dose_out_of_range | 1 |
| dose_range_stated | 2 |
| drug_not_in_lexicon | 2 |
| duplicate_dose | 1 |
| field_missing | 18 |
| possible_measurement | 1 |
| possible_not_given | 3 |
| repeat_dose_inferred | 2 |
| repeat_too_soon | 1 |
| self_correction | 2 |
| sound_alike_drug | 1 |
| time_not_stated | 33 |
