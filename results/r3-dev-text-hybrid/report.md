# Evaluation `r3-dev-text-hybrid`

Split **dev** · mode **text** · extractor **hybrid** · n = 480 utterances · commit at start `c0ff23e`
**Source: template-generated; extractor and generator share a lexicon; not a headline number**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.988 (P 0.996, R 0.980) |
| Record exact match | 482/520 = 0.927 |
| **Dangerous errors** | **5 of 440** (1.14%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 5 of 440 |
| **Administration-status errors** (not given, recorded as given) | **0 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 0 of 80 |
| Deliberate dose anomalies flagged | 21 of 21 |
| Accepted fields with a source quote | 1680 of 1680 |
| Latency p50 / p95 (s) | 0.8442 / 1.7885 (n=480) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 1.000 | 1.000 | 1.000 | 460 |
| dose_value | 0.982 | 0.982 | 0.982 | 380 |
| dose_unit | 1.000 | 1.000 | 1.000 | 380 |
| route | 1.000 | 1.000 | 1.000 | 360 |
| time | 1.000 | 0.873 | 0.932 | 244 |
| procedure | 1.000 | 1.000 | 1.000 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_measurement | 1.000 | 1.000 | 0/0 |
| category:context_negation | 1.000 | 1.000 | 0/0 |
| category:hinglish | 1.000 | 1.000 | 0/60 |
| category:med_basic | 1.000 | 1.000 | 0/40 |
| category:med_correction | 0.972 | 0.883 | 5/60 |
| category:med_incomplete | 1.000 | 1.000 | 0/40 |
| category:med_messy | 1.000 | 1.000 | 0/60 |
| category:med_multi | 1.000 | 1.000 | 0/80 |
| category:procedure | 0.795 | 0.483 | 0/60 |
| category:time_clock | 1.000 | 1.000 | 0/40 |
| lang:en | 0.986 | 0.917 | 5/380 |
| lang:hinglish | 1.000 | 1.000 | 0/60 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mc01-0-003` (wrong, DANGEROUS): “amio 250, no, three hundred milligrams intraosseous”  
  output {'drug': 'amiodarone', 'dose_value': 250.0, 'dose_unit': 'mg', 'route': 'IO'}  
  expected {'drug': 'amiodarone', 'dose_value': 300.0, 'dose_unit': 'mg', 'route': 'IO'}
- `mc01-0-005` (wrong, DANGEROUS): “norepinephrine 2.5, actually, 6 mics iv push”  
  output {'drug': 'norepinephrine', 'dose_value': 2.5, 'dose_unit': 'mcg', 'route': 'IV'}  
  expected {'drug': 'norepinephrine', 'dose_value': 6.0, 'dose_unit': 'mcg', 'route': 'IV'}
- `mc01-1-000` (wrong, DANGEROUS): “given magnesium sulfate 1.5, no, two grammes iv push two min ago”  
  output {'drug': 'magnesium sulfate', 'dose_value': 1.5, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:43:00+05:30'}  
  expected {'drug': 'magnesium sulfate', 'dose_value': 2.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:43:00+05:30'}
- `mc01-1-015` (wrong, DANGEROUS): “given morphine 1.5, no, 8 milligramme intramuscularly just now”  
  output {'drug': 'morphine', 'dose_value': 1.5, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'}  
  expected {'drug': 'morphine', 'dose_value': 8.0, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'}
- `mc01-1-016` (wrong, DANGEROUS): “given Cacl2 0.5, sorry, one gram ivp right now”  
  output {'drug': 'calcium chloride', 'dose_value': 0.5, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}  
  expected {'drug': 'calcium chloride', 'dose_value': 1.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
