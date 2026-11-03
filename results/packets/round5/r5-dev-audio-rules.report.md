# Evaluation `r5-dev-audio-rules`

Split **dev** · mode **audio** · extractor **rules** · n = 480 utterances · commit at start `0cdc6e2`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.673 (P 0.928, R 0.528) |
| Record exact match | 181/520 = 0.348 |
| **Dangerous errors** | **1 of 440** (0.23%; strict: weight_based_dose and low_asr_confidence do not catch) |
| Dangerous errors, lenient (weight_based_dose and low_asr_confidence count as catches) | 1 of 440 |
| **Administration-status errors** (not given, recorded as given) | **2 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 5 of 80 |
| Deliberate dose anomalies flagged | 17 of 21 |
| Accepted fields with a source quote | 1004 of 1004 |
| Latency p50 / p95 (s) | 0.0002 / 0.0004 (n=480) |
| WER (normalised: numbers, units, routes; same on both sides) | 0.406 |
| WER raw (lowercase, punctuation stripped) | 0.639 |
| Drug-term recall (lexicon names in the reference) | 0.574 (n=460) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.970 | 0.691 | 0.807 | 460 |
| dose_value | 0.871 | 0.553 | 0.676 | 380 |
| dose_unit | 0.957 | 0.474 | 0.634 | 380 |
| route | 0.908 | 0.439 | 0.592 | 360 |
| time | 0.886 | 0.381 | 0.533 | 244 |
| procedure | 1.000 | 0.600 | 0.750 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.802 | 0.472 | 0/58 |
| accent:in | 0.562 | 0.238 | 1/246 |
| accent:us | 0.787 | 0.482 | 0/136 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “Knock-in 2.75 mgs, IV, 5 min ago.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-002` (miss): “glucose, three gramme, intravenously, right now” → ASR “Work was 3 grand intravenously right now.”  
  output None  
  expected {'drug': 'dextrose', 'dose_value': 3.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
- `mb07-0-006` (miss): “Mag, eight g, i.m., 10 min ago” → ASR “MAG-8G, I am 10 min ago.”  
  output None  
  expected {'drug': 'magnesium sulfate', 'dose_value': 8.0, 'dose_unit': 'g', 'route': 'IM', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-011` (miss): “vomikind, seven and a half milligrammes, into the vein, at 9 20” → ASR “Vomicind 7.5 mg into the vein at 920.”  
  output None  
  expected {'drug': 'ondansetron', 'dose_value': 7.5, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T09:20:00+05:30'}
