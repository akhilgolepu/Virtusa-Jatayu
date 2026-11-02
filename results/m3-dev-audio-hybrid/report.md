# Evaluation `m3-dev-audio-hybrid`

Split **dev** · mode **audio** · extractor **hybrid** · n = 480 utterances · commit at start `cb16546-dirty`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.626 (P 0.920, R 0.474) |
| Record exact match | 152/520 = 0.292 |
| **Dangerous errors** | **4 of 440** (0.91%; strict: weight_based_dose does not catch) |
| Dangerous errors, lenient (weight_based_dose counts as a catch) | 4 of 440 |
| Context errors (not-given / measurement emitted unflagged) | 21 of 80 |
| Deliberate dose anomalies flagged | 14 of 21 |
| Accepted fields with a source quote | 927 of 927 |
| Latency p50 / p95 (s) | 0.9419 / 2.1671 (n=480) |
| WER | 0.631 |
| Drug-term recall | 0.591 |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.980 | 0.635 | 0.770 | 460 |
| dose_value | 0.837 | 0.500 | 0.626 | 380 |
| dose_unit | 0.947 | 0.466 | 0.624 | 380 |
| route | 0.894 | 0.353 | 0.506 | 360 |
| time | 0.876 | 0.291 | 0.437 | 244 |
| procedure | 1.000 | 0.600 | 0.750 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous |
|---|---|---|---|
| accent:gb | 0.751 | 0.403 | 1/58 |
| accent:in | 0.549 | 0.216 | 1/246 |
| accent:us | 0.693 | 0.373 | 2/136 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `mx07-1-004` (wrong, DANGEROUS): “at 10:15 mgso4 one grams i.v., at 10 20 Calcium 1 milligramme intraosseously” → ASR “At 1015, Yaso, IV, 1g, IV, at 1020, Calcium, 1mg, intraciously.”  
  output {'drug': 'calcium chloride', 'dose_value': 1.0, 'dose_unit': 'g', 'route': 'IV'}  
  expected {'drug': 'calcium chloride', 'dose_value': 1.0, 'dose_unit': 'mg', 'route': 'IO', 'time': '2026-10-31T10:20:00+05:30'}
- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mc01-1-005` (wrong, DANGEROUS): “gave fentanyl one hundred, no, seventy five microgram intramuscularly one mins ago” → ASR “Gave fentanyl 100, no 75 microgram intramuscularly one minutes ago.”  
  output {'drug': 'fentanyl', 'dose_value': 100.0, 'dose_unit': 'mcg', 'route': 'IM', 'time': '2026-10-31T10:44:00+05:30'}  
  expected {'drug': 'fentanyl', 'dose_value': 75.0, 'dose_unit': 'mcg', 'route': 'IM', 'time': '2026-10-31T10:44:00+05:30'}
- `mc01-1-015` (wrong, DANGEROUS): “given morphine 1.5, no, 8 milligramme intramuscularly just now” → ASR “given morphine 1.5, no, 8 milligram intramuscularly just now.”  
  output {'drug': 'morphine', 'dose_value': 1.5, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'}  
  expected {'drug': 'morphine', 'dose_value': 8.0, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'}
- `mb07-0-002` (miss): “glucose, three gramme, intravenously, right now” → ASR “Work was 3 grand intravenously right now.”  
  output None  
  expected {'drug': 'dextrose', 'dose_value': 3.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'}
