# Evaluation `m3-dev-text-llm`

Split **dev** · mode **text** · extractor **llm** · n = 480 utterances · commit `b966e83`


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.874 (P 0.868, R 0.880) |
| Record exact match | 391/520 = 0.752 |
| **Dangerous errors** | **1 of 440** (0.23%) |
| Context errors (not-given / measurement emitted unflagged) | 37 of 80 |
| Deliberate dose anomalies flagged | 21 of 23 |
| Accepted fields with a source quote | 1698 of 1698 |
| Latency p50 / p95 (s) | 1.9549 / 3.6993 (n=480) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.868 | 0.861 | 0.865 | 460 |
| dose_value | 0.843 | 0.918 | 0.879 | 380 |
| dose_unit | 0.869 | 0.921 | 0.894 | 380 |
| route | 0.857 | 0.947 | 0.900 | 360 |
| time | 0.924 | 0.815 | 0.866 | 238 |
| procedure | 1.000 | 0.383 | 0.554 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_measurement | 0.000 | 0.000 | 0/0 |
| category:context_negation | 0.943 | 0.875 | 0/0 |
| category:hinglish | 0.911 | 0.883 | 0/60 |
| category:med_basic | 0.919 | 0.850 | 0/40 |
| category:med_correction | 0.698 | 0.900 | 1/60 |
| category:med_incomplete | 0.957 | 0.825 | 0/40 |
| category:med_messy | 0.956 | 0.917 | 0/60 |
| category:med_multi | 0.981 | 0.963 | 0/80 |
| category:procedure | 0.404 | 0.233 | 0/60 |
| category:time_clock | 0.923 | 0.900 | 0/40 |
| lang:en | 0.869 | 0.735 | 1/380 |
| lang:hinglish | 0.911 | 0.883 | 0/60 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mc01-1-003` (wrong, DANGEROUS): “administered Valium twenty, no, 10 milligrammes rectally”  
  output {'drug': 'diazepam', 'dose_value': 20.0, 'dose_unit': 'mg', 'route': 'PR'}  
  expected {'drug': 'diazepam', 'dose_value': 10.0, 'dose_unit': 'mg', 'route': 'PR'}
- `mb07-0-006` (miss): “Mag, four g, i.v., 10 min ago”  
  output None  
  expected {'drug': 'magnesium sulfate', 'dose_value': 4.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-008` (miss): “o2, two lpm, inhaled, ten minutes ago”  
  output None  
  expected {'drug': 'oxygen', 'dose_value': 2.0, 'dose_unit': 'L/min', 'route': 'INH', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-011` (miss): “vomikind, four milligrammes, by mouth, 2 minutes ago”  
  output None  
  expected {'drug': 'ondansetron', 'dose_value': 4.0, 'dose_unit': 'mg', 'route': 'PO', 'time': '2026-10-31T10:43:00+05:30'}
- `mb07-1-007` (miss): “fortwin 30 mgs given iv push a minute ago”  
  output None  
  expected {'drug': 'pentazocine', 'dose_value': 30.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:44:00+05:30'}
