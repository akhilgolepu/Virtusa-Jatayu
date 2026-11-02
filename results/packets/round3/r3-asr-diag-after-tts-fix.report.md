# ASR diagnosis `r3-asr-diag-after-tts-fix` (dev, 100 clips, seed 3, commit `4351849`)

Synthetic speech (Piper). Extraction = rules extractor on the transcript (deterministic), so differences between rows come from the ASR setting alone. One setting changed per row against the baseline ({'model': 'small.en', 'beam': 5, 'vad': True, 'prompt': True}).

| Setting | WER raw | WER normalised | Drug-term recall | Entity F1 (rules) | s/clip |
|---|---|---|---|---|---|
| baseline | 0.603 | 0.366 | 0.648 (n=88) | 0.704 | 0.243 |
| vad off | 0.604 | 0.366 | 0.648 (n=88) | 0.701 | 0.234 |
| prompt off | 0.677 | 0.492 | 0.330 (n=88) | 0.474 | 0.204 |
| beam 1 | 0.598 | 0.366 | 0.659 (n=88) | 0.690 | 0.207 |
| beam 10 | 0.606 | 0.379 | 0.636 (n=88) | 0.697 | 0.35 |
| medium.en | 0.585 | 0.353 | 0.659 (n=88) | 0.693 | 0.362 |

WER raw = lowercase, punctuation stripped (the definition used in round 2). WER normalised = the pipeline's number normaliser + unit/route words mapped to lexicon codes, on reference AND hypothesis.
Drug-term recall = gold drugs whose name the lexicon recognises in the reference and that also appear in the transcript; the round-2 surface-string recall on the baseline is 0.670.

## Per field, baseline (entity F1, rules extractor)

| Field | F1 |
|---|---|
| drug | 0.821 |
| dose_value | 0.683 |
| dose_unit | 0.707 |
| route | 0.635 |
| time | 0.568 |
| procedure | 0.759 |

## Normalised WER by voice

| Voice | baseline | vad off | prompt off | beam 1 | beam 10 | medium.en |
|---|---|---|---|---|---|---|
| alan | 0.100 | 0.100 | 0.120 | 0.120 | 0.100 | 0.100 |
| amy | 0.200 | 0.200 | 0.286 | 0.200 | 0.200 | 0.171 |
| kusal | 0.205 | 0.205 | 0.385 | 0.205 | 0.205 | 0.231 |
| l2arctic-ASI | 0.681 | 0.681 | 0.745 | 0.617 | 0.681 | 0.660 |
| l2arctic-RRBI | 0.442 | 0.442 | 0.596 | 0.404 | 0.442 | 0.404 |
| l2arctic-SVBI | 0.690 | 0.690 | 0.828 | 0.655 | 0.759 | 0.690 |
| l2arctic-TNI | 0.516 | 0.516 | 0.875 | 0.578 | 0.531 | 0.500 |
| lessac | 0.167 | 0.167 | 0.222 | 0.222 | 0.167 | 0.222 |
| libritts_r-0 | 0.400 | 0.400 | 0.540 | 0.400 | 0.440 | 0.320 |
| ryan | 0.214 | 0.214 | 0.286 | 0.179 | 0.214 | 0.214 |
| southern_female | 0.259 | 0.259 | 0.293 | 0.259 | 0.259 | 0.155 |
| vctk-p248 | 0.431 | 0.431 | 0.500 | 0.431 | 0.448 | 0.483 |
| vctk-p251 | 0.319 | 0.319 | 0.507 | 0.319 | 0.391 | 0.362 |
| vctk-p376 | 0.352 | 0.352 | 0.426 | 0.370 | 0.315 | 0.333 |

## Audio reaching Whisper

- file_format: {'16000 Hz, 1 ch, 16 bit': 100}
- decoded_to_whisper: {'1-D float32': 100}
- sample_rate_given_to_whisper: 16000
- clips_with_duration_mismatch_over_10ms: 0

## 10 random (reference, transcript) pairs, baseline

- `mb07-0-007` (vctk-p251)  
  REF: Calpol, six hundred fifty milligram, io, 10 mins ago  
  ASR: Calpol, 650 mg, IO, 10 minutes ago.
- `mc01-0-014` (vctk-p248)  
  REF: pentazocine 50, I mean, 40 mgs intramuscular  
  ASR: Pentazocine 50, I mean 40 mgs intramuscular.
- `cn04-1-017` (l2arctic-ASI)  
  REF: on home narcan 0.5 milligramme  
  ASR: on whole north end 0.5 milligram.
- `tc01-1-003` (southern_female)  
  REF: epinephrine 5 milligram nebulization at 9:47  
  ASR: epinephrine 5mg nebulisation at 947.
- `mi02-0-015` (vctk-p251)  
  REF: gave naloxone intramuscular  
  ASR: Gave naloxone intramuscular.
- `mm02-2-003` (kusal)  
  REF: um 300 milligrammes uh amiodarone iv push  
  ASR: IM 300 milligrams, amiodarone, IV push.
- `hi01-0-009` (l2arctic-TNI)  
  REF: ketorolac fifteen milligrams into the vein diya  
  ASR: Ketorolac, 15 milligrams into the venti here.
- `cn04-0-019` (vctk-p251)  
  REF: patient takes normal saline two thousand five hundred ml daily  
  ASR: Patient takes normal saline, 2500 ml daily.
- `cn04-0-007` (l2arctic-RRBI)  
  REF: patient takes adenocard 10 milligram daily  
  ASR: Patient takes adenocortin, milligram daily.
- `cm05-0-010` (l2arctic-SVBI)  
  REF: Magnesium level 0.6  
  ASR: magnesium level 0.6.
