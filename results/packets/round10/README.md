# Evidence packet — evaluator round 10 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only).

What this round did not touch:

- No pipeline run on test or final_test. No real test clip read; the real-test runner ran only on dummy clips in
  throwaway folders.
- No merge into `main`, no force push, no history rewrite.

Everything below is **dev** data (synthetic speech, typed sentences, or the spent blind set). Item 2 is **in-sample**.

| # | Item | Status |
|---|---|---|
| 1 | Metric correction: new headline dangerous error, every dev run re-scored, old and new side by side | Done. The headline is higher everywhere; the old figure is now a labelled secondary row |
| 2 | Tick cost: classify the 49, ticks per note, exemption | Done, in-sample: only generic-name variants exempted (49 → 29 ticked), all 4 wrong drugs still ticked; aliases/brands NOT exempted (would have un-ticked 2 of 4) |
| 3 | Drug identity first on the confirm screen and in the read-back | Done; presentation only, not claimed to catch, not measured |
| 4 | Real-test runner with three gates, aggregate only, tested on dummy clips | Done (`eval/real_test.py`, 8 tests) |
| 5 | Docs: guard in-sample and hand-labelled by one labeller; drug-identity limitation | Done |

## 1. Metric correction

**New headline** (`dangerous_error_r10`, `eval/metrics.py`). A wrong drug, dose, unit, route or administration status
**recorded** without a flag the medic must tick (severity high: the confirm API refuses until it is acknowledged).
The denominator is all given and not-given gold records.

- **Wrong drug:** a gold medication with no same-drug prediction, paired in order with an unmatched predicted
  medication of the same utterance (the drug recorded instead). The old scorer saw this as a miss plus an extra entry.
- **Wrong dose, unit or route:** a value present and different from gold. A field left empty shows "not stated" on the
  confirm screen; that is an omission, counted apart and not as dangerous. This choice is mine; the old metric counted
  empties.
- **Status:** a not-given record recorded without `possible_not_given` and with no other high flag.
- **What catches:** any high flag, also one about another field. This is the round-10 definition, read literally.

**Old metric:** kept as a labelled secondary row, "matched-drug only".

**Re-scored offline from errors.jsonl** (`eval/rescore_r10.py`, as in round 2): every dev run, in
`r10-rescore.report.md` and `.json`.

- **Exact part:** wrong dose, unit or route; those rows stored their flag codes, and a code's severity is fixed.
- **Upper-bound part (≤):** runs before round 10 stored no flags on extra predictions, and no row for a not-given record
  whose fields were all right. So a wrong drug counts as caught only when a high flag follows for certain from the
  recorded values (validator, missing dose/unit); otherwise it counts as uncaught.
- **Exact runs:** the scorer now stores everything, so I also ran the round-10 scorer on the same inputs. `r10a` is the
  round-9 code; `r10b` is the round-10 code, after the item-2 exemption.

| Set | Run | Old: matched-drug only | **New headline** |
|---|---|---|---|
| **Dev speech** (480 clips) | rules, round 5 (re-scored) | 1 / 440 | ≤ 6 / 480 |
| | rules, round 9 (re-scored) | 1 / 440 | ≤ 5 / 480 |
| | rules, round-9 code, new scorer (`r10a`) | 1 / 440 | **5 / 480** (4 wrong dose/unit/route, 1 wrong drug) |
| | rules, round-10 code (`r10b`) | 1 / 440 | **6 / 480** (5 wrong dose/unit/route, 1 wrong drug) |
| | hybrid · LLM-only, round 4 (re-scored) | 3 · 0 / 440 | ≤ 11 · ≤ 16 / 480 |
| **Noisy speech** (160 utterances × 20/10/5 dB) | hybrid, round 3 (re-scored) | 3 / 240 | ≤ 10 / 360 |
| | rules, `r10a` and `r10b` | 3 / 240 | **6 / 360** (4 wrong dose/unit/route, 2 wrong drug) |
| **Blind v1** (32 sentences) | as-run: rules · hybrid · LLM-only (re-scored) | 1 · 1 · 0 / 34 | ≤ 3 · ≤ 3 · ≤ 3 / 37 |
| | converter-corrected (re-scored) | 1 · 1 · 0 / 34 | 2 · 2 · ≤ 2 / 37 |
| | round-9 code (`r10a`): rules · hybrid · LLM-only | 0 · 0 · 0 / 34 | **1 · 2 · 1 / 37** |
| | round-10 code (`r10b`), rules | 0 / 34 | **1 / 37** |

Per tier, at round-9 code (blind v1, `r10a`; headline / old): core 1 · 1 · 1 of 33 / 0 of 30; stretch 0 · 1 · 0 of 4 /
0 of 4.

**Why the counts grew:**

- medium flags no longer catch (`low_confidence`, the medium route `field_missing`, `dose_below_range`);
- a wrong drug is counted at all;
- not-given records are in the denominator.

The re-scored round-9 dev speech bound (≤ 5) equals the exact figure for the same code (`r10a`, 5), so the bound was
tight there.

**Docs:**

- `README.md`, `docs/architecture.md` (§5, §6, new §6c) and `datagen/README.md` state the headline next to every old
  figure; no document states the old figure alone.
- The old packets are left as they were.
- `DECISIONS.md` logs the change.
- Typed dev: 0 / 480 (old 0 / 440). Off-template, round-10 code: 3 / 71 (old 2 / 59).

## 2. Tick cost of the sound-alike flag (IN-SAMPLE)

`eval/tick_cost.py`. Every drug matched by sound on dev speech is put into one of three classes:

- a spelling variant of the **generic** name (≤ 2 letter edits);
- a variant of a **listed alias or brand** of the same drug (≤ 2 edits);
- a **look-alike** (neither).

The 2-edit line and the classes were chosen while looking at these same clips.

| Class | Correct (of the 49 ticked) | Wrong (of 4) |
|---|---|---|
| Generic-name spelling variant | 20 | 0 |
| Alias/brand spelling variant | 19 | **2** ("salin" ~ alias "saline", 1 edit; "At event" ~ brand "Atrovent", 2 edits) |
| Look-alike | 10 | 2 ("ASTEL", "chadrin") |

Alias and spelling variants together are 39 of 49, most of them. **But exempting both would un-tick 2 of the 4 true
wrong drugs.** Those 2 still had other high flags here (`dose_out_of_range`; `possible_not_given` /
`unit_not_allowed`), but that is luck in this sample. So **only generic-name variants are exempted**: medium
`low_confidence` ("Heard X, recorded Y"), heard word still shown, no tick.

Ticks per note on dev speech (one note = one clip; ticks = distinct high-flag codes per entry, summed):

| Option | All ticks / note: mean · p90 · max | Sound ticks / note: mean · p90 · max | Correct matches ticked | Wrong drugs still sound-ticked |
|---|---|---|---|---|
| Round 9 rule | 0.760 · 2 · 5 | 0.110 · 1 · 2 | 49 | 4 of 4 |
| **Exempt generic-name variants (adopted)** | **0.719 · 2 · 5** | **0.069 · 0 · 2** | **29** | **4 of 4** |
| Exempt generic + alias/brand variants (not adopted) | 0.675 · 2 · 4 | 0.025 · 0 · 1 | 10 | 2 of 4 |

Reports: `r10-tick-cost-before.report.md` (with every case listed) and `r10-tick-cost-after.report.md`; the drug
identity after the change is in `r10-drug-identity.report.md`. Typed dev text and off-template are unchanged
(`r10b-dev-text-rules`, `r10b-offtemplate-rules`).

**Cost under the new headline:** one wrong dose, "furosenide 14 mg" for furosemide 40 mg, was "caught" only by the
drug's sound tick. It is now uncaught, so dev speech goes 5 → 6 of 480 (`r10a` → `r10b`).

**Tests:**

- canonical variants need no tick but show the heard word;
- brand variants (zofren, lasicks, ketalor, adrenelin) still need the tick;
- the 4 dev wrong drugs are not generic-name variants.

## 3. Drug identity first (the 6 exact-word wrong drugs) — presentation only

**Confirm screen** (`web/src/components/EntryCard.tsx`; screenshots `ui-confirm-card.png`, `ui-confirm-dialog.png`,
taken on a throwaway server with synthetic input):

- the drug name is the largest element of each card, labelled DRUG, with the heard word beside it when different;
- units show in full ("mg · milligrams");
- the tick dialog opens with a boxed DRUG / HEARD panel, and its button says "Confirm <drug>".

**Read-back** (`jatayu/readback.py`):

- "Drug: X." is a phrase of its own, spoken first and slowly (Piper length scale 1.6, the voice's normal speed is
  1.0), then a pause;
- then "Heard as Y." if the heard words differ;
- then dose, route, time and warnings at normal speed, with units in full ("milligrams", "micrograms").

A test checks that the drug phrase audio is more than 1.3× the length of the normal-speed phrase.

**Not claimed:** that this catches the exact-word wrong drugs. Nothing new was measured; the human test comes later.

## 4. Real-test runner

`eval/real_test.py`. **Before reading any clip** it refuses (exit 2, nothing written, no run_log row) unless all three
hold:

1. the working tree is clean;
2. the real test manifest's SHA-256 is frozen in `eval/frozen.sha256` and the manifest still matches it.
   `--freeze-manifest` writes the hash once and never overwrites a different one;
3. the evaluator's release file `eval/real_test_release.json` exists and names that same hash.

**Then:**

- every clip is checked against the manifest (a changed clip stops the run);
- each clip is transcribed, extracted with rules (the demo extractor), validated, and scored against its prompt's gold
  entries.

**Output:** `metrics.json` and `report.md` only. They hold clip and speaker counts, WER (normalised and raw),
drug-term recall, entity P/R/F1, the headline and old dangerous errors, and admin-status errors. No transcript,
per-clip or per-speaker result, or error list is written. One run_log row (split `real-test`, with the manifest hash).

**Tests:** `test_real_test_runner.py`, 8 tests, all on **dummy clips in `tmp_path`** (copies of the test fixture clip):

- refusal on a dirty tree, an unfrozen hash, a changed manifest, a missing or wrong release file, and a changed clip;
- freezing never overwrites;
- the output holds no transcript, reference text or clip id;
- one model test with the real Whisper on the dummy clips.

**Never run on real test clips** (none are imported). Freeze checklist B3 now points to it; B2's mechanism exists.

## 5. Docs

**`architecture.md`:**

- **§6:** the `drug_not_in_lexicon` precision/recall row is labelled **IN-SAMPLE**: guard and labels were made on the
  same dev clips, by **one labeller** (the AI coding assistant used on this project), not reviewed by a second person,
  no agreement measured. The same wording is in `eval/unknown_drug_labels_dev.yaml`.
- **§7, the drug-identity limitation:**
  - 6 of the 10 wrong drugs recorded as known drugs on dev speech came from an exact wrong drug word;
  - nothing flags their identity, and 1 of the 6 had no high flag at all;
  - whether the drug-first screen and read-back help is unmeasured.
- **§7 also lists:** the tick exemption, in-sample.
- **§6c:** the old-vs-new table above.

## Notes

- **Failed R4 check attempts:** `r10-fhir-r4-check` has 3 run_log rows. The first two crashed on a relative `--bundle`
  path after logging, with no output; the third (absolute path) is the result: whole bundle and 20/20 resources valid.
  The script now resolves the path (`4fe077e`).
- **FHIR example sound-alike:** the example now uses "lasicks", because "furosemid" is a generic-name variant and is
  exempt. All 13 checks pass.
- **Blind v1 F1 at round-10 code:** rules entity F1 is 0.870 (core 0.906). The round-8 converter-corrected run (0.892)
  was at pre-round-8 code. The difference comes from the round-8/9 rules on this set: diclofenac kept as an unknown
  drug, and a concentration no longer recorded as a dose.

## Files changed (code, tests, docs; results not listed)

- **Metric and re-scoring:** `eval/metrics.py`, `eval/run.py` (reports), `eval/blind.py` (headline column,
  `--extractors`), `eval/rescore_r10.py` (new), `eval/tick_cost.py` (new).
- **Exemption:** `jatayu/extract/rules.py`.
- **Read-back:** `jatayu/readback.py`; `jatayu/api.py` (read-back WAV).
- **UI:** `web/src/components/EntryCard.tsx`, `web/src/app.css`; the rebuilt `jatayu/web/dist`.
- **Real-test runner:** `eval/real_test.py` (new).
- **Scripts:** `scripts/fhir_pdf_example.py` (sound-alike example word), `scripts/fhir_r4_check.py` (path fix).
- **Tests:**
  - new: `tests/test_metric_r10.py`, `tests/test_real_test_runner.py`;
  - updated: `tests/test_readback.py`, `tests/test_round9_drug_identity.py`, `tests/test_hybrid.py`,
    `tests/test_incident.py`.
- **Docs and data:** `README.md`, `docs/architecture.md`, `docs/freeze_checklist.md`, `datagen/README.md`,
  `DECISIONS.md`, `eval/unknown_drug_labels_dev.yaml` (header).

## Tests and freeze check

- **Full suite at `4fe077e`:** 460 passed, 12 xfailed, 0 skipped, 0 failed, model tests included
  (`pytest_output.txt`).
- **`freeze_check --pytest` on the pushed tree (`28cd431`):** FREEZE CHECK PASSED (`freeze_check.json`).
- **Still open before the freeze:**
  - B1: the real recordings are not imported;
  - B2: their manifest hash can't be frozen until they are;
  - B5: the evaluator's sign-off.

## Files to attach

The whole folder `results/packets/round10/`:

- `README.md`;
- metric: `r10-rescore.report.md`, `r10-rescore.json`, `r10a-dev-audio-rules`, `r10b-dev-audio-rules`,
  `r10a-dev-noise-rules`, `r10b-dev-noise-rules`, `r10a-blind-v1`, `r10b-blind-v1-rules` (`.report.md`),
  `test_metric_r10.py`;
- tick cost: `r10-tick-cost-before.report.md`, `r10-tick-cost-after.report.md`, `r10-drug-identity.report.md`,
  `r10b-dev-text-rules.report.md`, `r10b-offtemplate-rules.report.md`;
- drug first: `ui-confirm-card.png`, `ui-confirm-dialog.png`, `test_readback.py`;
- runner: `test_real_test_runner.py`;
- FHIR: `r10-fhir-pdf-example.report.md`, `r10-fhir-r4-check.report.md`;
- docs: `architecture.md`, `freeze_checklist.md`, `project_README.md`;
- `pytest_output.txt`, `freeze_check.json`, `run_log.jsonl`.
