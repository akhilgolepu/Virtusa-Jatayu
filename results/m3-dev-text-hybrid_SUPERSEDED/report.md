# Evaluation `m3-dev-text-hybrid`

Split **dev** · mode **text** · extractor **hybrid** · n = 480 utterances · commit `b966e83`


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.978 (P 0.976, R 0.980) |
| Record exact match | 443/520 = 0.852 |
| **Dangerous errors** | **3 of 440** (0.68%) |
| Context errors (not-given / measurement emitted unflagged) | 20 of 80 |
| Deliberate dose anomalies flagged | 23 of 23 |
| Accepted fields with a source quote | 1678 of 1678 |
| Latency p50 / p95 (s) | 1.1191 / 2.0002 (n=480) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 1.000 | 1.000 | 1.000 | 460 |
| dose_value | 0.893 | 0.984 | 0.936 | 380 |
| dose_unit | 1.000 | 0.997 | 0.999 | 380 |
| route | 1.000 | 1.000 | 1.000 | 360 |
| time | 1.000 | 0.870 | 0.930 | 238 |
| procedure | 1.000 | 1.000 | 1.000 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| category:context_measurement | 0.667 | 0.000 | 0/0 |
| category:context_negation | 1.000 | 1.000 | 0/0 |
| category:hinglish | 1.000 | 1.000 | 0/60 |
| category:med_basic | 1.000 | 1.000 | 0/40 |
| category:med_correction | 0.980 | 0.917 | 3/60 |
| category:med_incomplete | 1.000 | 1.000 | 0/40 |
| category:med_messy | 1.000 | 1.000 | 0/60 |
| category:med_multi | 0.998 | 0.988 | 0/80 |
| category:procedure | 0.795 | 0.483 | 0/60 |
| category:time_clock | 1.000 | 1.000 | 0/40 |
| lang:en | 0.975 | 0.833 | 3/380 |
| lang:hinglish | 1.000 | 1.000 | 0/60 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mc01-1-000` (wrong, DANGEROUS): “given magnesium sulfate 2, no, four grammes iv push two min ago”  
  output {'drug': 'magnesium sulfate', 'dose_value': 2.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:43:00+05:30'}  
  expected {'drug': 'magnesium sulfate', 'dose_value': 4.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:43:00+05:30'}
- `mc01-1-008` (wrong, DANGEROUS): “administered pcm 500, no, six hundred fifty mg orally ten min ago”  
  output {'drug': 'paracetamol', 'dose_value': 500.0, 'dose_unit': 'mg', 'route': 'PO', 'time': '2026-10-31T10:35:00+05:30'}  
  expected {'drug': 'paracetamol', 'dose_value': 650.0, 'dose_unit': 'mg', 'route': 'PO', 'time': '2026-10-31T10:35:00+05:30'}
- `mc01-2-002` (wrong, DANGEROUS): “one hundred, actually, fifty milligrammes ketamine nasal”  
  output {'drug': 'ketamine', 'dose_value': 100.0, 'dose_unit': 'mg', 'route': 'IN'}  
  expected {'drug': 'ketamine', 'dose_value': 50.0, 'dose_unit': 'mg', 'route': 'IN'}
- `mx07-1-015` (wrong): “right now o2 15 liters per minute inhaler, one minutes ago adenoject 6 milligrammes into the vein”  
  output {'drug': 'oxygen', 'route': 'INH', 'time': '2026-10-31T10:45:00+05:30'}  
  expected {'drug': 'oxygen', 'dose_value': 15.0, 'dose_unit': 'L/min', 'route': 'INH', 'time': '2026-10-31T10:45:00+05:30'}
- `mc01-0-009` (wrong): “cacl 2, I mean, 1 grammes i.v.”  
  output {'drug': 'calcium chloride', 'dose_value': 2.0, 'dose_unit': 'g', 'route': 'IV'}  
  expected {'drug': 'calcium chloride', 'dose_value': 1.0, 'dose_unit': 'g', 'route': 'IV'}
