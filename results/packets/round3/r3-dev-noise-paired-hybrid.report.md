# Evaluation `r3-dev-noise-paired-hybrid`

Split **dev** · mode **noisy** · extractor **hybrid** · n = 160 utterances · commit at start `c0ff23e`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.609 (P 0.933, R 0.451) |
| Record exact match | 195/480 = 0.406 |
| **Dangerous errors** | **3 of 240** (1.25%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 3 of 240 |
| **Administration-status errors** (not given, recorded as given) | **13 of 120** |
| Context errors (not-given / measurement emitted unflagged) | 30 of 240 |
| Deliberate dose anomalies flagged | 4 of 9 |
| Accepted fields with a source quote | 786 of 786 |
| Latency p50 / p95 (s) | 0.6889 / 1.0753 (n=640) |
| WER (normalised: numbers, units, routes; same on both sides) | 0.463 |
| WER raw (lowercase, punctuation stripped) | 0.683 |
| Drug-term recall (lexicon names in the reference) | 0.600 (n=640) |

## Noise curve (entity F1)

| SNR dB | F1 |
|---|---|
| clean | 0.653 |
| 20 | 0.633 |
| 10 | 0.624 |
| 5 | 0.567 |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.955 | 0.623 | 0.754 | 480 |
| dose_value | 0.861 | 0.431 | 0.574 | 360 |
| dose_unit | 0.965 | 0.383 | 0.549 | 360 |
| route | 0.909 | 0.222 | 0.357 | 180 |
| time | 1.000 | 0.363 | 0.532 | 102 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.657 | 0.516 | 0/8 |
| accent:in | 0.580 | 0.325 | 4/284 |
| accent:us | 0.744 | 0.649 | 0/28 |
| snr:10 | 0.624 | 0.431 | 1/80 |
| snr:20 | 0.633 | 0.425 | 2/80 |
| snr:5 | 0.567 | 0.362 | 0/80 |
| snr:clean | 0.653 | 0.456 | 1/80 |

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
- `mb07-0-018` (wrong, DANGEROUS): “atropine, 60 milligram, i.v., ten mins ago” → ASR “Atropine, 6 milligram, IV, 10 minutes ago.”  
  output {'drug': 'atropine', 'dose_value': 6.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'}  
  expected {'drug': 'atropine', 'dose_value': 60.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “Knock in 2.75 mgs, IV, five minutes ago.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “Knock-in 2.75 mgs, IV, five minutes ago.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
