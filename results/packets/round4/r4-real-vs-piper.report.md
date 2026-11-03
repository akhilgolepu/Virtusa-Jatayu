# Real vs Piper speech, dev (`r4-real-vs-piper`, commit `212d5e3`)

Piper run: `results/r4-dev-audio-hybrid` (480 synthetic clips). Real: `data/real/dev` (0 clips). Same ASR settings, same normalisation (eval/asr_text.py).

| | Clips | WER normalised | WER raw | Drug-term recall |
|---|---|---|---|---|
| Piper (synthetic) | 480 | 0.406 | 0.639 | 0.574 (n=460) |

**No real dev recordings have been imported yet** (`python -m scripts.import_real --split dev ...`).
