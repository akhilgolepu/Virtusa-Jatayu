# Required fields to fill per note, dev speech (`r12-required-fields`, commit `b1a995f`)

480 dev speech clips (synthetic speech, saved transcripts), rules NER; one note = one clip; 370 medication entries recorded. Required fields: drug, dose, unit, route.

| Per note | Mean | p90 | Max | Notes with any |
|---|---|---|---|---|
| Empty required fields on the recorded entries | 0.808 | 2 | 7 | 228 of 480 |
| Medication records with no entry at all (apart: nothing on screen to fill) | 0.2 | 1 | 2 | 93 of 480 |

| Field | Empty on a recorded entry (total) |
|---|---|
| drug | 0 |
| dose_value | 51 |
| dose_unit | 155 |
| route | 182 |
