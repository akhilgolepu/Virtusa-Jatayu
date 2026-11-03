# Evidence packet — evaluator round 4 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only). Round-4 items only.
**Dev data only**: no pipeline or speech run on test or final_test, no individual test record anywhere. Nothing
merged or pushed. Commits carry no co-author line.

Commits (local): `74d9b3e` (routes) · `6f375cf` (phonetic match, self-correction) · `c39d8db` (ASR prompt,
hotwords, word probabilities, low_asr_confidence) · `f64572b` (test audio + manifests, real-recording import) ·
`a117f45` · `212d5e3` (threshold) · `4b95fa2` (two fixes found by the dev run) · then results/packets.
Every round-4 run started on a clean tree (`dirty: false` in `run_log.jsonl`). The final runs are the `-v2` ones at
`4b95fa2`; the runs before that fix are kept with a NOTE.

## 1. Drug-term recall (0.574; trigger < 0.90 — not cleared)

**Prompt budget.** The vocabulary prompt was 199 of the 223 tokens Whisper keeps, so **nothing was dropped by
truncation**. The real gap: it listed the 36 generic names and **none of the 109 aliases/brands** (Calpol, Narcan,
Zofran, Toradol…). With every generic first, only 7 brands fit in 223 tokens (75 do not); a hotwords block carries
another ~220 tokens of brands.

Same 100 dev clips, rules extractor on each transcript (`r4-asr-options.report.md`, `r4-asr-options-distil.report.md`):

| Option | Drug-term recall | US/GB recall | Indian-accented recall | Entity F1 | WER norm. | s/clip | VRAM added (alone) | Peak with Qwen loaded |
|---|---|---|---|---|---|---|---|---|
| **small.en, generic prompt (kept)** | **0.648** | 0.829 | 0.528 | **0.750** | **0.363** | 0.24 | +0.8 GB | 6.5 GB |
| small.en, prompt + brands | 0.671 | 0.800 | 0.585 | 0.724 | 0.364 | 0.25 | +0.6 GB | — |
| small.en, + hotwords | 0.614 | 0.743 | 0.528 | 0.746 | 0.381 | 0.27 | +0.9 GB | — |
| large-v3-turbo | 0.523 | 0.571 | 0.491 | 0.706 | 0.419 | 0.36 | +1.5 GB | 7.2 GB (fits) |
| large-v3-turbo + hotwords | 0.443 | 0.543 | 0.377 | 0.534 | 0.585 | 0.37 | +1.6 GB | — |
| distil-large-v3 | 0.318 | 0.543 | 0.170 | 0.629 | 0.508 | 0.33 | +1.1 GB | 7.1 GB (fits) |

Both large models fit next to Qwen on the 8 GB card, so no swapping was needed; they are less accurate on this
synthetic audio. **Decision (DECISIONS 2026-11-03): small.en with the generic prompt.** No option improves both
recall and F1.

**Phonetic / fuzzy match** (rules extractor): adjacent unknown words joined and compared by a sound key against
every generic and brand name ("adenol card" → adenosine, "ketool" → ketorolac). The threshold was chosen on dev
transcripts by drug F1. Every fuzzy or phonetic match now always carries `low_confidence`; before, a single-word
fuzzy score ≥ 0.95 passed unflagged. On fixed dev transcripts (`r4-phonetic-sweep.report.md`):

| | Drug precision | Drug recall | Drug F1 | Entity F1 |
|---|---|---|---|---|
| before | 0.977 | 0.633 | 0.768 | 0.632 |
| **with phonetic match** | 0.970 | **0.691** | **0.807** | **0.670** |

Full dev speech after round 4, hybrid (`r4-dev-audio-hybrid-v2`):

- drug-term recall (ASR) **0.574** (n = 460);
- normalised WER 0.406 (US 0.257, GB 0.260, Indian-accented 0.532);
- entity F1 **0.673** (round 3: 0.633); by accent: US 0.791, GB 0.805, Indian-accented 0.558 (round 3: 0.523).

## 2. Self-corrections

The rules extractor marks a spoken correction (`self_correction`, informational, not a catch) and takes the number
right after the marker. The hybrid keeps that dose when the LLM linked another number.

| Round-3 dangerous self-correction cases | Now |
|---|---|
| hybrid, typed text: 5 | **5/5 correct** |
| hybrid, speech: 2 | **2/2 correct** |
| LLM-only, typed text: 3 | unchanged (that extractor has no rules layer) |

- Dev typed text, hybrid: dangerous errors **5/440 → 0/440**. Dev speech, hybrid: **3/440 → 1/440**; the one left is
  ASR.
- **Bugs found and fixed.** The first round-4 speech run exposed two bugs in this change, fixed in `4b95fa2`: the
  correction took the clause's last number ("800, sorry, 1000 mg … 10 men ago" → 10), and a missing-unit flag was
  dropped. Before-fix runs: `results/r4-dev-*` without `-v2`.

## 3. Low ASR confidence

Whisper word probabilities are now kept, with character offsets (`AsrResult.words`). A drug, dose or unit read from
a word with p < threshold gets `low_asr_confidence` (medium), which counts as a catch in the dangerous-error rate.

- **Threshold:** chosen on dev only, by a criterion fixed before looking: the largest gap between wrong records
  flagged and correct records flagged. Chosen: **p < 0.2** (`r4-asr-threshold.report.md`).
- **At p < 0.2:** 24.2% of wrong records are flagged; **12.8% of correct records** are flagged.
- **Dangerous errors:** 1/440 without the flag and 1/440 with it. The remaining error ("fifty" → "15") was heard with
  p = 0.93. This is a weak signal on synthetic audio.

## 4. Hybrid justification

Final runs, dev:

| | Speech (480 clips, same transcripts) | Off-template (57 records) | Typed template dev |
|---|---|---|---|
| rules | F1 0.673 · dangerous 1/440 · admin-status 4/40 | F1 0.948 · 2/57 · 3/9 | F1 1.000 · 0/440 |
| LLM only | F1 0.527 · 0/440 · **21/40** | F1 0.894 · 1/57 · 3/9 | (round 3: 0.897 · 3/440 · 37/40) |
| hybrid | F1 0.673 · 1/440 · 4/40 | F1 0.950 · 2/57 · 3/9 | F1 0.992 · 0/440 |

**The LLM adds nothing measurable.** The hybrid costs about 0.6–0.9 s per utterance and 3.35 GB of VRAM. LLM-only is
worse everywhere, and on speech it records 21 of 40 not-given drugs as given.

Proposed framing (DECISIONS): a rules-first, lexicon-grounded extractor, with the local LLM as an optional linker
reported as an ablation. I recommend making `rules` the default extractor; not switched, for you to confirm.

## 5. Routes

Fixes:

- a written upper-case "IN" is intranasal (lower-case "in" never is);
- "i.n." and "sub cut" added.

Coverage:

- **Unit tests** (`tests/test_rules.py::test_route_forms`): 17 forms across IN, IO, SL, PR, NEB, INH and SC all parse.
- **Dev cases:** 14 route cases added to the off-template set. Rules and hybrid get **16/16** route instances right;
  LLM-only gets 14/16 (it misses 2 of the 4 intranasal ones).
- **Not a route problem:** one new case fails for another reason. "no IV access" is extracted as the procedure
  *IV cannulation*, because negation isn't applied to procedures (xfail with that reason).

## 6. Test audio

- **Re-rendered:** test and final_test, with the TTS route-spelling rule; 630 of 2,100 clips changed.
- **Frozen:** every clip, clean and noisy (4,802 and 3,602 files), is hashed into
  `data/audio/manifests/<split>.audio.sha256`. The two manifest hashes are in `frozen.sha256` (copy here).
  `eval.run` refuses speech on test/final_test unless every clip matches.
- **Not evaluated:** no speech evaluation was run on test or final_test.

## 7. Real recordings

**Import:** `python -m scripts.import_real --split dev|test --speaker S01 --refs refs.tsv`, where `refs.tsv` holds
one `audio path<TAB>reference text` per line. It writes:

- `data/real/<split>/<speaker>/<sha8>.wav`, as 16 kHz mono;
- `manifest.jsonl`, with id, speaker, path, SHA-256, reference, duration and source;
- `manifest.sha256`.

Speaker ids must be anonymous tokens. Re-importing the same audio is a no-op, and a changed clip is detected.

**Real test clips are sealed:** `load_real("test")` and `eval/real_wer.py --split test` refuse.

`eval/real_wer.py` compares real dev with Piper dev (normalised WER, raw WER and drug-term recall, per speaker):
`r4-real-vs-piper.report.md`. **No real recording exists yet**, so the report shows the Piper row and says so.
Tests: `tests/test_real_import.py`.

## Tests

`python -m pytest -m "not models"`: 364 passed, 13 xfailed, 0 failed at `4b95fa2`. The full suite including the GPU
model tests was not re-run this round; the last full run is M1's (343 passed at `9bfa6c3`).

## Changed beyond the list

- `self_correction` (informational) is a new flag.
- A fuzzy drug match is now always flagged.
- The off-template set grew to 54 cases.
- `results/r4-*` runs before the bug fix are kept, with NOTEs.

## Files to attach

The whole folder `results/packets/round4/`: this README, the report copies, `offtemplate_dev.yaml`,
`frozen.sha256` and `run_log.jsonl`.
