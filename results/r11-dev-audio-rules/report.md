# Evaluation `r11-dev-audio-rules`

Split **dev** · mode **audio** · extractor **rules** · n = 480 utterances · commit at start `1515ea5`
**Source: synthetic speech (Piper)**


Decision-support demo, not a clinical device. Synthetic data (see README).

| Metric | Value |
|---|---|
| Entity F1 (micro) | 0.644 (P 0.825, R 0.529) |
| Record exact match | 181/520 = 0.348 |
| **Dangerous errors (headline, round 10): wrong drug, dose, unit, route or status with no flag that must be ticked** | **5 of 480** (1.04%; uncaught by kind: {'wrong dose/unit/route': 4, 'wrong drug': 1}; all such errors: {'omitted dose/unit/route (shown as not stated; not counted)': 120, 'wrong dose/unit/route': 30, 'wrong drug': 43, 'status (not given recorded as given)': 2}) |
| Not stated (shown apart: an empty field, not a wrong value) — drug (no entry at all) / dose / unit / route / time | 96 of 420 · 25 of 299 · 84 of 299 · 89 of 276 · 67 of 169 |
| Dangerous errors, matched-drug only (pre-round-10 metric, secondary; a wrong drug is not counted) | 1 of 440 (0.23%; strict: weight_based_dose and low_asr_confidence do not catch) |
| Dangerous errors, lenient (weight_based_dose and low_asr_confidence count as catches) | 1 of 440 |
| **Administration-status errors** (not given, recorded as given) | **2 of 40** |
| Context errors (not-given / measurement emitted unflagged) | 5 of 80 |
| Deliberate dose anomalies flagged | 17 of 21 |
| Accepted fields with a source quote | 1128 of 1128 |
| Latency p50 / p95 (s) | 0.0002 / 0.0004 (n=480) |
| WER (normalised: numbers, units, routes; same on both sides) | 0.406 |
| WER raw (lowercase, punctuation stripped) | 0.639 |
| Drug-term recall (lexicon names in the reference) | 0.574 (n=460) |

## Per field

| Field | P | R | F1 | gold |
|---|---|---|---|---|
| drug | 0.860 | 0.691 | 0.766 | 460 |
| dose_value | 0.748 | 0.555 | 0.637 | 380 |
| dose_unit | 0.837 | 0.474 | 0.605 | 380 |
| route | 0.840 | 0.439 | 0.577 | 360 |
| time | 0.802 | 0.381 | 0.517 | 244 |
| procedure | 1.000 | 0.600 | 0.750 | 60 |

## Groups

| Group | Entity F1 | Exact match | Dangerous (headline) | Dangerous, matched-drug only |
|---|---|---|---|---|
| accent:gb | 0.755 | 0.472 | 1/63 | 0/58 |
| accent:in | 0.538 | 0.238 | 4/266 | 1/246 |
| accent:us | 0.759 | 0.482 | 0/151 | 0/136 |

## Leakage checks

- test families in train/dev: 0
- test patterns in final_test: 0

## Five worst failures

- `hi01-0-001` (miss): “epipen 15 micrograms i.v. de diya” → ASR “Atropine 50 micrograms, IV to the U.”  
  output None  
  expected {'drug': 'epinephrine', 'dose_value': 15.0, 'dose_unit': 'mcg', 'route': 'IV'}
- `mx07-0-005` (wrong): “frusemide eighty milligramme iv 10 min ago then calcium one mg io ten min ago” → ASR “furosemide, 18 milligram, iodine, minu-covin, calcium, onlamgene, aero, 10 minu-gos.”  
  output {'drug': 'furosemide', 'dose_value': 18.0, 'dose_unit': 'mg'}  
  expected {'drug': 'furosemide', 'dose_value': 80.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'}
- `mb07-0-013` (wrong, DANGEROUS): “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  output {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'}  
  expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'}
- `mm02-2-017` (wrong): “um 0.8 mcg uh adrenalin ivp” → ASR “IM 0.8 MCG, our adrenaline IVP.”  
  output {'drug': 'epinephrine', 'dose_value': 0.8, 'dose_unit': 'mcg', 'route': 'IM'}  
  expected {'drug': 'epinephrine', 'dose_value': 0.8, 'dose_unit': 'mcg', 'route': 'IV'}
- `mx07-1-013` (wrong): “right now fentanyl sixty mcgs in the nose, right now diphenhydramine 50 milligrammes oral” → ASR “Right now, fentanyl is 16 mcgs in the nose. Right now, teselhyde drumming 50 milligrams That's all.”  
  output {'drug': 'fentanyl', 'dose_value': 16.0, 'dose_unit': 'mcg', 'route': 'IN', 'time': '2026-10-31T10:45:00+05:30'}  
  expected {'drug': 'fentanyl', 'dose_value': 60.0, 'dose_unit': 'mcg', 'route': 'IN', 'time': '2026-10-31T10:45:00+05:30'}
