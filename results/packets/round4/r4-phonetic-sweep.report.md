# Phonetic drug-match threshold (`r4-phonetic-sweep`, dev, 480 clips, commit `f64572b`)

Rules extractor on fixed dev ASR transcripts (`results/r3-dev-audio-hybrid/transcripts.jsonl`); only the phonetic matcher changes.

| Threshold | Drug P | Drug R | Drug F1 | Entity F1 |
|---|---|---|---|---|
| off | 0.977 | 0.633 | 0.768 | 0.632 |
| 80 | 0.888 | 0.724 | 0.798 | 0.680 |
| 84 | 0.970 | 0.691 | 0.807 | 0.670 |
| 88 | 0.969 | 0.680 | 0.799 | 0.664 |
| 92 | 0.978 | 0.670 | 0.795 | 0.657 |
| 96 | 0.978 | 0.661 | 0.789 | 0.654 |
