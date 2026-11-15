# Blind off-template set v1 — aggregate only (`r8-blind-v1-converter-corrected`)

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

| Extractor | Entity F1 (P / R) | Exact match | Dangerous (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|
| rules (`746c000`) | 0.892 (0.945 / 0.844) | 24/36 | 0/30 / 0/30 | 0/3 | 0/6 | 57 |
| hybrid (`746c000`) | 0.858 (0.933 / 0.795) | 22/36 | 0/30 / 0/30 | 0/3 | 0/6 | 62 |
| llm (`746c000`) | 0.780 (0.790 / 0.770) | 20/36 | 0/30 / 0/30 | 1/3 | 1/6 | 62 |

## Tier: stretch

| Extractor | Entity F1 (P / R) | Exact match | Dangerous (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|
| rules (`746c000`) | 0.857 (0.923 / 0.800) | 1/4 | 1/4 / 1/4 | 0/0 | 0/0 | 7 |
| hybrid (`746c000`) | 0.857 (0.923 / 0.800) | 1/4 | 1/4 / 1/4 | 0/0 | 0/0 | 7 |
| llm (`746c000`) | 0.812 (0.765 / 0.867) | 1/4 | 0/4 / 0/4 | 0/0 | 0/0 | 12 |

## Tier: all

| Extractor | Entity F1 (P / R) | Exact match | Dangerous (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|
| rules (`746c000`) | 0.888 (0.943 / 0.839) | 25/40 | 1/34 / 1/34 | 0/3 | 0/6 | 64 |
| hybrid (`746c000`) | 0.858 (0.932 / 0.796) | 23/40 | 1/34 / 1/34 | 0/3 | 0/6 | 69 |
| llm (`746c000`) | 0.784 (0.787 / 0.781) | 21/40 | 0/34 / 0/34 | 1/3 | 1/6 | 74 |

## Flags raised, by code (all tiers)

| Code | rules | hybrid | llm |
|---|---|---|---|
| ambiguous_dose | 2 | 1 | 0 |
| dose_below_range | 1 | 1 | 3 |
| dose_out_of_range | 1 | 2 | 1 |
| dose_range_stated | 2 | 2 | 0 |
| duplicate_dose | 1 | 1 | 5 |
| field_missing | 15 | 16 | 3 |
| llm_omitted | 0 | 1 | 0 |
| llm_unsupported | 0 | 2 | 22 |
| low_confidence | 1 | 1 | 0 |
| no_reference_range | 1 | 1 | 1 |
| possible_measurement | 1 | 1 | 0 |
| possible_not_given | 3 | 3 | 0 |
| repeat_dose_inferred | 2 | 2 | 0 |
| repeat_too_soon | 1 | 1 | 7 |
| self_correction | 2 | 2 | 0 |
| time_not_stated | 31 | 32 | 32 |
