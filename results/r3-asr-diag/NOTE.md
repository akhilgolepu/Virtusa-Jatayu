# NOTE — r3-asr-diag (BEFORE the TTS route-abbreviation fix)

Dev only, 100 clips (seed 3), rules extractor on each transcript. Stamped `1b7c3fd-dirty`: the run used the
uncommitted `Transcriber(beam_size, vad_filter, use_prompt)` knobs (defaults identical to the committed code) and the
new `eval/asr_diag.py` / `eval/asr_text.py`; all were committed unchanged in `1359226`.
Audio = the round-2 dev renders, in which Piper read a bare "iv" as the Roman numeral ("Roman four", 8 of 9 clips).
The AFTER run on re-rendered audio is `results/r3-asr-diag-after-tts-fix/`.
