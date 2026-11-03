# ASR diagnosis `r4-asr-options-distil` (dev, 100 clips, seed 3, commit `f64572b-dirty`)

Synthetic speech (Piper). Extraction = rules extractor on the transcript (deterministic), so differences between rows come from the ASR setting alone. One setting changed per row against the baseline ({'model': 'small.en', 'beam': 5, 'vad': True, 'prompt': True, 'aliases': False, 'hotwords': False}).

| Setting | WER raw | WER normalised | Drug-term recall | Entity F1 (rules) | s/clip |
|---|---|---|---|---|---|
| baseline | 0.600 | 0.362 | 0.648 (n=88) | 0.750 | 0.239 |
| distil-large-v3 | 0.697 | 0.508 | 0.318 (n=88) | 0.629 | 0.33 |

## By accent group (normalised WER / drug-term recall)

| Setting | US/GB WER | US/GB recall | Indian-accented WER | Indian-accented recall |
|---|---|---|---|---|
| baseline | 0.230 | 0.829 (n=35) | 0.461 | 0.528 (n=53) |
| distil-large-v3 | 0.335 | 0.543 (n=35) | 0.638 | 0.170 (n=53) |

## Cost (ASR alone; VRAM from nvidia-smi, includes the Windows desktop's share)

| Setting | load s | s/clip | VRAM before | VRAM peak | added | prompt names dropped | hotword tokens |
|---|---|---|---|---|---|---|---|
| baseline | 1.82 | 0.239 | 2605 | 3451 | 846 | 0 | 0 |
| distil-large-v3 | 2.88 | 0.33 | 2984 | 4124 | 1140 | 0 | 0 |

## With Qwen3-4B loaded first (co-resident, as the hybrid runs)

| Model | VRAM peak MiB | fits in 8151 MiB |
|---|---|---|
| distil-large-v3 | 7126 | True |
| small.en | 6440 | True |

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

| Voice | baseline | distil-large-v3 |
|---|---|---|
| alan | 0.100 | 0.160 |
| amy | 0.200 | 0.229 |
| kusal | 0.205 | 0.487 |
| l2arctic-ASI | 0.681 | 0.894 |
| l2arctic-RRBI | 0.442 | 0.731 |
| l2arctic-SVBI | 0.621 | 0.966 |
| l2arctic-TNI | 0.516 | 0.703 |
| lessac | 0.167 | 0.222 |
| libritts_r-0 | 0.400 | 0.520 |
| ryan | 0.214 | 0.286 |
| southern_female | 0.259 | 0.345 |
| vctk-p248 | 0.431 | 0.466 |
| vctk-p251 | 0.319 | 0.522 |
| vctk-p376 | 0.352 | 0.407 |

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
