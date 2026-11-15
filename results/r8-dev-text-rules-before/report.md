# Evaluation `r8-dev-text-rules-before`

Split **dev** · mode **text** · extractor **rules** · n = 480 utterances · commit at start `746c000`
**Source: template-generated; extractor and generator share a lexicon; not a headline number**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 1.000 (P 1.000, R 1.000) |
| Record exact match | 520/520 = 1.000 |
| **Dangerous errors** | **0 of 440** (0.00%; strict: weight_based_dose and low_asr_confidence do not catch) |
| Dangerous errors, lenient (weight_based_dose and low_asr_confidence count as catches) | 0 of 440 |
| **Administration-status errors** (not given, recorded as given) | **0 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 0 of 80 |
| Deliberate dose anomalies flagged | 21 of 21 |
| Accepted fields with a source quote | 1680 of 1680 |
| Latency p50 / p95 (s) | 0.0001 / 0.0003 (n=480) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 1.000 | 1.000 | 1.000 | 460 |
| dose_value | 1.000 | 1.000 | 1.000 | 380 |
| dose_unit | 1.000 | 1.000 | 1.000 | 380 |
| route | 1.000 | 1.000 | 1.000 | 360 |
| time | 1.000 | 1.000 | 1.000 | 244 |
| procedure | 1.000 | 1.000 | 1.000 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_measurement | 1.000 | 1.000 | 0/0 |
| category:context_negation | 1.000 | 1.000 | 0/0 |
| category:hinglish | 1.000 | 1.000 | 0/60 |
| category:med_basic | 1.000 | 1.000 | 0/40 |
| category:med_correction | 1.000 | 1.000 | 0/60 |
| category:med_incomplete | 1.000 | 1.000 | 0/40 |
| category:med_messy | 1.000 | 1.000 | 0/60 |
| category:med_multi | 1.000 | 1.000 | 0/80 |
| category:procedure | 1.000 | 1.000 | 0/60 |
| category:time_clock | 1.000 | 1.000 | 0/40 |
| lang:en | 1.000 | 1.000 | 0/380 |
| lang:hinglish | 1.000 | 1.000 | 0/60 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

