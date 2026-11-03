# Evidence packet — evaluator round 5 + addendum (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only). Round-5 items and
addendum A–F only. **Dev data only**: no pipeline or speech run on test or final_test. Nothing merged or pushed, no
history rewritten, no co-author lines. Every round-5 run started on a clean tree (`run_log.jsonl`: `dirty: false`).

Commits (local): `4662d9f` (ASR re-check tooling) · `f86c458` (rules default, low_asr_confidence, procedure
negation) · `ecd7a47` (README, sealed /record, import) · `4279edd` · `0cdc6e2` (context cues) · `0904591`…`02e6fb0`
(latency) · `feb79b6` (commit map, G0, DECISIONS) · packet after.

## Protocol slip (disclosed)

To see the `/record` prompt format I printed the first two lines of `data/recordings/prompts.jsonl` to my console.
Both were **test-split prompts** (one sentence each, with gold entries). Nothing was written to any file or result,
and no tool was tuned on them. After that I looked at counts only (60 dev, 180 test prompts).

## 1. ASR re-check

`r5-asr-recheck.report.md`; same 100 dev clips as round 4.

- **Language.** English was already forced in every transcription (`language="en"` in `jatayu/asr.py` since round 1);
  the earlier runs did not save the detected language. The re-run records it:

  | | small.en | + brands in prompt | hotwords | large-v3-turbo | distil-large-v3 |
  |---|---|---|---|---|---|
  | Decoding language | en 100/100 | en 100/100 | en 100/100 | en 100/100 | en 100/100 |
  | Whisper's own detection (not forced) | n/a (.en model) | n/a | n/a | **en 100/100** | **en 100/100** |

  All transcripts are English: 0 non-ASCII, 0 empty.

- **The metric is alias-aware.** `drugs_heard` maps every lexicon name (generic or brand) to the generic drug. The test
  `test_drug_term_recall_is_alias_aware` covers Narcan, Zofran, Calpol, adrenaline and mag sulph. On small.en, 17 hits
  are credited through a brand name only. Nothing needed fixing, so the five options' numbers equal round 4's:

  | Option | Drug-term recall | US/GB | Indian-accented | Drug recall after the extractor's matcher | Entity F1 | s/clip |
  |---|---|---|---|---|---|---|
  | **small.en, generic prompt (kept)** | **0.648** | 0.829 | 0.528 | 0.773 | **0.750** | 0.24 |
  | + brands in prompt | 0.671 | 0.800 | 0.585 | 0.750 | 0.724 | 0.25 |
  | hotwords | 0.614 | 0.743 | 0.528 | 0.795 | 0.746 | 0.27 |
  | large-v3-turbo | 0.523 | 0.571 | 0.491 | 0.705 | 0.706 | 0.36 |
  | distil-large-v3 | 0.318 | 0.543 | 0.170 | 0.614 | 0.629 | 0.33 |

- **Why turbo and distil score lower.** They are English and fluent, but they misspell drug names ("Diffenhydramine",
  "Pentazocene", "Calpel"). Exact name matching doesn't credit those, and the extractor's matcher only partly recovers
  them.
- **Decision (DECISIONS): unchanged, small.en with the generic prompt.** Drug-term recall stays below the plan's 0.90
  trigger.

## 2. Default extractor: rules

- `JATAYU_EXTRACTOR` now defaults to `rules`, as do the API form and the capture-screen selector (now "rules / hybrid /
  llm only"; UI rebuilt). Hybrid and LLM-only stay selectable.
- The measured reason is in the repository README (`project_README.md` here) and DECISIONS: the LLM added nothing measurable (speech F1
  0.673 vs 0.673; off-template 0.948 vs 0.950) and costs ~0.6–0.9 s per utterance and 3.35 GB of VRAM.
- Test: `tests/test_api.py::test_default_extractor_is_rules_and_others_stay_selectable`.

## 3. Low ASR confidence

- `low_asr_confidence` is now **severity low and informational**. It does **not** count as a catch in the headline
  (strict) dangerous-error rate.
- The **lenient row** (secondary, in every report) counts it, as it counts `weight_based_dose`.
- Measured flag rates on dev speech at p < 0.2: **24.2% of wrong records, 12.8% of correct records**.
- DECISIONS line 66 has been rewritten to match (addendum E).
- Dev speech, rules, round-5 code (`r5-dev-audio-rules`): dangerous errors **1/440 strict, 1/440 lenient**. The one
  error ("fifty" → "15", heard with p = 0.93) has no low-confidence flag either way.

## 4. Blind set — NOT DONE

`eval/offtemplate_blind_v1.yaml` has not been received: it is not in the repository or anywhere on this machine. It is
evaluator-authored, so I have not written it. When it arrives, I will follow its header protocol exactly: convert with
a script, run rules / hybrid / LLM-only once, log in `run_log`, report aggregates per tier, then analyse.

## 5. "no IV access" — negation on procedures (dev only)

- A procedure with a negation or failure cue in the 4 words before it ("no", "not", "unable", "failed", "couldn't",
  "cannot"…) is flagged `possible_not_given` (high; FHIR `not-done`), not recorded as done.
- The xfail case `ot-rt-sc-2` now passes. Two dev cases were added: "unable to get IV access" and "failed intubation".
- The off-template set has 59 records; rules: F1 0.952, 2/59 dangerous (the two route corrections, xfail)
  (`r5-offtemplate-rules.report.md`).

## 6. Real recordings

The repository README (`project_README.md` here) gives the exact commands.

- **A. In the app:** record at `http://localhost:8000/record` (60 dev and 180 test prompts across six conditions), then
  `python -m scripts.import_real --from-recordings --speaker S01`.
- **B. Any recorder:** WAV files plus a `refs.tsv`, then `python -m scripts.import_real --split dev|test --speaker S01
  --refs …`.
- **Comparison:** `python -m eval.real_wer --tag real-vs-piper --piper results/r4-dev-audio-hybrid-v2`.
- **Test stays sealed:**
  - imported real test clips are refused by `load_real` and `eval/real_wer.py`;
  - **new:** the `/record` page no longer transcribes test takes (status `sealed`, no ASR text or WER). Before, it ran
    Whisper on each test take and showed the WER;
  - tests in `tests/test_corpus.py` and `tests/test_real_import.py`.

## Addendum

**A. Commit map.**

- **Map:** `commit-map.txt` (also `docs/commit-map.txt`) covers every hash referenced in the run logs,
  `setup_check.json`, the metrics files, the packet READMEs and DECISIONS: 13 rewritten (same tree), 32 made after the
  rewrite, **0 not found**.
- **Tag:** `git rev-parse m1-pass^{commit}` = `9bfa6c3…` (old `760ebd2`).
- **G0 re-stamp:** `setup_check.json` was re-run in a clean worktree checked out at `m1-pass`. JSON `commit`, G0 README
  and tag all read **`9bfa6c3`**; all_pass true, LLM included in the offline check.
- No further history rewriting without asking (DECISIONS).

**B. Negation on dev speech** (rules, counts only; `r5-negation-breakdown-before/after.report.md`):

| | Before | After the fix |
|---|---|---|
| Administration-status errors | 4/40: all 4 cue lost in the transcript as seen by the extractor | **2/40**: both ASR lost the cue |
| Context errors (not given + measurement) | 10/80: 4 + 6, all as above | **5/80**: 2 + 3, all ASR lost the cue |

Two kinds were fixable in the extractor:

- the cue inside a hyphenated token ("on-home");
- sound-alike spellings of "serum" ("serm", "ceram").

Cues are now read inside hyphenated tokens and by phonetic key, for cue words of 5+ letters with keys of 3+ letters
(this rejects "with" as "without"). Not fixable: "Onhone", "On the form of", "Sir"/"Sera"/"Seven" magnesium. No
regression on typed dev (0/80, 0/40) or off-template.

**C. End-to-end latency** (`r5-e2e-latency.report.md`, raw timings in `e2e_latency_timings.csv`):

- 30 runs of a 10-second dictation (8.8 s of Piper speech padded to 10 s), from the end of the recording (upload sent)
  to the parsed confirm-screen payload.
- Real HTTP server on localhost, default extractor rules, faster-whisper small.en on the RTX 5060.
- **p50 0.387 s, p95 0.422 s** (min 0.346, max 0.426; ASR part p50 0.337 s). The first run with model load took 2.2 s.
- Browser audio encoding and screen paint are not included.
- A first run used an 11.3 s dictation cut to 10 s, which lost the last words. It is kept as
  `results/r5-e2e-latency-TRIMMED-superseded/` and the script now refuses speech longer than 10 s.

**D. Wording.** In `wording_draft.md` (copy here; the original is in round3), the "medic's review has to catch"
sentence is replaced with "…that residual risk depends on read-back confirmation, whose effectiveness we have not
measured." I added a short lead-in so the sentence has a subject.

**E.** DECISIONS line 66 is revised (see 3).

**F.** Routes coverage from round 4 stands; the rest is above.

## Tests

Full suite, nothing deselected, GPU model tests included, at `feb79b6`: **395 passed, 12 xfailed, 0 skipped,
0 failed** (`pytest_output.txt`).

## Files to attach

The whole folder `results/packets/round5/`:

- `README.md` (this file);
- the report copies;
- `e2e_latency_timings.csv`;
- `commit-map.txt`;
- `project_README.md` (copy of the repository README: run, extractor choice, recording commands);
- `wording_draft.md`;
- `pytest_output.txt`;
- `run_log.jsonl`.

Also attach the G0 folder `results/packets/g0/` (re-stamped).
