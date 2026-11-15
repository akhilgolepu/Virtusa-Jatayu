# Evaluation `r10a-dev-noise-rules`

Split **dev** · mode **noisy** · extractor **rules** · n = 160 utterances · commit at start `32a0b3d`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.607 (P 0.802, R 0.488) |
| Record exact match | 200/480 = 0.417 |
| **Dangerous errors (headline, round 10): wrong drug, dose, unit, route or status with no flag that must be ticked** | **6 of 360** (1.67%; uncaught by kind: {'wrong dose/unit/route': 4, 'wrong drug': 2}; all such errors: {'omitted dose/unit/route (shown as not stated; not counted)': 86, 'wrong dose/unit/route': 15, 'wrong drug': 43, 'status (not given recorded as given)': 10}) |
| Dangerous errors, matched-drug only (pre-round-10 metric, secondary; a wrong drug is not counted) | 3 of 240 (1.25%; strict: weight_based_dose and low_asr_confidence do not catch) |
| Dangerous errors, lenient (weight_based_dose and low_asr_confidence count as catches) | 3 of 240 |
| **Administration-status errors** (not given, recorded as given) | **10 of 120** |
| Context errors (not-given / measurement emitted unflagged) | 20 of 240 |
| Deliberate dose anomalies flagged | 6 of 9 |
| Accepted fields with a source quote | 972 of 972 |
| Latency p50 / p95 (s) | 0.0002 / 0.0004 (n=640) |
| WER (normalised: numbers, units, routes; same on both sides) | 0.463 |
| WER raw (lowercase, punctuation stripped) | 0.683 |
| Drug-term recall (lexicon names in the reference) | 0.600 (n=640) |

## Noise curve (entity F1)

| SNR dB | F1 |
|---|---|
| clean | 0.624 |
| 20 | 0.629 |
| 10 | 0.613 |
| 5 | 0.578 |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.831 | 0.675 | 0.745 | 480 |
| dose_value | 0.722 | 0.483 | 0.579 | 360 |
| dose_unit | 0.828 | 0.400 | 0.539 | 360 |
| route | 0.750 | 0.250 | 0.375 | 180 |
| time | 0.974 | 0.363 | 0.529 | 102 |

## Groups

| Group | Entity F1 | Exact match | Dangerous (headline) | Dangerous, matched-drug only |
|---|---|---|---|---|
| accent:gb | 0.533 | 0.516 | 0/28 | 0/8 |
| accent:in | 0.585 | 0.327 | 8/364 | 4/284 |
| accent:us | 0.725 | 0.676 | 0/88 | 0/28 |
| snr:10 | 0.613 | 0.438 | 2/120 | 1/80 |
| snr:20 | 0.629 | 0.431 | 3/120 | 2/80 |
| snr:5 | 0.578 | 0.381 | 1/120 | 0/80 |
| snr:clean | 0.624 | 0.456 | 2/120 | 1/80 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `hi01-0-001` (miss): “epipen 15 micrograms i.v. de diya” → ASR “Atropine, 50 micrograms, IDE to the ear.”  
  output None  
  expected {'drug': 'epinephrine', 'dose_value': 15.0, 'dose_unit': 'mcg', 'route': 'IV'}
- `hi01-0-001` (miss): “epipen 15 micrograms i.v. de diya” → ASR “Atropine 15 micrograms, IV to the ear.”  
  output None  
  expected {'drug': 'epinephrine', 'dose_value': 15.0, 'dose_unit': 'mcg', 'route': 'IV'}
- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mb07-0-018` (wrong): “atropine, 60 milligram, i.v., ten mins ago” → ASR “atropine, 6 milligram, 10 minutes ago.”  
  output {'drug': 'atropine', 'dose_value': 6.0, 'dose_unit': 'mg', 'time': '2026-10-31T10:35:00+05:30'}  
  expected {'drug': 'atropine', 'dose_value': 60.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'}
