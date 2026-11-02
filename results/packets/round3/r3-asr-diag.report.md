# ASR diagnosis `r3-asr-diag` (dev, 100 clips, seed 3, commit `cb82312-dirty`)

Synthetic speech (Piper). Extraction = rules extractor on the transcript (deterministic), so differences between rows come from the ASR setting alone. One setting changed per row against the baseline ({'model': 'small.en', 'beam': 5, 'vad': True, 'prompt': True}).

| Setting | WER raw | WER normalised | Drug-term recall | Entity F1 (rules) | s/clip |
|---|---|---|---|---|---|
| baseline | 0.616 | 0.398 | 0.636 (n=88) | 0.671 | 0.221 |
| vad off | 0.616 | 0.398 | 0.636 (n=88) | 0.671 | 0.203 |
| prompt off | 0.691 | 0.519 | 0.341 (n=88) | 0.448 | 0.199 |
| beam 1 | 0.629 | 0.415 | 0.625 (n=88) | 0.663 | 0.165 |
| beam 10 | 0.617 | 0.409 | 0.648 (n=88) | 0.677 | 0.306 |
| medium.en | 0.632 | 0.429 | 0.625 (n=88) | 0.639 | 0.345 |

WER raw = lowercase, punctuation stripped (the definition used in round 2). WER normalised = the pipeline's number normaliser + unit/route words mapped to lexicon codes, on reference AND hypothesis.
Drug-term recall = gold drugs whose name the lexicon recognises in the reference and that also appear in the transcript; the round-2 surface-string recall on the baseline is 0.659.

## Per field, baseline (entity F1, rules extractor)

| Field | F1 |
|---|---|
| drug | 0.797 |
| dose_value | 0.683 |
| dose_unit | 0.661 |
| route | 0.571 |
| time | 0.507 |
| procedure | 0.759 |

## Normalised WER by voice

| Voice | baseline | vad off | prompt off | beam 1 | beam 10 | medium.en |
|---|---|---|---|---|---|---|
| alan | 0.160 | 0.160 | 0.200 | 0.180 | 0.160 | 0.220 |
| amy | 0.200 | 0.200 | 0.286 | 0.200 | 0.200 | 0.171 |
| kusal | 0.282 | 0.282 | 0.487 | 0.282 | 0.282 | 0.410 |
| l2arctic-ASI | 0.638 | 0.638 | 0.872 | 0.617 | 0.681 | 0.723 |
| l2arctic-RRBI | 0.500 | 0.500 | 0.865 | 0.577 | 0.500 | 0.673 |
| l2arctic-SVBI | 0.552 | 0.552 | 0.724 | 0.586 | 0.621 | 0.897 |
| l2arctic-TNI | 0.500 | 0.500 | 0.797 | 0.547 | 0.516 | 0.547 |
| lessac | 0.222 | 0.222 | 0.444 | 0.278 | 0.222 | 0.278 |
| libritts_r-0 | 0.460 | 0.460 | 0.520 | 0.520 | 0.460 | 0.420 |
| ryan | 0.214 | 0.214 | 0.250 | 0.179 | 0.214 | 0.286 |
| southern_female | 0.414 | 0.414 | 0.379 | 0.362 | 0.414 | 0.276 |
| vctk-p248 | 0.431 | 0.431 | 0.431 | 0.414 | 0.448 | 0.431 |
| vctk-p251 | 0.391 | 0.391 | 0.507 | 0.449 | 0.435 | 0.391 |
| vctk-p376 | 0.370 | 0.370 | 0.333 | 0.370 | 0.333 | 0.259 |

## Audio reaching Whisper

- file_format: {'16000 Hz, 1 ch, 16 bit': 100}
- decoded_to_whisper: {'1-D float32': 100}
- sample_rate_given_to_whisper: 16000
- clips_with_duration_mismatch_over_10ms: 0

## 10 random (reference, transcript) pairs, baseline

- `mb07-0-007` (vctk-p251)  
  REF: Calpol, six hundred fifty milligram, io, 10 mins ago  
  ASR: towel bowl, 650 mg a year, 10 minutes ago.
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
  ASR: I'm 300 milligrams of amiodarone roman IV push.
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
