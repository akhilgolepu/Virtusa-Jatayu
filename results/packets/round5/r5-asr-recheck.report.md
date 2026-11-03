# ASR diagnosis `r5-asr-recheck` (dev, 100 clips, seed 3, commit `4662d9f`)

Synthetic speech (Piper). Extraction = rules extractor on the transcript (deterministic), so differences between rows come from the ASR setting alone. One setting changed per row against the baseline ({'model': 'small.en', 'beam': 5, 'vad': True, 'prompt': True, 'aliases': False, 'hotwords': False}).

| Setting | WER raw | WER normalised | Drug-term recall | Entity F1 (rules) | s/clip |
|---|---|---|---|---|---|
| baseline | 0.603 | 0.366 | 0.648 (n=88) | 0.750 | 0.237 |
| prompt+aliases | 0.613 | 0.364 | 0.670 (n=88) | 0.724 | 0.219 |
| hotwords | 0.626 | 0.381 | 0.614 (n=88) | 0.746 | 0.229 |
| large-v3-turbo | 0.660 | 0.419 | 0.523 (n=88) | 0.706 | 0.262 |
| distil-large-v3 | 0.697 | 0.508 | 0.318 (n=88) | 0.629 | 0.239 |

## By accent group (normalised WER / drug-term recall)

| Setting | US/GB WER | US/GB recall | Indian-accented WER | Indian-accented recall |
|---|---|---|---|---|
| baseline | 0.230 | 0.829 (n=35) | 0.467 | 0.528 (n=53) |
| prompt+aliases | 0.237 | 0.800 (n=35) | 0.458 | 0.585 (n=53) |
| hotwords | 0.255 | 0.743 (n=35) | 0.474 | 0.528 (n=53) |
| large-v3-turbo | 0.291 | 0.571 (n=35) | 0.515 | 0.491 (n=53) |
| distil-large-v3 | 0.335 | 0.543 (n=35) | 0.638 | 0.170 (n=53) |

## Language and extraction-level drug recall

| Setting | language used for decoding | Whisper's own detection (not forced) | drug hits credited via a brand/alias | drug recall after the extractor's lexicon/phonetic matcher |
|---|---|---|---|---|
| baseline | {'en': 100} | n/a (.en model) | 17 | 0.773 |
| prompt+aliases | {'en': 100} | n/a (.en model) | 18 | 0.750 |
| hotwords | {'en': 100} | n/a (.en model) | 20 | 0.795 |
| large-v3-turbo | {'en': 100} | {'en': 100} | 12 | 0.705 |
| distil-large-v3 | {'en': 100} | {'en': 100} | 12 | 0.614 |

## Cost (ASR alone; VRAM from nvidia-smi, includes the Windows desktop's share)

| Setting | load s | s/clip | VRAM before | VRAM peak | added | prompt names dropped | hotword tokens |
|---|---|---|---|---|---|---|---|
| baseline | 2.61 | 0.237 | 2491 | 3276 | 785 | 0 | 0 |
| prompt+aliases | 0.78 | 0.219 | 2587 | 3088 | 501 | 75 | 0 |
| hotwords | 0.77 | 0.229 | 2591 | 3158 | 567 | 0 | 220 |
| large-v3-turbo | 3.02 | 0.262 | 2589 | 3956 | 1367 | 0 | 0 |
| distil-large-v3 | 2.83 | 0.239 | 2668 | 3922 | 1254 | 0 | 0 |

WER raw = lowercase, punctuation stripped (the definition used in round 2). WER normalised = the pipeline's number normaliser + unit/route words mapped to lexicon codes, on reference AND hypothesis.
Drug-term recall = gold drugs whose name the lexicon recognises in the reference and that also appear in the transcript; the round-2 surface-string recall on the baseline is 0.670.

## Per field, baseline (entity F1, rules extractor)

| Field | F1 |
|---|---|
| drug | 0.866 |
| dose_value | 0.750 |
| dose_unit | 0.740 |
| route | 0.692 |
| time | 0.605 |
| procedure | 0.759 |

## Normalised WER by voice

| Voice | baseline | prompt+aliases | hotwords | large-v3-turbo | distil-large-v3 |
|---|---|---|---|---|---|
| alan | 0.100 | 0.100 | 0.140 | 0.140 | 0.160 |
| amy | 0.200 | 0.200 | 0.200 | 0.229 | 0.229 |
| kusal | 0.205 | 0.205 | 0.282 | 0.462 | 0.487 |
| l2arctic-ASI | 0.681 | 0.638 | 0.681 | 0.723 | 0.894 |
| l2arctic-RRBI | 0.442 | 0.423 | 0.385 | 0.365 | 0.731 |
| l2arctic-SVBI | 0.690 | 0.552 | 0.586 | 0.793 | 0.966 |
| l2arctic-TNI | 0.516 | 0.500 | 0.516 | 0.656 | 0.703 |
| lessac | 0.167 | 0.278 | 0.222 | 0.278 | 0.222 |
| libritts_r-0 | 0.400 | 0.420 | 0.380 | 0.380 | 0.520 |
| ryan | 0.214 | 0.214 | 0.214 | 0.321 | 0.286 |
| southern_female | 0.259 | 0.241 | 0.293 | 0.259 | 0.345 |
| vctk-p248 | 0.431 | 0.448 | 0.448 | 0.483 | 0.466 |
| vctk-p251 | 0.319 | 0.333 | 0.420 | 0.464 | 0.522 |
| vctk-p376 | 0.352 | 0.407 | 0.370 | 0.259 | 0.407 |

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
