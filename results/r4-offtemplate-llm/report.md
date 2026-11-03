# Evaluation `r4-offtemplate-llm`

Split **offtemplate_dev** · mode **text** · extractor **llm** · n = 54 utterances · commit at start `212d5e3`
**Source: hand-written off-template dev sentences (eval/offtemplate_dev.yaml); dev only**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.894 (P 0.853, R 0.939) |
| Record exact match | 47/66 = 0.712 |
| **Dangerous errors** | **1 of 57** (1.75%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 1 of 57 |
| **Administration-status errors** (not given, recorded as given) | **3 of 9** |
| Context errors (not-given / measurement emitted unflagged) | 3 of 9 |
| Deliberate dose anomalies flagged | 0 of 0 |
| Accepted fields with a source quote | 245 of 245 |
| Latency p50 / p95 (s) | 1.9402 / 3.6118 (n=54) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.866 | 0.906 | 0.885 | 64 |
| dose_value | 0.857 | 0.980 | 0.914 | 49 |
| dose_unit | 0.885 | 1.000 | 0.939 | 54 |
| route | 0.814 | 0.923 | 0.865 | 52 |
| time | 0.714 | 0.625 | 0.667 | 8 |
| procedure | 1.000 | 1.000 | 1.000 | 2 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_negation | 0.667 | 0.333 | 0/1 |
| category:hinglish | 0.900 | 0.333 | 0/5 |
| category:med_basic | 0.992 | 0.933 | 0/15 |
| category:med_correction | 0.727 | 1.000 | 0/5 |
| category:med_messy | 0.791 | 0.818 | 0/11 |
| category:med_multi | 0.958 | 0.667 | 1/12 |
| category:time_clock | 0.955 | 0.750 | 0/8 |
| lang:en | 0.893 | 0.750 | 1/52 |
| lang:hinglish | 0.900 | 0.333 | 0/5 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `ot-m1-05` (wrong, DANGEROUS): “gave 4 mg ondansetron 10 mg metoclopramide IV”  
  output {'drug': 'ondansetron', 'dose_value': 4.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'ondansetron', 'dose_value': 4.0, 'dose_unit': 'mg'}
- `ot-tim-03` (wrong): “12 lead done at 10 20, then 324 mg aspirin chewed”  
  output {'drug': 'aspirin', 'dose_value': 324.0, 'dose_unit': 'mg', 'time': '2026-11-02T10:20:00+05:30'}  
  expected {'drug': 'aspirin', 'dose_value': 324.0, 'dose_unit': 'mg', 'route': 'PO'}
- `ot-m1-02` (wrong): “ketamine 1 mg per kg IV”  
  output {'drug': 'ketamine', 'dose_value': 1.0, 'route': 'IV'}  
  expected {'drug': 'ketamine', 'route': 'IV'}
- `ot-m1-03` (wrong): “adrenaline 1 mg IV, then another 1 mg two minutes later”  
  output {'drug': 'epinephrine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'epinephrine', 'dose_value': 1.0, 'dose_unit': 'mg'}
- `ot-neg-02` (miss): “no aspirin, patient already took it at home”  
  output None  
  expected {'drug': 'aspirin'}
