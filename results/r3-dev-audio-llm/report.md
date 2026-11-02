# Evaluation `r3-dev-audio-llm`

Split **dev** · mode **audio** · extractor **llm** · n = 480 utterances · commit at start `c0ff23e`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.526 (P 0.781, R 0.397) |
| Record exact match | 86/520 = 0.165 |
| **Dangerous errors** | **0 of 440** (0.00%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 0 of 440 |
| **Administration-status errors** (not given, recorded as given) | **21 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 25 of 80 |
| Deliberate dose anomalies flagged | 14 of 21 |
| Accepted fields with a source quote | 872 of 872 |
| Latency p50 / p95 (s) | 1.9031 / 3.5324 (n=480) |
| WER (normalised: numbers, units, routes; same on both sides) | 0.402 |
| WER raw (lowercase, punctuation stripped) | 0.634 |
| Drug-term recall (lexicon names in the reference) | 0.574 (n=460) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.808 | 0.530 | 0.640 | 460 |
| dose_value | 0.697 | 0.442 | 0.541 | 380 |
| dose_unit | 0.817 | 0.305 | 0.444 | 380 |
| route | 0.786 | 0.367 | 0.500 | 360 |
| time | 0.820 | 0.299 | 0.438 | 244 |
| procedure | 1.000 | 0.233 | 0.378 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.634 | 0.222 | 0/58 |
| accent:in | 0.453 | 0.106 | 0/246 |
| accent:us | 0.589 | 0.241 | 0/136 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “Knock-in 2.75 mgs, IV, 5 min ago.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-002` (miss): “glucose, three gramme, intravenously, right now” → ASR “Work was 3 grand intravenously right now.”  
  output None  
  expected {'drug': 'dextrose', 'dose_value': 3.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
- `mb07-0-006` (miss): “Mag, eight g, i.m., 10 min ago” → ASR “MAG-8G, I am 10 min ago.”  
  output None  
  expected {'drug': 'magnesium sulfate', 'dose_value': 8.0, 'dose_unit': 'g', 'route': 'IM', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-008` (miss): “o2, one lpm, inhaled, ten minutes ago” → ASR “O2, 1 LPM, inhaled 10 minutes ago.”  
  output None  
  expected {'drug': 'oxygen', 'dose_value': 1.0, 'dose_unit': 'L/min', 'route': 'INH', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-011` (miss): “vomikind, seven and a half milligrammes, into the vein, at 9 20” → ASR “Vomicind 7.5 mg into the vein at 920.”  
  output None  
  expected {'drug': 'ondansetron', 'dose_value': 7.5, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T09:20:00+05:30'}
