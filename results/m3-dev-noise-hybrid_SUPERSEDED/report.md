# Evaluation `m3-dev-noise-hybrid`

Split **dev** · mode **noisy** · extractor **hybrid** · n = 160 utterances · commit `b966e83`


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.594 (P 0.953, R 0.432) |
| Record exact match | 178/480 = 0.371 |
| **Dangerous errors** | **2 of 240** (0.83%) |
| Context errors (not-given / measurement emitted unflagged) | 65 of 240 |
| Deliberate dose anomalies flagged | 0 of 9 |
| Accepted fields with a source quote | 736 of 736 |
| Latency p50 / p95 (s) | 1.001 / 1.9288 (n=480) |
| WER | 0.688 |
| Drug-term recall | 0.577 |

## Noise curve (entity F1)

| SNR dB | F1 |
|---|---|
| 20 | 0.616 |
| 10 | 0.612 |
| 5 | 0.553 |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.967 | 0.602 | 0.742 | 480 |
| dose_value | 0.911 | 0.428 | 0.582 | 360 |
| dose_unit | 0.969 | 0.347 | 0.511 | 360 |
| route | 0.912 | 0.172 | 0.290 | 180 |
| time | 1.000 | 0.400 | 0.571 | 105 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.747 | 0.562 | 0/6 |
| accent:in | 0.545 | 0.259 | 2/213 |
| accent:us | 0.709 | 0.613 | 0/21 |
| snr:10 | 0.612 | 0.375 | 1/80 |
| snr:20 | 0.616 | 0.400 | 1/80 |
| snr:5 | 0.553 | 0.338 | 0/80 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mb07-0-001` (miss): “narcan, 0.4 mgs, im, 5 min ago” → ASR “Knock-in, 0.4 mgs in five minute go.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.4, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-001` (miss): “narcan, 0.4 mgs, im, 5 min ago” → ASR “knock in 0.4 mgs in five minutes ago.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.4, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-002` (miss): “glucose, twenty five milligramme, intravenously, right now” → ASR “Cocols 25mg intravenously right now.”  
  output None  
  expected {'drug': 'dextrose', 'dose_value': 25.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
