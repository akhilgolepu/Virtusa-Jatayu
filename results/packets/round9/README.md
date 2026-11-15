# Evidence packet — evaluator round 9 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only).

What this round did not touch:

- No pipeline run on test or final_test.
- No real-recording data read. The pre-flight and the freeze check skip `data/real` and `data/recordings`.
- No merge into `main`, no force push, no history rewrite.

Everything below is **dev** (synthetic speech or typed text) unless labelled otherwise.

| # | Item | Status |
|---|---|---|
| 1 | Wrong drug by sound: count, rule, "did you mean X?", tests, before/after | Done. The 4 sound-matched wrong drugs now need a tick; the 6 exact-word ones stay open (stated) |
| 2 | False unknown-drug entries: classify the 49, junk guard, precision/recall before/after | Done: precision 0.776 → 0.881, recall 1.000 → 0.974 |
| 3 | FHIR: patient reference; strict R4 with no placeholder; what was checked and what was not | Done: whole Bundle and 20/20 resources valid, nothing patched |
| 4 | LLM-only: experimental in the UI, config and docs; off the demo path; no fixes | Done |
| 5 | Launcher `start_demo` with a loud pre-flight | Done: `./start_demo.sh` |
| 6 | `docs/freeze_checklist.md` | Done, plus `scripts/freeze_check.py` (passes); 4 non-mechanical items open |

## 1. Wrong drug recorded as another known drug (dev speech)

`eval/drug_identity.py` runs on the saved transcripts of the 480 dev speech clips: rules NER, validator and
`low_asr_confidence`, as the pipeline runs them. A wrong drug is an entry whose drug is in the lexicon but is not a
drug of that utterance's gold.

| | Before (`r9-drug-identity-before`, at `57d35ce`: round-8 code plus the counting script) | After (`r9-drug-identity-after`, at `1fa9301`: round-9 code) |
|---|---|---|
| Wrong-drug entries | **10**: 4 matched by sound, 6 an exact (wrong) drug word from the recogniser | 10 (extraction unchanged) |
| No identity flag stronger than low_confidence / low_asr_confidence | **10 of 10** | 6 of 10 (the exact-word ones) |
| No high-severity flag at all (confirmable without ticking anything) | 1 of 10 | 1 of 10 (an exact-word one: "Atropine" for "epipen") |
| Need the "did you mean" tick | 0 | **4 of 4 sound-matched** |
| Correct drugs matched by sound that now also need the tick (the cost) | — | 49 of 55 |

On the high flags in the before column: in 9 of the 10 entries they are about other fields (a missing dose, a route
not allowed, a range). Ticking them never asks whether the drug is right.

**The rule (general; `jatayu/extract/rules.py`):**

- **When it fires:** the drug was matched only by sound (fuzzy or phonetic), and the heard letters are less than
  **0.95** alike (rapidfuzz ratio) to the recorded drug's nearest name or alias.
- **Effect:** the entry gets `sound_alike_drug`, a high flag: "Heard 'X' — did you mean Y? Matched by sound only
  (similarity s)".
- **Why spelling, not the phonetic score:** a phonetic match can score 1.0 on two different words ("kettler" ~
  ketalar), so the measure is how alike the letters are.
- **Why 0.95:** it is the existing low-confidence line, stated, not tuned. The 4 wrong sound matches score 0.50 to 0.91.
  Near-identical spellings (≥ 0.95, e.g. "hydrocortisonne") keep the medium `low_confidence` flag.

**The heard word is never hidden:**

- **Confirm screen:** the heard word shows next to the recorded drug whenever they differ. A sound-alike entry also gets
  a "Heard X — did you mean Y?" box, and the acknowledgement dialog shows Heard / Recorded side by side.
- **Confirming:** the API refuses until `sound_alike_drug` is ticked. Correcting the drug clears the flag.
- **JSON:** the heard word stays in the drug field's `raw` text in the provenance.
- **PDF:** it shows as heard "…" under the drug.
- **Hybrid:** keeps the flag.

**Tests:** `test_round9_drug_identity.py`, with new sentences:

- ondansatron, furosemid, kettamin, adrenelin;
- the near-identical case and the exact case;
- the confirm API, JSON and PDF;
- an edit clearing the flag;
- the hybrid and the UI.

The "Match" number in the drug-identity reports is the matcher's own score, not the spelling similarity. The spelling
similarity is in the flag message.

**Still open (in the docs):** the 6 wrong drugs that came from an exact lexicon word the recogniser wrote ("salbutamol"
for "solumedrol"). No sound rule can see them; only the informational `low_asr_confidence` and any dose/route flags
apply.

**Scorer gap:** the dangerous-error metric pairs predictions with gold only on the same drug. So a wrong drug counts as
a miss plus an extra prediction, never as a dangerous error. This count is the separate measure; the gap is now in
`architecture.md` §7.

## 2. False unknown-drug entries (dev speech)

**Classification.** The 49 round-8 `drug_not_in_lexicon` entries were hand-labelled from the gold sentence and the
transcript, before the guard was written (`unknown_drug_labels_dev.yaml`, with a reason per entry):

- **38 true misheard drugs:** "Vomicind" (Vomikind), "Thaxia" (TXA), "spring" (Disprin), …
- **7 junk:**
  - "fine" (five) and "rise", ordinary words;
  - "evipush" and "intramascula", misheard routes;
  - "tivendat 957", "Attend 16" and "elida 1043", words run into a time.
- **4 other:** three misheard "serum magnesium" readings, and "signed", a fragment of "adenosine" with a misheard
  dose.

**The guard (general; `rules.py::_unknown_drug`):**

- **a. Ordinary English words.** The common-word list is the 24,493 whole-word tokens of Whisper small.en's own
  vocabulary, minus every lexicon word (`jatayu/lexicon/common_words.txt`, built by `scripts/build_common_words.py`).
  A word on the list counts as an unknown drug only with a number **and** a unit after it ("spring 300 mg"). A bare
  number or a route after it is not enough.
- **b. Drug-like shape.** A word with similarity ≥ 75 to a route or unit term is a misheard route or unit, never a drug.
  Misheard drugs on dev score ≤ 59.
- **Rejected: a clock-time guard.** It would have removed "tivendat 957", but it would also silently drop a real unknown
  drug said with a bare dose.

| `drug_not_in_lexicon` on dev speech | Flags | Misheard drug / junk / other | Precision | Recall (of 38 misheard drugs) |
|---|---|---|---|---|
| Before (round 8) | 49 | 38 / 7 / 4 | **0.776** | **1.000** |
| After (round 9) | 42 | 37 / 2 / 3 | **0.881** | **0.974** |

- **Removed:** "fine", "rise", "Attend", "evipush", "intramascula", "signed" — and one true misheard drug, "equals 10" for
  Ecosprin (an English word with no unit after it).
- **Still flagged:** "tivendat", "elida", and the 3 magnesium readings.
- **Recall caveat:** recall is measured against the drugs the round-8 rule found. Drugs the recogniser lost completely
  are outside that denominator.
- **Tests:** junk sentences ("BP stable 120 over 80", "gave fresh IV", "intramuskular", "ivpusch", "milligramms 2") and
  true unknown drugs still flagged (levetiracetam, heparin, and "candle 300 mg", an English word with a dose and a
  unit).

**Regression, before (round 8, `b081f3c`) → after (round 9, `1fa9301`); same inputs:**

| Run | Entity F1 | Precision | Exact | Dangerous | Admin-status |
|---|---|---|---|---|---|
| dev typed text, rules | 1.000 → 1.000 | 1.000 → 1.000 | 520/520 → 520/520 | 0/440 → 0/440 | 0/40 → 0/40 |
| dev typed text, hybrid | 0.992 → 0.992 | 1.000 → 1.000 | 489/520 → 489/520 | 0/440 → 0/440 | 0/40 → 0/40 |
| off-template dev, rules | 0.952 → 0.952 | 0.946 → 0.946 | 54/71 → 54/71 | 2/59 → 2/59 | 3/12 → 3/12 |
| dev speech, rules (same transcripts) | 0.640 → **0.644** | 0.811 → **0.825** | 181/520 → 181/520 | 1/440 → 1/440 | 2/40 → 2/40 |

**Flags raised by the rules NER, round 8 → round 9** (`eval/flag_counts.py`):

- **Typed text and off-template:** identical, 641 → 641 and 122 → 122.
- **Dev speech:** 413 → 406 entries and 928 → 905 flags. `drug_not_in_lexicon` 49 → 42; `sound_alike_drug` 0 → 53
  (4 wrong + 49 correct); `low_confidence` 59 → 6.

## 3. FHIR: patient reference and strict R4

**What the app now emits (`jatayu/output/fhir.py`, schema updated):**

- **Subject:** every resource has `subject` = "Unidentified patient". It is a logical reference, keyed by the incident
  (`identifier: urn:jatayu:incident-patient / <incident id>`), because no identity is captured in the field.
- **Wrapper fields:**
  - the incident id is `Bundle.identifier`;
  - the device is `meta.source`;
  - each utterance's transcript is a `Communication` resource; the provenance spans index into it.

  These replace the non-FHIR top-level fields.
- **Procedure:** a not-done `Procedure` has a single `statusReason`, as R4 requires (0..1). Round 8's example had no
  not-done procedure, so this had not shown up.

**Checked** (`r9-fhir-r4-check.report.md`):

- **What:** the round-9 example (`example.json`), **exactly as emitted**: no placeholder, nothing patched.
- **How:** parsed by the `fhir.resources` 6.5.0 R4 models (pydantic 1.10), in a separate environment.
- **Result:** the **whole Bundle is valid**, and so are **20 of 20 resources** on their own (10 clinical, including
  not-done and reading entries, and 10 Communications).
- **Coverage:** the models check required elements, cardinality, datatypes, required-binding status codes, choice-type
  names and extension shape.

**Not checked:**

- the official HL7 validator's further invariants;
- terminology (ATC and SNOMED codes are not looked up);
- profiles (no US Core or IPS);
- reference resolution (the patient is a logical reference, not a Patient resource in the bundle).

This wording is in `architecture.md` §6b. Our own check on every bundle remains **our FHIR-lite JSON Schema**.

**Example** (`r9-fhir-pdf-example.report.md`, `example.json` / `.pdf` / `_pdf.txt`): the round-7 cases plus a
sound-alike ("furosemid", shown as heard in the PDF), a drug not in the lexicon (no code), a concentration (no dose)
and a failed IV access (`not-done`). All 13 checks pass.

## 4. LLM-only is experimental

- **Config:** `jatayu/config.py` has `DEMO_EXTRACTORS = (rules, hybrid)` and `EXPERIMENTAL_EXTRACTORS = (llm,)`. The
  switch is `JATAYU_EXPERIMENTAL=1`, off by default. `JATAYU_EXTRACTOR=llm` refuses to start without it.
- **API:** LLM-only is built only with the switch. Without it, a request for `llm` gets 403 "experimental and off in the
  demo". `/api/health` lists the offered extractors.
- **UI:** shows the extractors the server offers. With the switch on, LLM-only is labelled "llm only (experimental)".
- **CLI:** `f2r` follows the same rule.
- **Pre-flight:** fails if the switch is on.
- **Docs:** `README.md` and `architecture.md` mark it experimental with no safety fixes. The harness still scores it on
  dev for comparison.
- **No fixes applied:** none of the round-8 or round-9 fixes went into `jatayu/extract/llm.py`.

## 5. Launcher

`./start_demo.sh` activates `anpr` and the CUDA library path, then runs `scripts/start_demo.py`.

**Pre-flight checks** — any FAIL prints in capitals, exits 1 and starts nothing:

- GPU: nvidia-smi, torch CUDA and CTranslate2 CUDA;
- models: Whisper, the LLM file, the voice, the word list and the built UI;
- config: demo extractor, LLM-only off, ASR on CUDA;
- offline: the variables set to 1, and **Whisper transcribing the fixture on the GPU and the voice speaking, both with
  outbound sockets blocked**;
- the audit chain;
- the port.

**Then:** it starts the server on 127.0.0.1, waits for `/api/health`, and opens the Windows browser from WSL.

**Evidence:**

- `preflight.json`: all 8 PASS on the demo laptop (RTX 5060).
- `negative_experimental_and_online.txt`: config and offline FAIL, not started.
- `negative_port_busy.txt`: port FAIL, not started.
- `start_demo_run.txt`: a full start; the server answered `/api/health` with extractors [rules, hybrid].
- `test_start_demo.py`: 4 tests.

## 6. Freeze checklist

`freeze_checklist.md` has four parts:

- **A, mechanical:** clean tree, tests, frozen hashes, pinned versions, model file hashes, config, run_log. Automated
  by `python -m scripts.freeze_check --pytest`. Run on the pushed tree it reported **FREEZE CHECK PASSED**
  (`freeze_check.json`, 440 passed). The model file hashes are now pinned in `eval/models.sha256`.
- **B, what must be true before the freeze commit.** Open:
  - **B1:** the real recordings are not imported yet;
  - **B2:** the real test manifest's hash is not frozen;
  - **B3:** no reviewed runner exists yet for scoring the real test clips (`load_real("test")` refuses);
  - **B5:** the evaluator's sign-off.
- **C, the freeze:** tag and push.
- **D, the one test run:** exact commands, run once, aggregates only. No re-runs without agreement; final_test only at
  S7.

## Files changed (code, tests, docs; results not listed)

- **Rules NER:** `jatayu/extract/rules.py`. Sound-alike flag, spelling similarity, junk guard.
- **Word list:** `jatayu/lexicon/common_words.txt`, generated by `scripts/build_common_words.py`.
- **Hybrid:** `jatayu/extract/hybrid.py`. Passes the sound flag through.
- **Edits:** `jatayu/incident.py`. An edit of the drug clears the sound flag.
- **FHIR:** `jatayu/output/fhir.py` and `jatayu/schemas/fhir_lite.schema.json`.
- **PDF:** `jatayu/output/pdf.py`. Heard word; Communications skipped.
- **LLM-only switch:** `jatayu/config.py`, `jatayu/api.py`, `f2r/cli.py`, and the help text in `eval/run.py`.
- **UI:**
  - `web/src/components/EntryCard.tsx`, `web/src/screens/Capture.tsx`, `web/src/api.ts`, `web/src/app.css`;
  - the rebuilt bundle in `jatayu/web/dist`.
- **Launcher:** `start_demo.sh`, `scripts/start_demo.py`.
- **Freeze:** `scripts/freeze_check.py`, `scripts/make_lock.py` (a `pins()` function factored out),
  `eval/models.sha256`, `docs/freeze_checklist.md`.
- **Evaluation:** `eval/drug_identity.py`, `eval/unknown_drug_labels_dev.yaml`.
- **Examples and the R4 check:** `scripts/fhir_pdf_example.py`, `scripts/fhir_r4_check.py`.
- **Tests:**
  - new: `tests/test_round9_drug_identity.py`, `tests/test_start_demo.py`;
  - updated for the intended changes: `tests/test_api.py`, `tests/test_fhir.py`, `tests/test_incident.py`,
    `tests/test_pdf.py`, `tests/test_hybrid.py`;
  - fixed: `tests/test_audit_tamper.py`. Its `prev_hash` mutation was a no-op 1 run in 16; this was found during this
    round and is not a code change.
- **Docs:** `README.md`, `docs/architecture.md`, `DECISIONS.md`.

## Tests

The full suite at `a77f4ce`, model tests included: **440 passed, 12 xfailed, 0 skipped, 0 failed**
(`pytest_output.txt`). The freeze check reran it at `7d921d7` with the same result.

## Files to attach

The whole folder `results/packets/round9/`:

- `README.md`;
- `r9-drug-identity-before.report.md`, `r9-drug-identity-after.report.md`, `unknown_drug_labels_dev.yaml`;
- regression: `r9-dev-text-rules-after`, `r9-dev-text-hybrid-after`, `r9-offtemplate-rules-after`,
  `r9-dev-audio-rules-after` (`.report.md`) and `r9-flag-counts-after.metrics.json`;
- FHIR: `r9-fhir-pdf-example.report.md`, `example.json`, `example.pdf`, `example_pdf.txt`,
  `r9-fhir-r4-check.report.md`;
- launcher: `preflight.json`, `negative_*.txt`, `start_demo_run.txt`;
- freeze: `freeze_checklist.md`, `freeze_check.json`;
- docs: `architecture.md`, `project_README.md`;
- tests: `test_round9_drug_identity.py`, `test_start_demo.py`, `pytest_output.txt`;
- `run_log.jsonl`.
