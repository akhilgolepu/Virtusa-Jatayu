# Evaluation `r3-dev-audio-hybrid`

Split **dev** · mode **audio** · extractor **hybrid** · n = 480 utterances · commit at start `c0ff23e`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.633 (P 0.922, R 0.482) |
| Record exact match | 161/520 = 0.310 |
| **Dangerous errors** | **3 of 440** (0.68%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 3 of 440 |
| **Administration-status errors** (not given, recorded as given) | **4 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 10 of 80 |
| Deliberate dose anomalies flagged | 16 of 21 |
| Accepted fields with a source quote | 937 of 937 |
| Latency p50 / p95 (s) | 0.7336 / 1.3142 (n=480) |
| WER (normalised: numbers, units, routes; same on both sides) | 0.402 |
| WER raw (lowercase, punctuation stripped) | 0.634 |
| Drug-term recall (lexicon names in the reference) | 0.574 (n=460) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.977 | 0.633 | 0.768 | 460 |
| dose_value | 0.839 | 0.492 | 0.620 | 380 |
| dose_unit | 0.946 | 0.461 | 0.620 | 380 |
| route | 0.918 | 0.403 | 0.560 | 360 |
| time | 0.871 | 0.303 | 0.450 | 244 |
| procedure | 1.000 | 0.600 | 0.750 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.794 | 0.444 | 1/58 |
| accent:in | 0.523 | 0.220 | 1/246 |
| accent:us | 0.729 | 0.404 | 1/136 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mc01-1-005` (wrong, DANGEROUS): “gave fentanyl one hundred, no, seventy five microgram intramuscularly one mins ago” → ASR “Gave fentanyl 100, no 75 microgram intramuscularly one minutes ago.”  
  output {'drug': 'fentanyl', 'dose_value': 100.0, 'dose_unit': 'mcg', 'route': 'IM', 'time': '2026-10-31T10:44:00+05:30'}  
  expected {'drug': 'fentanyl', 'dose_value': 75.0, 'dose_unit': 'mcg', 'route': 'IM', 'time': '2026-10-31T10:44:00+05:30'}
- `mc01-1-015` (wrong, DANGEROUS): “given morphine 1.5, no, 8 milligramme intramuscularly just now” → ASR “given morphine 1.5, no, 8 milligram intramuscularly just now.”  
  output {'drug': 'morphine', 'dose_value': 1.5, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'}  
  expected {'drug': 'morphine', 'dose_value': 8.0, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'}
- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “Knock-in 2.75 mgs, IV, 5 min ago.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-002` (miss): “glucose, three gramme, intravenously, right now” → ASR “Work was 3 grand intravenously right now.”  
  output None  
  expected {'drug': 'dextrose', 'dose_value': 3.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
