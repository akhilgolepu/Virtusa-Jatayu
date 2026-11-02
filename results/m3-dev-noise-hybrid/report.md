# Evaluation `m3-dev-noise-hybrid`

Split **dev** · mode **noisy** · extractor **hybrid** · n = 160 utterances · commit at start `cb16546-dirty`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.600 (P 0.936, R 0.441) |
| Record exact match | 183/480 = 0.381 |
| **Dangerous errors** | **2 of 240** (0.83%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 2 of 240 |
| Context errors (not-given / measurement emitted unflagged) | 62 of 240 |
| Deliberate dose anomalies flagged | 5 of 9 |
| Accepted fields with a source quote | 776 of 776 |
| Latency p50 / p95 (s) | 0.9218 / 2.0918 (n=480) |
| WER | 0.696 |
| Drug-term recall | 0.596 |

## Noise curve (entity F1)

| SNR dB | F1 |
|---|---|
| 20 | 0.636 |
| 10 | 0.611 |
| 5 | 0.550 |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.950 | 0.633 | 0.760 | 480 |
| dose_value | 0.874 | 0.442 | 0.587 | 360 |
| dose_unit | 0.971 | 0.372 | 0.538 | 360 |
| route | 0.933 | 0.156 | 0.267 | 180 |
| time | 1.000 | 0.284 | 0.443 | 102 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.640 | 0.479 | 0/6 |
| accent:in | 0.562 | 0.277 | 2/213 |
| accent:us | 0.716 | 0.640 | 0/21 |
| snr:10 | 0.611 | 0.400 | 1/80 |
| snr:20 | 0.636 | 0.400 | 1/80 |
| snr:5 | 0.550 | 0.344 | 0/80 |

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
- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “NAKAN 0.75 MGS, ROMAN IV, 5 MINUTE GO”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “napkin 0.75 MGS, roman IV, five minute go.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-002` (miss): “glucose, three gramme, intravenously, right now” → ASR “Work was 3 grand intravenously right now.”  
  output None  
  expected {'drug': 'dextrose', 'dose_value': 3.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
