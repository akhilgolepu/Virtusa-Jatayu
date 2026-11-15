# Evaluation `r9-dev-text-hybrid-after`

Split **dev** · mode **text** · extractor **hybrid** · n = 480 utterances · commit at start `1fa9301`
**Source: template-generated; extractor and generator share a lexicon; not a headline number**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.992 (P 1.000, R 0.984) |
| Record exact match | 489/520 = 0.940 |
| **Dangerous errors** | **0 of 440** (0.00%; strict: weight_based_dose and low_asr_confidence do not catch) |
| Dangerous errors, lenient (weight_based_dose and low_asr_confidence count as catches) | 0 of 440 |
| **Administration-status errors** (not given, recorded as given) | **0 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 0 of 80 |
| Deliberate dose anomalies flagged | 21 of 21 |
| Accepted fields with a source quote | 1680 of 1680 |
| Latency p50 / p95 (s) | 0.9816 / 2.4119 (n=480) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 1.000 | 1.000 | 1.000 | 460 |
| dose_value | 1.000 | 1.000 | 1.000 | 380 |
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
| category:med_correction | 1.000 | 1.000 | 0/60 |
| category:med_incomplete | 1.000 | 1.000 | 0/40 |
| category:med_messy | 1.000 | 1.000 | 0/60 |
| category:med_multi | 1.000 | 1.000 | 0/80 |
| category:procedure | 0.795 | 0.483 | 0/60 |
| category:time_clock | 1.000 | 1.000 | 0/40 |
| lang:en | 0.991 | 0.933 | 0/380 |
| lang:hinglish | 1.000 | 1.000 | 0/60 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `pr01-0-000` (wrong): “started cpr at ten twenty”  
  output {'procedure': 'cpr'}  
  expected {'procedure': 'cpr', 'time': '2026-10-31T10:20:00+05:30'}
- `pr01-0-001` (wrong): “started cardiopulmonary resuscitation 5 min ago”  
  output {'procedure': 'cpr'}  
  expected {'procedure': 'cpr', 'time': '2026-10-31T10:40:00+05:30'}
- `pr01-0-002` (wrong): “started Cpr a minute ago”  
  output {'procedure': 'cpr'}  
  expected {'procedure': 'cpr', 'time': '2026-10-31T10:44:00+05:30'}
- `pr01-0-003` (wrong): “started chest compressions at 10:28”  
  output {'procedure': 'cpr'}  
  expected {'procedure': 'cpr', 'time': '2026-10-31T10:28:00+05:30'}
- `pr01-0-005` (wrong): “started cpr 1 minutes ago”  
  output {'procedure': 'cpr'}  
  expected {'procedure': 'cpr', 'time': '2026-10-31T10:44:00+05:30'}
