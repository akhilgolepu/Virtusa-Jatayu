# low_asr_confidence threshold (`r4-asr-threshold`, dev, commit `a117f45`)

125 correct and 132 wrong matched given-medication records (rules extractor on `results/r4-dev-audio-rules-no-asr-flag/transcripts.jsonl`). Criterion fixed in advance: max(catch - false alarm), ties → lower threshold.

**Chosen: p < 0.2** — flags 24.2% of wrong records and 12.8% of correct records.

| Threshold | Wrong records flagged | Correct records flagged | J |
|---|---|---|---|
| 0.05 | 0.061 | 0.040 | 0.021 |
| 0.1 | 0.106 | 0.064 | 0.042 |
| 0.15 | 0.167 | 0.104 | 0.063 |
| 0.2 | 0.242 | 0.128 | 0.114 |
| 0.25 | 0.273 | 0.184 | 0.089 |
| 0.3 | 0.326 | 0.272 | 0.054 |
| 0.35 | 0.417 | 0.360 | 0.057 |
| 0.4 | 0.485 | 0.400 | 0.085 |
| 0.45 | 0.553 | 0.504 | 0.049 |
| 0.5 | 0.636 | 0.568 | 0.068 |
| 0.55 | 0.735 | 0.656 | 0.079 |
| 0.6 | 0.795 | 0.768 | 0.028 |
| 0.65 | 0.841 | 0.824 | 0.017 |
| 0.7 | 0.871 | 0.880 | -0.009 |
| 0.75 | 0.932 | 0.904 | 0.028 |
| 0.8 | 0.962 | 0.960 | 0.002 |
| 0.85 | 0.970 | 0.992 | -0.022 |
| 0.9 | 0.992 | 0.992 | 0.000 |
| 0.95 | 1.000 | 1.000 | 0.000 |
