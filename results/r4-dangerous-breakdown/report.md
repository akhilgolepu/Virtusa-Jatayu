# Dangerous errors, categorised (`r4-dangerous-breakdown`, dev, commit `4b95fa2`)

Strict definition (weight_based_dose does not catch). Every dangerous record in the runs below.

| Run | Dangerous |
|---|---|
| r4-dev-text-rules-v2 | 0/440 |
| r4-dev-text-hybrid-v2 | 0/440 |
| r4-dev-audio-rules-v2 | 1/440 |
| r4-dev-audio-hybrid-v2 | 1/440 |
| r4-dev-audio-llm | 0/440 |

| Wrong field | n |
|---|---|
| dose_value | 2 |

| Why no catching flag fired | n |
|---|---|
| valid dose for the recorded drug and route (inside the cited range) | 2 |

| Origin | n |
|---|---|
| ASR | 2 |

## Every record (dev)

- **r4-dev-audio-rules-v2** `mb07-0-013` — dose_value; valid dose for the recorded drug and route (inside the cited range); ASR (dose_value '50' not in the transcript)  
  input “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  recorded {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'} · expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'} · flags ['time_not_stated']
- **r4-dev-audio-hybrid-v2** `mb07-0-013` — dose_value; valid dose for the recorded drug and route (inside the cited range); ASR (dose_value '50' not in the transcript)  
  input “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  recorded {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'} · expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'} · flags ['time_not_stated']
