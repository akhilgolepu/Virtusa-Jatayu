# Evaluation `m3-dev-audio-hybrid`

Split **dev** · mode **audio** · extractor **hybrid** · n = 480 utterances · commit `b966e83`


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.575 (P 0.915, R 0.419) |
| Record exact match | 136/520 = 0.262 |
| **Dangerous errors** | **6 of 440** (1.36%) |
| Context errors (not-given / measurement emitted unflagged) | 24 of 80 |
| Deliberate dose anomalies flagged | 13 of 23 |
| Accepted fields with a source quote | 823 of 823 |
| Latency p50 / p95 (s) | 0.9749 / 2.6908 (n=480) |
| WER | 0.654 |
| Drug-term recall | 0.546 |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.985 | 0.587 | 0.736 | 460 |
| dose_value | 0.808 | 0.410 | 0.544 | 380 |
| dose_unit | 0.956 | 0.400 | 0.564 | 380 |
| route | 0.911 | 0.314 | 0.467 | 360 |
| time | 0.811 | 0.252 | 0.385 | 238 |
| procedure | 1.000 | 0.600 | 0.750 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.709 | 0.361 | 2/58 |
| accent:in | 0.512 | 0.188 | 2/246 |
| accent:us | 0.616 | 0.343 | 2/136 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `tc01-1-014` (wrong, DANGEROUS): “morphine sulfate 4 mg iv at nine eleven” → ASR “morphine, sulfate, IV, mg, roman, IV, at 9, 11.”  
  output {'drug': 'morphine', 'dose_value': 9.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'morphine', 'dose_value': 4.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T09:11:00+05:30'}
- `mm02-2-001` (wrong, DANGEROUS): “um 4 milligrams uh Morphine iv” → ASR “im 4mg im morphine roman 4.”  
  output {'drug': 'morphine', 'dose_value': 4.0, 'dose_unit': 'mg', 'route': 'IM'}  
  expected {'drug': 'morphine', 'dose_value': 4.0, 'dose_unit': 'mg', 'route': 'IV'}
- `mx07-1-014` (wrong, DANGEROUS): “a minute ago Epinephrine 1 milligram intraosseous, at ten thirty three hydrocort two hundred microgram intravenous” → ASR “A minute ago epinephrine one milligram introsius, a 1033 hydrochlorate 200 microgram intravenous.”  
  output {'drug': 'epinephrine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:44:00+05:30'}  
  expected {'drug': 'epinephrine', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IO', 'time': '2026-10-31T10:44:00+05:30'}
- `mc01-0-000` (wrong, DANGEROUS): “furosemide 20, sorry, eighty mg intravenous” → ASR “Furosemide 20, sari, 80 mg unit, intravenous.”  
  output {'drug': 'furosemide', 'dose_value': 20.0, 'dose_unit': 'mg', 'route': 'IV'}  
  expected {'drug': 'furosemide', 'dose_value': 80.0, 'dose_unit': 'mg', 'route': 'IV'}
