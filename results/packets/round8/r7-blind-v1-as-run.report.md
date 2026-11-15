# Blind off-template set v1 — aggregate only (`r7-blind-v1`)

Evaluator-authored, 32 typed sentences (28 core, 4 stretch). Run once per extractor, per the file's protocol; nothing in the pipeline was changed. **A sanity check from a single author, not a headline number.**

## Conversion (script only, no gold fixed)

| Mapping | Count |
|---|---|
| concentration: no field in the repo's gold format (dropped) | 1 |
| dose: text, not one number -> no single gold dose | 4 |
| drug: NOT in lexicon (kept as written) | 5 |
| drug: in lexicon | 32 |
| procedure: NOT in lexicon (kept as written) | 2 |
| procedure: in lexicon | 1 |
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
| rules (`3b7be15`) | 0.840 (0.890 / 0.795) | 21/36 | 0/30 / 0/30 | 0/3 | 0/6 | 57 |
| hybrid (`3b7be15`) | 0.805 (0.875 / 0.746) | 19/36 | 0/30 / 0/30 | 0/3 | 0/6 | 62 |
| llm (`3b7be15`) | 0.747 (0.756 / 0.738) | 19/36 | 0/30 / 0/30 | 1/3 | 1/6 | 62 |

## Tier: stretch

| Extractor | Entity F1 (P / R) | Exact match | Dangerous (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|
| rules (`3b7be15`) | 0.857 (0.923 / 0.800) | 1/4 | 1/4 / 1/4 | 0/0 | 0/0 | 7 |
| hybrid (`3b7be15`) | 0.857 (0.923 / 0.800) | 1/4 | 1/4 / 1/4 | 0/0 | 0/0 | 7 |
| llm (`3b7be15`) | 0.812 (0.765 / 0.867) | 1/4 | 0/4 / 0/4 | 0/0 | 0/0 | 12 |

## Tier: all

| Extractor | Entity F1 (P / R) | Exact match | Dangerous (strict / lenient) | Admin-status errors | Context errors | Flags raised |
|---|---|---|---|---|---|---|
| rules (`3b7be15`) | 0.842 (0.893 / 0.796) | 22/40 | 1/34 / 1/34 | 0/3 | 0/6 | 64 |
| hybrid (`3b7be15`) | 0.811 (0.880 / 0.752) | 20/40 | 1/34 / 1/34 | 0/3 | 0/6 | 69 |
| llm (`3b7be15`) | 0.755 (0.757 / 0.752) | 20/40 | 0/34 / 0/34 | 1/3 | 1/6 | 74 |

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
