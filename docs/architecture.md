# Scribe108 — architecture

Draft, updated for evaluator round 9. **Decision-support demo, not a clinical device. Adult patients only.** Every number below
was written by the evaluation harness (`results/`) and carries a label:

- **[dev · synthetic]** — the development split, template sentences and/or computer voices (Piper TTS). We tuned on it.
- **[dev · hand-written]** — our own off-template sentences; written by the same person who wrote the fixes.
- **[test · validator only]** — the frozen test split, used only to check the dose validator on gold labels; the full
  pipeline has never been run on it.
- **[sealed]** — not measured yet: final_test, all pipeline runs on test, and every real recording.

## 1. What it does

A responder speaks a medication or procedure note ("gave 0.3 mg adrenaline IM two minutes ago"). On the laptop, with
no network, the app transcribes it, reads drug / dose / unit / route / time out of the transcript, checks the dose
against a cited adult range and the incident so far, and shows every value next to the words it came from. The medic
confirms, edits or rejects each entry; confirmed entries become a FHIR-lite record and a PDF note. Every step is
appended to a hash-chained audit log.

## 2. Pipeline

```
 microphone (browser)          typed text
        │                          │
        ▼                          │
 decode → 16 kHz mono  (jatayu/audio.py)
        │                          │
        ▼                          │
 ASR: faster-whisper small.en on the GPU  (jatayu/asr.py)
   vocabulary prompt (routes + 36 generic drug names, within Whisper's 223-token prompt limit),
   English forced, word probabilities kept
        │                          │
        └────────────┬─────────────┘
                     ▼
 normalise: spoken numbers → digits, every token keeps its offset in the transcript  (jatayu/normalise/)
                     ▼
 NER — rules-first clinical NER (lexicon and patterns), with optional LLM-assisted NER  (jatayu/extract/)
   rules (default): lexicon phrases + patterns; fuzzy/phonetic drug match (always flagged; below 0.95 spelling
                    similarity it is high, "heard X — did you mean Y?", and must be ticked); a drug not in the
                    lexicon is kept as spoken (flagged); context cues (not given / measurement), self-corrections,
                    concentrations, ranges, repeat doses
   hybrid (optional): the rules layer finds candidate spans, a local LLM (Qwen3-4B, llama.cpp) only LINKS them
   llm (EXPERIMENTAL, off the demo path): the LLM quotes the transcript; any quote not in the transcript is rejected.
        Offered only with JATAYU_EXPERIMENTAL=1; none of the round-8/9 safety fixes; scored on dev for comparison
                     ▼
 low_asr_confidence (informational): a drug/dose/unit from a word Whisper heard with p < 0.2  (jatayu/asr_confidence.py)
                     ▼
 VALIDATE  (jatayu/validate.py) — adds flags, never changes a value
   cited dose ranges (NASEMSO v3.0 rows + labelled illustrative rows), mg↔mcg check, weight-derived range for per-kg
   doses (45-130 kg, CDC NHANES), allowed units/routes, duplicate and repeat-too-soon against the incident history
                     ▼
 confirm screen (web/, DOT UI)  — high flags must be acknowledged before confirming
                     ▼
 FHIR-lite bundle (jatayu/output/fhir.py) + PDF note (jatayu/output/pdf.py)
   a "not given" or measurement entry is always status not-done, never a completed administration;
   every resource names an unidentified patient; transcripts are Communication resources (passes the R4 models)
                     ▼
 audit log (jatayu/audit.py): append-only SQLite, each row hashes the previous; verify() names the first broken row
```

## 3. Design rules

- **Every value points at transcript words.** Each field has a span into the raw transcript, a confidence and a source
  (rules / llm / user). Neither extractor can write a value that is not in the transcript.
- **Doubt is shown, never fixed silently.** Missing fields, approximate drug matches, a spoken range, a borrowed time, a
  correction, a dose outside the cited range, an unsure recogniser: each becomes a flag on the entry. The validator
  only adds flags.
- **"Not given" is never "given".** Negation, allergy, refusal, home medication, a failed or negated procedure, or a
  measurement reading → `possible_not_given` / `possible_measurement` (high); FHIR status `not-done`.
- **Offline.** Models load from disk; the setup check re-runs the speech recogniser, the LLM and the read-back voice with
  every outbound socket blocked.
- **Rules-first clinical NER (lexicon and patterns), with optional LLM-assisted NER.** On dev the LLM-assisted modes
  added nothing measurable (tables below), so `rules` is the default and `hybrid` stays selectable. **LLM-only is
  experimental** (round 9): it is not on the demo path, the app offers it only when started with `JATAYU_EXPERIMENTAL=1`
  (the UI then labels it "experimental"), and it has none of the round-8/9 safety fixes; it is still scored on dev as a
  comparison. There is no trained NER model: entity recognition is the lexicon, the patterns and, optionally, the LLM.

## 3a. Entity types (what the NER recognises)

| Entity | What is recognised | Normalised to |
|---|---|---|
| drug | generic or brand name; ASR misspellings by sound (always flagged; "did you mean" and a forced tick below 0.95 spelling similarity); a drug-like word not in the lexicon (kept as spoken, flagged) | one of 36 generic names in the lexicon, or the word as spoken |
| dose value | the number of the dose, spoken or written ("point three", ".5", "1,000"), the corrected value after "no, sorry" | a number |
| dose unit | mg, mcg, g, ml, L/min, units, puffs, drops, mmol, mEq and their spellings | one of 10 unit codes |
| route | IV, IM, IO, SC, PO, SL, IN, NEB, INH, ET, PR and their phrasings ("into the vein", "under the tongue") | one of 11 route codes |
| time | clock times ("at 10 40") and relative times ("two minutes ago"); none said → the device clock, flagged | an absolute time |
| procedure | 14 procedures (CPR, defibrillation, IV cannulation, 12-lead ECG, ...) | one of 14 procedure names |
| procedure detail | e.g. "size 7.5" | text (extracted, **not scored**) |

Each recognised entity also carries an **administration status** (given / not given / measurement), read from cue words
around it, and the flags above. Scored entity types: drug, dose value, dose unit, route, time, procedure.

## 4. Knowledge

`jatayu/lexicon/`: 36 drugs with 109 aliases and brand names (Indian brands included), 14 procedures, 11 routes,
10 units, 174 dose rows (170 cited with guideline section and page; 4 labelled illustrative), and the plausible adult
weight range. Sources and every choice: `DECISIONS.md`.

## 5. Evaluation design

- **Data:** synthetic sentences from templates, split by template family (train 2,180 / dev 480 / test 400 /
  final_test 300 utterances); test and final_test use paraphrase patterns no other split uses. Speech: each sentence
  read by Piper voices (US, GB and Indian-accented), plus ESC-50 noise at 20/10/5 dB.
- **Freezing:** SHA-256 of the test and final_test sentences and of every rendered clip in `eval/frozen.sha256`. The
  harness refuses test/final_test on a dirty working tree, writes aggregates only for them, and logs every run in
  `results/run_log.jsonl`. final_test is sealed until the last stage.
- **Metrics** (`eval/metrics.py`): entity F1 over drug / dose / unit / route / time / procedure; record exact match;
  **dangerous error** = a wrong drug, dose, unit or route with no catching flag (headline: strict — informational flags
  such as `weight_based_dose` and `low_asr_confidence` do not catch; a lenient row counts them); **administration-status
  error** = a "not given" record written as given; context errors; normalised WER (both sides through the same
  normaliser) and drug-term recall (brand names count as the generic).

## 6. Measured so far

| Measure | Result | Label |
|---|---|---|
| Typed template sentences, rules: entity F1 / dangerous errors | 1.000 / 0 of 440 | dev · synthetic (generator and extractor share a lexicon: not a headline) |
| Off-template sentences (59), rules: entity F1 / dangerous | 0.952 / 2 of 59 (both route corrections) | dev · hand-written |
| Speech (480 Piper clips): normalised WER | 0.406 (US 0.257, GB 0.260, Indian-accented 0.532) | dev · synthetic |
| Speech: drug-term recall | 0.574 (plan target 0.90: not met) | dev · synthetic |
| Speech, rules: entity F1 / dangerous / "not given" recorded as given | 0.673 / 1 of 440 / 2 of 40 (round 5); 0.640 / 1 of 440 / 2 of 40 after the round-8 unknown-drug fix (precision 0.928 → 0.811: misheard drug names now kept and flagged instead of dropped); **0.644** / 1 of 440 / 2 of 40 after the round-9 junk guard (precision 0.825) | dev · synthetic |
| Speech, rules: wrong drug recorded as a known drug | 10 entries (4 matched by sound, 6 a wrong drug word from the recogniser). Round 8: all 10 carried no identity flag stronger than low_confidence / low_asr_confidence. Round 9: the 4 sound matches need a "did you mean" tick; the 6 exact-word ones are unchanged (open) | dev · synthetic |
| Speech, rules: `drug_not_in_lexicon` precision / recall (hand labels, 49 round-8 flags) | round 8: 0.776 / 1.000 (49 flags: 38 misheard drugs, 7 junk, 4 other); round 9: **0.881 / 0.974** (42 flags: 37 / 2 / 3) | dev · synthetic, labelled by us |
| Speech, same transcripts: rules / hybrid / LLM-only (experimental) entity F1 | 0.673 / 0.673 / 0.527 (round 5) | dev · synthetic |
| Noise, same 160 utterances (hybrid): clean / 20 / 10 / 5 dB entity F1 | 0.653 / 0.633 / 0.624 / 0.567 | dev · synthetic |
| ASR options (100 clips): drug-term recall small.en / large-v3-turbo / distil-large-v3 | 0.648 / 0.523 / 0.318 | dev · synthetic |
| End of a 10-second dictation → confirm-screen payload: p50 / p95 | 0.387 s / 0.422 s (RTX 5060) | dev · synthetic dictation |
| Seeded dose errors caught (×10, ÷10, mg↔mcg, route) | 99.0% (198/200; 95% CI 96.4-99.7) — circular by construction | test · validator only |
| Harder seeded errors (×2, ×5, digit slip, mg→g) | 78.0% (156/200; 95% CI 71.8-83.2) | test · validator only |
| Correct gold doses flagged by the validator | dev 1.9%, test 0.3%, final_test 1.2% | dev / test · validator only |
| PDF note (bundle + schema check + chain verify + render): 10 / 50 entries, p50 | 19.8 ms / 87.4 ms (p95 28.6 / 111.3 ms) | synthetic incidents |
| Blind off-template set, evaluator-authored (32 typed sentences), entity F1 core / stretch: rules · hybrid · LLM-only | as-run (official): 0.840 / 0.857 · 0.805 / 0.857 · 0.747 / 0.812; converter-corrected (round 8): 0.892 / 0.857 · 0.858 / 0.857 · 0.780 / 0.812 | blind · single author, sanity check, not a headline |
| Full pipeline on test or final_test; any real recording | — | sealed / not yet recorded |

## 6a. Per entity type, dev

Precision / recall / F1 per entity type, from the existing dev runs (nothing re-run). "gold" = number of gold values.
These runs predate the round-8 safety fixes: the typed results are unchanged by them (round-8 before/after runs are
identical), but on speech the rules NER now keeps misheard drug names as flagged "not in lexicon" entries (entity F1
0.673 → 0.640, precision 0.928 → 0.811).

**Typed template sentences [dev · synthetic]** — 480 utterances (generator and NER share a lexicon: not a headline)

| Entity (gold) | rules P / R / F1 | hybrid P / R / F1 | LLM-only P / R / F1 |
|---|---|---|---|
| drug (460) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.890 / 0.876 / 0.883 |
| dose value (380) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.862 / 0.937 / 0.898 |
| dose unit (380) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.903 / 0.953 / 0.927 |
| route (360) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0.895 / 0.967 / 0.929 |
| time (244) | 1.000 / 1.000 / 1.000 | 1.000 / 0.873 / 0.932 | 0.931 / 0.832 / 0.879 |
| procedure (60) | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 1.000 / 0.383 / 0.554 |

**Speech, same ASR transcripts [dev · synthetic]** — 480 Piper clips

| Entity (gold) | rules P / R / F1 | hybrid P / R / F1 | LLM-only P / R / F1 |
|---|---|---|---|
| drug (460) | 0.970 / 0.691 / 0.807 | 0.970 / 0.691 / 0.807 | 0.805 / 0.530 / 0.640 |
| dose value (380) | 0.871 / 0.553 / 0.676 | 0.864 / 0.550 / 0.672 | 0.698 / 0.445 / 0.543 |
| dose unit (380) | 0.957 / 0.474 / 0.634 | 0.946 / 0.503 / 0.656 | 0.819 / 0.311 / 0.450 |
| route (360) | 0.908 / 0.439 / 0.592 | 0.919 / 0.442 / 0.597 | 0.782 / 0.369 / 0.502 |
| time (244) | 0.886 / 0.381 / 0.533 | 0.882 / 0.336 / 0.487 | 0.816 / 0.291 / 0.429 |
| procedure (60) | 1.000 / 0.600 / 0.750 | 1.000 / 0.600 / 0.750 | 1.000 / 0.233 / 0.378 |

**Off-template sentences [dev · hand-written]** — rules on the 56-sentence version of the set (round 5); hybrid and
LLM-only on the 54-sentence version (round 4; two procedure-negation sentences were added in round 5)

| Entity | rules P / R / F1 (gold) | hybrid P / R / F1 (gold) | LLM-only P / R / F1 (gold) |
|---|---|---|---|
| drug | 1.000 / 1.000 / 1.000 (65) | 1.000 / 1.000 / 1.000 (64) | 0.866 / 0.906 / 0.886 (64) |
| dose value | 0.889 / 0.960 / 0.923 (50) | 0.868 / 0.939 / 0.902 (49) | 0.857 / 0.980 / 0.914 (49) |
| dose unit | 0.982 / 0.964 / 0.973 (55) | 0.981 / 0.963 / 0.972 (54) | 0.885 / 1.000 / 0.939 (54) |
| route | 0.961 / 0.925 / 0.942 (53) | 0.960 / 0.923 / 0.941 (52) | 0.814 / 0.923 / 0.865 (52) |
| time | 0.600 / 0.750 / 0.667 (8) | 0.857 / 0.750 / 0.800 (8) | 0.714 / 0.625 / 0.667 (8) |
| procedure | 1.000 / 1.000 / 1.000 (6) | 0.667 / 1.000 / 0.800 (2) | 1.000 / 1.000 / 1.000 (2) |

Runs: `results/r5-dev-text-rules`, `r4-dev-text-hybrid-v2`, `r3-dev-text-llm`; `r5-dev-audio-rules`,
`r4-dev-audio-hybrid-v2`, `r4-dev-audio-llm`; `r5-offtemplate-rules`, `r4-offtemplate-hybrid-v2`, `r4-offtemplate-llm`.

Known gaps, plainly: **procedure is extracted and scored**, but LLM-only recognises few procedures (recall 0.383 typed,
0.233 speech); the **procedure detail** (e.g. a tube size) is extracted but **not scored**; **time** is the weakest
entity on speech (rules recall 0.381). Not fixed this round.

## 6b. FHIR-lite record and the PDF

- **How the JSON is checked.** Every bundle is validated against **our FHIR-lite JSON Schema**
  (`jatayu/schemas/fhir_lite.schema.json`, JSON Schema 2020-12, with format checking) by `jatayu/output/fhir.py::validate_bundle`, every time one is built: per utterance in
  the pipeline, and per incident at `/api/incidents/<id>/bundle`. A bundle that fails is never returned or logged.
  Tests: `tests/test_fhir.py` (validity, omitted-not-null fields, provenance spans, rejects garbage),
  `tests/test_fhir_safety.py`, `tests/test_demo_flow.py`.
- **Strict FHIR R4 (optional check).** Round 8 found the example was not strict R4 (no `subject`; extra wrapper
  fields). Since round 9 the app emits:
  - a `subject` on every resource: "Unidentified patient", a logical reference keyed by the incident
    (`identifier.system urn:jatayu:incident-patient`), because no patient identity is captured in the field;
  - the incident id as `Bundle.identifier` and the device as `meta.source`;
  - each utterance's transcript as a `Communication` resource (provenance spans index into it);
  - a single `statusReason` on a not-done `Procedure` (R4 cardinality 0..1).

  **What was checked** (`results/r9-fhir-r4-check/`, `scripts/fhir_r4_check.py`): the round-9 example bundle, exactly
  as the app emitted it (nothing added or patched), parsed by the FHIR R4 models of `fhir.resources` 6.5.0 (pydantic
  1.10, separate virtual environment). The whole Bundle and each of its 20 resources on its own (6 given/draft and
  4 not-done or reading administrations and procedures, 10 Communications) are valid. The models enforce: required
  elements, cardinality, datatypes, required-binding status codes, choice-type names, extension shape.
  **What was not checked:** HL7 validator invariants beyond those models, terminology (ATC and SNOMED codes are not
  looked up), any profile (no US Core / IPS), reference resolution (the patient is a logical reference, not a Patient
  resource in the bundle). Our own check on every bundle remains our FHIR-lite JSON Schema.
- **One JSON, one PDF.** Since round 7 the PDF's entries are rendered **from that same validated bundle** (one helper
  builds it for both endpoints); the PDF adds the audit-log history and the chain verdict, which are not clinical
  record. `tests/test_pdf.py::test_pdf_entries_come_from_the_fhir_bundle` alters a dose in the JSON and checks the PDF
  shows the altered value. (Before round 7 both were built from the same audit-logged entries by two separate code
  paths.)
- **Not given = not-done.** An entry flagged not given (or a measurement) is `status: not-done` with a `statusReason`
  in the JSON, and "NOT GIVEN" / "READING" in the PDF, even after the medic confirms it.
- **Synthetic example:** `results/r9-fhir-pdf-example/` (round 7: `results/r7-fhir-pdf-example/`) — `example.json`
  (the bundle) and `example.pdf` (rendered from it): adrenaline (draft), aspirin (confirmed → `completed`), **morphine
  allergy (confirmed → `not-done`, "NOT GIVEN")**, a blood glucose reading (`not-done`, "READING"), CPR (draft), a
  self-corrected ondansetron dose (draft, 2 mg), and since round 9: "furosemid" matched by sound (the PDF shows
  heard "furosemid" under furosemide), levetiracetam (not in the lexicon, no code), atropine said as a concentration
  (no dose) and IV access that failed (`not-done`).
- **The heard word is never hidden.** Each field keeps the transcript words it came from (`raw` in the provenance); the
  confirm screen and the PDF show the heard word next to the recorded drug whenever they differ.

## 7. Known limits (each pinned by an expected-failure test, a DECISIONS row or an evaluation report)

Fixed in round 8 (general rules, unit-tested on new sentences; `tests/test_safety_fixes.py`):
- a drug-like word that is not in the lexicon, followed by a dose, unit or route, is kept with its spoken name and a
  visible `drug_not_in_lexicon` flag (high) on the confirm screen — it is no longer dropped;
- a concentration ("x mg per ml", "x mg/ml", "1 in 10000") is never recorded as the dose: `concentration_not_dose`
  (high), and the entry cannot be confirmed until the responder enters the dose.

Fixed in round 9 (general rules, unit-tested on new sentences; `tests/test_round9_drug_identity.py`):
- a drug matched **only by sound** with a spelling similarity below 0.95 to the recorded drug's nearest name gets
  `sound_alike_drug` (high): "heard X — did you mean Y?" on the confirm screen, with the heard word next to the
  recorded one, and it cannot be confirmed without ticking it. On dev speech this covers the 4 wrong drugs that were
  matched by sound; it also asks for a tick on 49 correct sound matches (the cost);
- junk guard for `drug_not_in_lexicon`: an ordinary English word (one of the 24,493 whole-word tokens of Whisper's
  own vocabulary, lexicon words removed) counts as an unknown drug only with a number and a unit after it, and a word
  shaped like a route or unit (similarity >= 75) never does. Dev speech: precision 0.776 → 0.881, recall 1.000 → 0.974.

Still open:
- **Time is the weakest entity on speech** (rules recall 0.38; dev, synthetic).
- **The procedure detail** (e.g. a tube size) is extracted but **not scored**.
- Speech is the weak link overall: the recogniser misses drug names (57% heard exactly) and is much weaker on the
  Indian-accented synthetic voices. Whether this holds for real speakers is unknown until real recordings exist.
- **Sound-alike substitution** is now caught at the confirm screen, not prevented: "tramadol" is still recorded as
  ketorolac, with a high "heard 'tramadol' — did you mean ketorolac?" that must be ticked or the entry rejected.
- **A wrong drug word from the recogniser** (it wrote "salbutamol" for "solumedrol", "atropine" for "epipen"): an
  exact lexicon word, so no sound flag; on dev speech 6 of the 10 wrong-drug entries, guarded only by
  `low_asr_confidence` (informational) and whatever dose / route flags apply.
- **Unknown-drug entries on speech:** 42 on dev speech after the round-9 guard; 2 are still junk (a word run into a
  clock time: "tivendat 957"), 3 are misheard lab readings ("serum magnesium"), and one true misheard drug is now
  dropped ("equals 10" for "ecosprin": an English word with no unit after it).
- Readings said as values ("blood sugar 54", "pulse ox 88", "BP 120 over 80") are not recorded as readings; a reading
  cue near a drug can mark that drug as a possible measurement ("blood sugar 54, gave dextrose").
- "second dose at 10 48" is not read as a repeat dose; negation said after the drug ("naloxone was not given",
  "morphine nahi diya"); route corrections ("IM, sorry, IV"); Hindi numbers and times ("ek", "char", "do minute
  pehle"); "about five minutes back"; per-kg doses ("1 mg per kg").
- The round-8 and round-9 fixes are in the rules NER and the hybrid; LLM-only is experimental, off the demo path, and
  does not have them.
- FHIR: the bundle passes the R4 data models, but it is not checked by the official HL7 validator, codes are not
  looked up, and the patient is only a logical "unidentified patient" reference (see 6b).
- **The dangerous-error metric does not see a wrong drug.** The scorer pairs a prediction with gold only on the same
  drug, so a wrong drug counts as a miss plus an extra prediction, not as a dangerous error. Wrong drugs are counted
  separately by `eval/drug_identity.py` (10 on dev speech; see section 6).
- A wrong dose that is still a legal dose cannot be caught by a range check; the residual risk depends on read-back
  confirmation, whose effectiveness we have not measured.

## 8. Deployment

WSL2 (Ubuntu) on the Windows laptop with an NVIDIA GPU; the browser runs on the Windows side at
`http://localhost:8000`. **One command:** `./start_demo.sh` runs a pre-flight that fails loudly (GPU; Whisper, LLM file
and voice present; Whisper transcribes a clip on the GPU and the voice speaks, both with outbound sockets blocked;
offline variables; demo-path config with LLM-only off; audit chain; port), then starts the server on 127.0.0.1 and
opens the browser; `--check-only` runs the pre-flight alone. Before the one test run: `docs/freeze_checklist.md`. Whisper small.en and Qwen3-4B fit together in 8 GB. Clean-install steps are in
`DECISIONS.md` (2026-11-02); they have not yet been run on a clean machine.
