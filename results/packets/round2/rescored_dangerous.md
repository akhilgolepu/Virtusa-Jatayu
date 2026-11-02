# Dangerous-error rate, offline re-score from errors.jsonl (dev runs, pre-regeneration data)

Strict: weight_based_dose, no_reference_range, time_not_stated do not catch. Lenient: weight_based_dose catches (the old definition; it reproduces every recorded count).

| Run | As recorded | Strict (headline) | Lenient |
|---|---|---|---|
| m3-dev-audio-hybrid_SUPERSEDED | 6/440 | 6/440 | 6/440 |
| m3-dev-noise-hybrid_SUPERSEDED | 2/240 | 2/240 | 2/240 |
| m3-dev-text-hybrid_SUPERSEDED | 3/440 | 3/440 | 3/440 |
| m3-dev-text-llm_SUPERSEDED | 1/440 | 1/440 | 1/440 |
| m3-dev-text-rules_SUPERSEDED-pre-regeneration | 0/440 | 0/440 | 0/440 |
| m3-dev-text-rules_SUPERSEDED | 0/440 | 0/440 | 0/440 |
