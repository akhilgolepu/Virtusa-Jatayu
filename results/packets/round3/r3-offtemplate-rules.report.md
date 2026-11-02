# Evaluation `r3-offtemplate-rules`

Split **offtemplate_dev** · mode **text** · extractor **rules** · n = 40 utterances · commit at start `f0ae275`
**Source: hand-written off-template dev sentences (eval/offtemplate_dev.yaml); dev only**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.929 (P 0.924, R 0.935) |
| Record exact match | 33/51 = 0.647 |
| **Dangerous errors** | **2 of 42** (4.76%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 2 of 42 |
| **Administration-status errors** (not given, recorded as given) | **3 of 9** |
| Context errors (not-given / measurement emitted unflagged) | 3 of 9 |
| Deliberate dose anomalies flagged | 0 of 0 |
| Accepted fields with a source quote | 161 of 161 |
| Latency p50 / p95 (s) | 0.0001 / 0.0003 (n=40) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 1.000 | 1.000 | 1.000 | 49 |
| dose_value | 0.842 | 0.941 | 0.889 | 34 |
| dose_unit | 0.974 | 0.949 | 0.961 | 39 |
| route | 0.941 | 0.865 | 0.901 | 37 |
| time | 0.600 | 0.750 | 0.667 | 8 |
| procedure | 1.000 | 1.000 | 1.000 | 2 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_negation | 0.957 | 0.889 | 0/1 |
| category:hinglish | 0.900 | 0.500 | 0/5 |
| category:med_correction | 0.900 | 0.600 | 2/5 |
| category:med_messy | 0.895 | 0.364 | 0/11 |
| category:med_multi | 0.967 | 0.833 | 0/12 |
| category:time_clock | 0.943 | 0.625 | 0/8 |
| lang:en | 0.933 | 0.667 | 2/37 |
| lang:hinglish | 0.900 | 0.500 | 0/5 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `ot-cor-02` (wrong, DANGEROUS): “morphine 5 mg IM, sorry, IV”  
  output {'drug': 'morphine', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IM'}  
  expected {'drug': 'morphine', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IV'}
- `ot-cor-05` (wrong, DANGEROUS): “midazolam 5 mg IV, scratch that, IM”  
  output {'drug': 'midazolam', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'midazolam', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IM'}
- `ot-m1-02` (wrong): “ketamine 1 mg per kg IV”  
  output {'drug': 'ketamine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'ketamine', 'route': 'IV'}
- `ot-m1-05` (wrong): “gave 4 mg ondansetron 10 mg metoclopramide IV”  
  output {'drug': 'metoclopramide', 'route': 'IV'}  
  expected {'drug': 'metoclopramide', 'dose_value': 10.0, 'dose_unit': 'mg', 'route': 'IV'}
- `ot-hi-04` (wrong): “adrenaline ek mg IM diya”  
  output {'drug': 'epinephrine', 'route': 'IM'}  
  expected {'drug': 'epinephrine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IM'}
