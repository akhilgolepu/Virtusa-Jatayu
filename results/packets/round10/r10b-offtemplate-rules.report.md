# Evaluation `r10b-offtemplate-rules`

Split **offtemplate_dev** · mode **text** · extractor **rules** · n = 56 utterances · commit at start `8761138`
**Source: hand-written off-template dev sentences (eval/offtemplate_dev.yaml); dev only**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.952 (P 0.946, R 0.958) |
| Record exact match | 54/71 = 0.761 |
| **Dangerous errors (headline, round 10): wrong drug, dose, unit, route or status with no flag that must be ticked** | **3 of 71** (4.23%; uncaught by kind: {'wrong dose/unit/route': 3}; all such errors: {'wrong dose/unit/route': 8, 'omitted dose/unit/route (shown as not stated; not counted)': 4, 'status (not given recorded as given)': 3}) |
| Dangerous errors, matched-drug only (pre-round-10 metric, secondary; a wrong drug is not counted) | 2 of 59 (3.39%; strict: weight_based_dose and low_asr_confidence do not catch) |
| Dangerous errors, lenient (weight_based_dose and low_asr_confidence count as catches) | 2 of 59 |
| **Administration-status errors** (not given, recorded as given) | **3 of 12** |
| Context errors (not-given / measurement emitted unflagged) | 3 of 12 |
| Deliberate dose anomalies flagged | 0 of 0 |
| Accepted fields with a source quote | 230 of 230 |
| Latency p50 / p95 (s) | 0.0002 / 0.0004 (n=56) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 1.000 | 1.000 | 1.000 | 65 |
| dose_value | 0.889 | 0.960 | 0.923 | 50 |
| dose_unit | 0.982 | 0.964 | 0.973 | 55 |
| route | 0.961 | 0.924 | 0.942 | 53 |
| time | 0.600 | 0.750 | 0.667 | 8 |
| procedure | 1.000 | 1.000 | 1.000 | 6 |

## Groups

| Group | Entity F1 | Exact match | Dangerous (headline) | Dangerous, matched-drug only |
|---|---|---|---|---|
| category:context_negation | 1.000 | 1.000 | 0/13 | 0/3 |
| category:hinglish | 0.900 | 0.500 | 0/6 | 0/5 |
| category:med_basic | 1.000 | 1.000 | 0/16 | 0/15 |
| category:med_correction | 0.900 | 0.600 | 2/5 | 2/5 |
| category:med_messy | 0.895 | 0.364 | 1/11 | 0/11 |
| category:med_multi | 0.967 | 0.833 | 0/12 | 0/12 |
| category:time_clock | 0.943 | 0.625 | 0/8 | 0/8 |
| lang:en | 0.957 | 0.785 | 3/65 | 2/54 |
| lang:hinglish | 0.900 | 0.500 | 0/6 | 0/5 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `ot-m1-02` (wrong): “ketamine 1 mg per kg IV”  
  output {'drug': 'ketamine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'ketamine', 'route': 'IV'}
- `ot-cor-02` (wrong, DANGEROUS): “morphine 5 mg IM, sorry, IV”  
  output {'drug': 'morphine', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IM'}  
  expected {'drug': 'morphine', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IV'}
- `ot-cor-05` (wrong, DANGEROUS): “midazolam 5 mg IV, scratch that, IM”  
  output {'drug': 'midazolam', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'midazolam', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IM'}
- `ot-m1-05` (wrong): “gave 4 mg ondansetron 10 mg metoclopramide IV”  
  output {'drug': 'metoclopramide', 'route': 'IV'}  
  expected {'drug': 'metoclopramide', 'dose_value': 10.0, 'dose_unit': 'mg', 'route': 'IV'}
- `ot-hi-04` (wrong): “adrenaline ek mg IM diya”  
  output {'drug': 'epinephrine', 'route': 'IM'}  
  expected {'drug': 'epinephrine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IM'}
