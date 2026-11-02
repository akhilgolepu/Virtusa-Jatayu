# NOTE — r3-asr-diag-after-tts-fix

Same 100 dev clip identities as `results/r3-asr-diag/` (seed 3; same utterance + voice), re-rendered after
`datagen/tts.py` started spelling route abbreviations ("iv" -> "I V"); 153 of 480 dev clips changed. Commit `4351849`
(clean). "Roman" in transcripts: 8 -> 0. Normalised WER 0.398 -> 0.366; entity F1 (rules) 0.671 -> 0.704.
