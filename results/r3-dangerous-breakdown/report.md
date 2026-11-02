# Dangerous errors, categorised (`r3-dangerous-breakdown`, dev, commit `c0ff23e`)

Strict definition (weight_based_dose does not catch). Every dangerous record in the runs below.

| Run | Dangerous |
|---|---|
| r3-dev-text-rules | 0/440 |
| r3-dev-text-hybrid | 5/440 |
| r3-dev-text-llm | 3/440 |
| r3-dev-audio-rules | 1/440 |
| r3-dev-audio-hybrid | 3/440 |
| r3-dev-audio-llm | 0/440 |
| r3-dev-noise-paired-hybrid | 3/240 |

| Wrong field | n |
|---|---|
| dose_value | 15 |

| Why no catching flag fired | n |
|---|---|
| valid dose for the recorded drug and route (inside the cited range) | 15 |

| Origin | n |
|---|---|
| extraction | 10 |
| ASR | 5 |

## Every record (dev)

- **r3-dev-text-hybrid** `mc01-0-003` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “amio 250, no, three hundred milligrams intraosseous”  
  recorded {'drug': 'amiodarone', 'dose_value': 250.0, 'dose_unit': 'mg', 'route': 'IO'} · expected {'drug': 'amiodarone', 'dose_value': 300.0, 'dose_unit': 'mg', 'route': 'IO'} · flags ['time_not_stated']
- **r3-dev-text-hybrid** `mc01-0-005` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “norepinephrine 2.5, actually, 6 mics iv push”  
  recorded {'drug': 'norepinephrine', 'dose_value': 2.5, 'dose_unit': 'mcg', 'route': 'IV'} · expected {'drug': 'norepinephrine', 'dose_value': 6.0, 'dose_unit': 'mcg', 'route': 'IV'} · flags ['time_not_stated']
- **r3-dev-text-hybrid** `mc01-1-000` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “given magnesium sulfate 1.5, no, two grammes iv push two min ago”  
  recorded {'drug': 'magnesium sulfate', 'dose_value': 1.5, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:43:00+05:30'} · expected {'drug': 'magnesium sulfate', 'dose_value': 2.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:43:00+05:30'} · flags []
- **r3-dev-text-hybrid** `mc01-1-015` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “given morphine 1.5, no, 8 milligramme intramuscularly just now”  
  recorded {'drug': 'morphine', 'dose_value': 1.5, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'} · expected {'drug': 'morphine', 'dose_value': 8.0, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'} · flags []
- **r3-dev-text-hybrid** `mc01-1-016` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “given Cacl2 0.5, sorry, one gram ivp right now”  
  recorded {'drug': 'calcium chloride', 'dose_value': 0.5, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'} · expected {'drug': 'calcium chloride', 'dose_value': 1.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'} · flags []
- **r3-dev-text-llm** `mc01-0-004` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “Tranexamic acid 1.5, no sorry, two gram intraosseous”  
  recorded {'drug': 'tranexamic acid', 'dose_value': 1.5, 'dose_unit': 'g', 'route': 'IO'} · expected {'drug': 'tranexamic acid', 'dose_value': 2.0, 'dose_unit': 'g', 'route': 'IO'} · flags ['time_not_stated']
- **r3-dev-text-llm** `mc01-1-001` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “given Nitroglycerin 0.8, no sorry, .4 mgs under the tongue ten minutes ago”  
  recorded {'drug': 'nitroglycerin', 'dose_value': 0.8, 'dose_unit': 'mg', 'route': 'SL', 'time': '2026-10-31T10:35:00+05:30'} · expected {'drug': 'nitroglycerin', 'dose_value': 0.4, 'dose_unit': 'mg', 'route': 'SL', 'time': '2026-10-31T10:35:00+05:30'} · flags []
- **r3-dev-text-llm** `mc01-1-016` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (typed text)  
  input “given Cacl2 0.5, sorry, one gram ivp right now”  
  recorded {'drug': 'calcium chloride', 'dose_value': 0.5, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'} · expected {'drug': 'calcium chloride', 'dose_value': 1.0, 'dose_unit': 'g', 'route': 'IV', 'time': '2026-10-31T10:45:00+05:30'} · flags []
- **r3-dev-audio-rules** `mb07-0-013` — dose_value; valid dose for the recorded drug and route (inside the cited range); ASR (dose_value '50' not in the transcript)  
  input “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  recorded {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'} · expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'} · flags ['time_not_stated']
- **r3-dev-audio-hybrid** `mb07-0-013` — dose_value; valid dose for the recorded drug and route (inside the cited range); ASR (dose_value '50' not in the transcript)  
  input “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  recorded {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'} · expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'} · flags ['time_not_stated']
- **r3-dev-audio-hybrid** `mc01-1-005` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (the gold values are in the transcript)  
  input “gave fentanyl one hundred, no, seventy five microgram intramuscularly one mins ago” → ASR “Gave fentanyl 100, no 75 microgram intramuscularly one minutes ago.”  
  recorded {'drug': 'fentanyl', 'dose_value': 100.0, 'dose_unit': 'mcg', 'route': 'IM', 'time': '2026-10-31T10:44:00+05:30'} · expected {'drug': 'fentanyl', 'dose_value': 75.0, 'dose_unit': 'mcg', 'route': 'IM', 'time': '2026-10-31T10:44:00+05:30'} · flags []
- **r3-dev-audio-hybrid** `mc01-1-015` — dose_value; valid dose for the recorded drug and route (inside the cited range); extraction (the gold values are in the transcript)  
  input “given morphine 1.5, no, 8 milligramme intramuscularly just now” → ASR “given morphine 1.5, no, 8 milligram intramuscularly just now.”  
  recorded {'drug': 'morphine', 'dose_value': 1.5, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'} · expected {'drug': 'morphine', 'dose_value': 8.0, 'dose_unit': 'mg', 'route': 'IM', 'time': '2026-10-31T10:45:00+05:30'} · flags []
- **r3-dev-noise-paired-hybrid** `mb07-0-013` — dose_value; valid dose for the recorded drug and route (inside the cited range); ASR (dose_value '50' not in the transcript)  
  input “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  recorded {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'} · expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'} · flags ['time_not_stated']
- **r3-dev-noise-paired-hybrid** `mb07-0-013` — dose_value; valid dose for the recorded drug and route (inside the cited range); ASR (dose_value '50' not in the transcript)  
  input “bicarbonate, fifty millimole, intravenous, 15 minutes ago” → ASR “Bicarbonate, 15 millimole, intravenous, 15 minutes at all.”  
  recorded {'drug': 'sodium bicarbonate', 'dose_value': 15.0, 'dose_unit': 'mmol', 'route': 'IV'} · expected {'drug': 'sodium bicarbonate', 'dose_value': 50.0, 'dose_unit': 'mmol', 'route': 'IV', 'time': '2026-10-31T10:30:00+05:30'} · flags ['time_not_stated']
- **r3-dev-noise-paired-hybrid** `mb07-0-018` — dose_value; valid dose for the recorded drug and route (inside the cited range); ASR (dose_value '60' not in the transcript)  
  input “atropine, 60 milligram, i.v., ten mins ago” → ASR “Atropine, 6 milligram, IV, 10 minutes ago.”  
  recorded {'drug': 'atropine', 'dose_value': 6.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'} · expected {'drug': 'atropine', 'dose_value': 60.0, 'dose_unit': 'mg', 'route': 'IV', 'time': '2026-10-31T10:35:00+05:30'} · flags []
