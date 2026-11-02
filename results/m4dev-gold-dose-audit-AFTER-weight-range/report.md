# Gold dose audit — `m4dev-gold-dose-audit-AFTER-weight-range`

Aggregate only: gold labels, no pipeline, no individual record. 'Outside range' = outside the lexicon range for the drug (+ route when spoken; per-kg rows x 45-130 kg). 'Validator flagged' = the validator raises a catching flag on the gold record itself (includes its own N/5 decimal-slip floor).

| Split | Gold doses | Outside range | Validator flagged | Deliberate out_of_range_case |
|---|---|---|---|---|
| dev | 359 | 0 | 7 | 21 |
| test | 291 | 0 | 1 | 9 |
| final_test | 168 | 0 | 2 | 12 |

## dev: drugs with any gold dose outside range or flagged

| Drug | Gold doses | Outside range | Validator flagged (by rule) |
|---|---|---|---|
| dextrose | 13 | 0 | 4 (dose_below_range 4) |
| epinephrine | 10 | 0 | 2 (dose_below_range 1, possible_mg_mcg_confusion 1) |
| naloxone | 9 | 0 | 1 (dose_below_range 1) |

## test: drugs with any gold dose outside range or flagged

| Drug | Gold doses | Outside range | Validator flagged (by rule) |
|---|---|---|---|
| dextrose | 7 | 0 | 1 (dose_below_range 1) |

## final_test: drugs with any gold dose outside range or flagged

| Drug | Gold doses | Outside range | Validator flagged (by rule) |
|---|---|---|---|
| epinephrine | 5 | 0 | 2 (dose_below_range 2) |
