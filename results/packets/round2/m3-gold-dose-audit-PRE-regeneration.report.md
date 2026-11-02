# Gold dose audit — `m3-gold-dose-audit-PRE-regeneration`

Aggregate only: gold labels, no pipeline, no individual record. 'Outside range' = outside the lexicon range for the drug (+ route when spoken; per-kg rows x 45-130 kg). 'Validator flagged' = the validator raises a catching flag on the gold record itself (includes its own N/5 decimal-slip floor).

| Split | Gold doses | Outside range | Validator flagged | Deliberate out_of_range_case |
|---|---|---|---|---|
| dev | 357 | 51 | 28 | 23 |
| test | 288 | 48 | 19 | 12 |
| final_test | 170 | 23 | 11 | 10 |

## dev: drugs with any gold dose outside range or flagged

| Drug | Gold doses | Outside range | Validator flagged (by rule) |
|---|---|---|---|
| atropine | 7 | 5 | 5 (dose_below_range 5) |
| dexamethasone | 8 | 6 | 0 (-) |
| epinephrine | 11 | 2 | 0 (-) |
| fentanyl | 15 | 6 | 0 (-) |
| glucagon | 4 | 3 | 3 (dose_below_range 3) |
| hydrocortisone | 16 | 7 | 7 (dose_out_of_range 7) |
| ipratropium | 6 | 2 | 2 (dose_below_range 2) |
| ketamine | 8 | 1 | 0 (-) |
| ketorolac | 12 | 7 | 7 (dose_out_of_range 7) |
| methylprednisolone | 12 | 5 | 0 (-) |
| normal saline | 9 | 1 | 0 (-) |
| paracetamol | 15 | 2 | 0 (-) |
| salbutamol | 10 | 4 | 4 (dose_below_range 4) |

## test: drugs with any gold dose outside range or flagged

| Drug | Gold doses | Outside range | Validator flagged (by rule) |
|---|---|---|---|
| atropine | 4 | 1 | 1 (dose_below_range 1) |
| dexamethasone | 6 | 2 | 0 (-) |
| fentanyl | 12 | 2 | 0 (-) |
| glucagon | 10 | 6 | 6 (dose_below_range 6) |
| hydrocortisone | 5 | 3 | 3 (dose_out_of_range 3) |
| ipratropium | 8 | 3 | 3 (dose_below_range 3) |
| ketamine | 9 | 2 | 0 (-) |
| ketorolac | 9 | 5 | 5 (dose_out_of_range 5) |
| methylprednisolone | 10 | 8 | 0 (-) |
| midazolam | 12 | 3 | 0 (-) |
| normal saline | 21 | 12 | 0 (-) |
| salbutamol | 5 | 1 | 1 (dose_below_range 1) |

## final_test: drugs with any gold dose outside range or flagged

| Drug | Gold doses | Outside range | Validator flagged (by rule) |
|---|---|---|---|
| atropine | 3 | 2 | 2 (dose_below_range 2) |
| dexamethasone | 4 | 3 | 0 (-) |
| epinephrine | 5 | 1 | 1 (dose_out_of_range 1) |
| fentanyl | 5 | 1 | 0 (-) |
| glucagon | 3 | 3 | 3 (dose_below_range 3) |
| ketorolac | 16 | 3 | 3 (dose_out_of_range 3) |
| methylprednisolone | 3 | 1 | 0 (-) |
| normal saline | 15 | 5 | 0 (-) |
| paracetamol | 8 | 2 | 0 (-) |
| salbutamol | 4 | 2 | 2 (dose_below_range 2) |
