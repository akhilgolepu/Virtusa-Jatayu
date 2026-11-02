# Evaluation `r3-offtemplate-hybrid`

Split **offtemplate_dev** · mode **text** · extractor **hybrid** · n = 40 utterances · commit at start `c0ff23e`
**Source: hand-written off-template dev sentences (eval/offtemplate_dev.yaml); dev only**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.938 (P 0.941, R 0.935) |
| Record exact match | 35/51 = 0.686 |
| **Dangerous errors** | **2 of 42** (4.76%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 2 of 42 |
| **Administration-status errors** (not given, recorded as given) | **3 of 9** |
| Context errors (not-given / measurement emitted unflagged) | 3 of 9 |
| Deliberate dose anomalies flagged | 0 of 0 |
| Accepted fields with a source quote | 161 of 161 |
| Latency p50 / p95 (s) | 0.8425 / 1.8269 (n=40) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 1.000 | 1.000 | 1.000 | 49 |
| dose_value | 0.842 | 0.941 | 0.889 | 34 |
| dose_unit | 0.974 | 0.949 | 0.961 | 39 |
| route | 0.941 | 0.865 | 0.901 | 37 |
| time | 0.857 | 0.750 | 0.800 | 8 |
| procedure | 1.000 | 1.000 | 1.000 | 2 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_negation | 0.957 | 0.889 | 0/1 |
| category:hinglish | 0.900 | 0.500 | 0/5 |
| category:med_correction | 0.950 | 0.800 | 1/5 |
| category:med_messy | 0.895 | 0.364 | 0/11 |
| category:med_multi | 0.968 | 0.750 | 1/12 |
| category:time_clock | 0.954 | 0.875 | 0/8 |
| lang:en | 0.943 | 0.711 | 2/37 |
| lang:hinglish | 0.900 | 0.500 | 0/5 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `ot-m1-05` (wrong, DANGEROUS): “gave 4 mg ondansetron 10 mg metoclopramide IV”  
  output {'drug': 'ondansetron', 'dose_value': 4.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'ondansetron', 'dose_value': 4.0, 'dose_unit': 'mg'}
- `ot-cor-02` (wrong, DANGEROUS): “morphine 5 mg IM, sorry, IV”  
  output {'drug': 'morphine', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IM'}  
  expected {'drug': 'morphine', 'dose_value': 5.0, 'dose_unit': 'mg', 'route': 'IV'}
- `ot-tim-03` (wrong): “12 lead done at 10 20, then 324 mg aspirin chewed”  
  output {'drug': 'aspirin'}  
  expected {'drug': 'aspirin', 'dose_value': 324.0, 'dose_unit': 'mg', 'route': 'PO'}
- `ot-m1-02` (wrong): “ketamine 1 mg per kg IV”  
  output {'drug': 'ketamine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'ketamine', 'route': 'IV'}
- `ot-hi-04` (wrong): “adrenaline ek mg IM diya”  
  output {'drug': 'epinephrine', 'route': 'IM'}  
  expected {'drug': 'epinephrine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IM'}
