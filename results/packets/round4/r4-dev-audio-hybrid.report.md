# Evaluation `r4-dev-audio-hybrid`

Split **dev** · mode **audio** · extractor **hybrid** · n = 480 utterances · commit at start `212d5e3`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.672 (P 0.925, R 0.528) |
| Record exact match | 174/520 = 0.335 |
| **Dangerous errors** | **3 of 440** (0.68%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 3 of 440 |
| **Administration-status errors** (not given, recorded as given) | **4 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 10 of 80 |
| Deliberate dose anomalies flagged | 17 of 21 |
| Accepted fields with a source quote | 1018 of 1018 |
| Latency p50 / p95 (s) | 0.6269 / 1.167 (n=480) |
| WER (normalised: numbers, units, routes; same on both sides) | 0.406 |
| WER raw (lowercase, punctuation stripped) | 0.639 |
| Drug-term recall (lexicon names in the reference) | 0.574 (n=460) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.970 | 0.691 | 0.807 | 460 |
| dose_value | 0.860 | 0.547 | 0.669 | 380 |
| dose_unit | 0.946 | 0.503 | 0.656 | 380 |
| route | 0.919 | 0.442 | 0.597 | 360 |
| time | 0.882 | 0.336 | 0.487 | 244 |
| procedure | 1.000 | 0.600 | 0.750 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.805 | 0.458 | 0/58 |
| accent:in | 0.558 | 0.231 | 1/246 |
| accent:us | 0.789 | 0.458 | 2/136 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mc01-1-008` (wrong, DANGEROUS): “administered pcm 800, sorry, one thousand mg intravenously ten min ago” → ASR “Administered PCM 800, sorry, 1000 angia intravenously 10 men ago.”  
  output {'drug': 'paracetamol', 'dose_value': 10.0, 'route': 'IV'}  
  expected {'drug': 'paracetamol', 'dose_value': 1000.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mc01-1-009` (wrong, DANGEROUS): “administered furosemide thirty, no, 25 mg ivp” → ASR “Administered furosemide 30, no 25, empty IVP.”  
  output {'drug': 'furosemide', 'dose_value': 25.0, 'route': 'IV'}  
  expected {'drug': 'furosemide', 'dose_value': 25.0, 'dose_unit': 'mg', 'route': 'IV'}
- `mb07-0-001` (miss): “narcan, 0.75 mgs, iv, 5 min ago” → ASR “Knock-in 2.75 mgs, IV, 5 min ago.”  
  output None  
  expected {'drug': 'naloxone', 'dose_value': 0.75, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:40:00+05:30'}
- `mb07-0-002` (miss): “glucose, three gramme, intravenously, right now” → ASR “Work was 3 grand intravenously right now.”  
  output None  
  expected {'drug': 'dextrose', 'dose_value': 3.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
