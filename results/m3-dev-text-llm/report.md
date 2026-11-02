# Evaluation `m3-dev-text-llm`

Split **dev** · mode **text** · extractor **llm** · n = 480 utterances · commit at start `cb16546-dirty`
**Source: template-generated; extractor and generator share a lexicon; not a headline number**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.897 (P 0.893, R 0.900) |
| Record exact match | 401/520 = 0.771 |
| **Dangerous errors** | **3 of 440** (0.68%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 3 of 440 |
| Context errors (not-given / measurement emitted unflagged) | 37 of 80 |
| Deliberate dose anomalies flagged | 20 of 21 |
| Accepted fields with a source quote | 1683 of 1683 |
| Latency p50 / p95 (s) | 1.6717 / 3.2198 (n=480) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.890 | 0.876 | 0.883 | 460 |
| dose_value | 0.862 | 0.937 | 0.898 | 380 |
| dose_unit | 0.903 | 0.953 | 0.927 | 380 |
| route | 0.895 | 0.967 | 0.929 | 360 |
| time | 0.931 | 0.832 | 0.879 | 244 |
| procedure | 1.000 | 0.383 | 0.554 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_measurement | 0.000 | 0.000 | 0/0 |
| category:context_negation | 0.949 | 0.925 | 0/0 |
| category:hinglish | 0.959 | 0.950 | 0/60 |
| category:med_basic | 0.961 | 0.900 | 0/40 |
| category:med_correction | 0.739 | 0.883 | 3/60 |
| category:med_incomplete | 0.940 | 0.825 | 0/40 |
| category:med_messy | 0.948 | 0.933 | 0/60 |
| category:med_multi | 0.985 | 0.975 | 0/80 |
| category:procedure | 0.404 | 0.233 | 0/60 |
| category:time_clock | 0.961 | 0.925 | 0/40 |
| lang:en | 0.888 | 0.748 | 3/380 |
| lang:hinglish | 0.959 | 0.950 | 0/60 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mc01-0-004` (wrong, DANGEROUS): “Tranexamic acid 1.5, no sorry, two gram intraosseous”  
  output {'drug': 'tranexamic acid', 'dose_value': 1.5, 'dose_unit': 'g', 'route': 'IO'}  
  expected {'drug': 'tranexamic acid', 'dose_value': 2.0, 'dose_unit': 'g', 'route': 'IO'}
- `mc01-1-001` (wrong, DANGEROUS): “given Nitroglycerin 0.8, no sorry, .4 mgs under the tongue ten minutes ago”  
  output {'drug': 'nitroglycerin', 'dose_value': 0.8, 'dose_unit': 'mg', 'route': 'SL', 'time': '2026-10-31T10:35:00+05:30'}  
  expected {'drug': 'nitroglycerin', 'dose_value': 0.4, 'dose_unit': 'mg', 'route': 'SL', 'time': '2026-10-31T10:35:00+05:30'}
- `mc01-1-016` (wrong, DANGEROUS): “given Cacl2 0.5, sorry, one gram ivp right now”  
  output {'drug': 'calcium chloride', 'dose_value': 0.5, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}  
  expected {'drug': 'calcium chloride', 'dose_value': 1.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
- `mb07-0-008` (miss): “o2, one lpm, inhaled, ten minutes ago”  
  output None  
  expected {'drug': 'oxygen', 'dose_value': 1.0, 'dose_unit': 'L/min', 'route': 'INH', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-1-003` (miss): “Oxygen eight lpm given mdi at 10:16”  
  output None  
  expected {'drug': 'oxygen', 'dose_value': 8.0, 'dose_unit': 'L/min', 'route': 'INH', 'time': '2026-10-31T10:16:00+05:30'}
