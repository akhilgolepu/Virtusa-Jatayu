# Evidence packet — evaluator round 7 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only).

What this round did not touch:

- No extractor, lexicon, validator, prompt or threshold was changed.
- No pipeline run on test or final_test. No force push, no merge, no history rewrite.

The one code change is in the output layer (item 3): the PDF is now rendered from the validated FHIR-lite bundle.

| # | Item | Status |
|---|---|---|
| 5 | Blind set, run exactly per its header | Done — aggregate reported first; one converter defect disclosed (below) |
| 1 | Wording: rules-first clinical NER with optional LLM-assisted NER, entity types | Done |
| 2 | Per-entity-type P / R / F1 on dev, three extractors | Done (existing runs, nothing re-run) |
| 3 | FHIR-lite checks, synthetic JSON + PDF, same JSON, not-done | Done — the PDF was NOT built from the JSON before; now it is |
| 4 | PDF timing in the harness | Done (`r7-pdf-latency`) |
| 6 | Optional pretrained NER baseline | Done, about 3 minutes |

## 5. Blind set (`eval/offtemplate_blind_v1.yaml`, evaluator-authored, 32 cases)

**Protocol.**

- The file was committed exactly as received (`0f7eaaa`, SHA-256 `863faa60…`). I read the header first and the
  structure only after that.
- The converter (`eval/blind.py`) is a script with mechanical mappings only. It writes a conversion report and
  changes no gold.
- Rules, hybrid and LLM-only each ran **once**, at `3b7be15` with a clean tree; each run is logged in
  `run_log.jsonl` (`r7-blind-v1-*`).
- The aggregate report (`r7-blind-v1.report.md`) was committed (`d3a6074`) **before any individual error was read**.

**Aggregate, per tier.** The blind set is a sanity check from a single author, not a headline number.

| Tier | Extractor | Entity F1 (P / R) | Exact match | Dangerous (strict) | Admin-status errors | Flags raised |
|---|---|---|---|---|---|---|
| core (28) | rules | **0.840** (0.890 / 0.795) | 21/36 | **0/30** | 0/3 | 57 |
| core | hybrid | 0.805 (0.875 / 0.746) | 19/36 | 0/30 | 0/3 | 62 |
| core | LLM-only | 0.747 (0.756 / 0.738) | 19/36 | 0/30 | 1/3 | 62 |
| stretch (4) | rules | 0.857 (0.923 / 0.800) | 1/4 | 1/4 | 0/0 | 7 |
| stretch | hybrid | 0.857 (0.923 / 0.800) | 1/4 | 1/4 | 0/0 | 7 |
| stretch | LLM-only | 0.812 (0.765 / 0.867) | 1/4 | 0/4 | 0/0 | 12 |

**Converter defect, found after the run — the run is not repeated.**

- **The defect:** the file writes multi-word names with underscores (`magnesium_sulfate`, `iv_cannulation`); my
  converter did not map them to the lexicon names.
- **Effect:** 3 gold records (b17, b20, b21) were scored as a miss plus an extra prediction. Rules and hybrid had
  actually extracted magnesium sulfate 4 g IV and the IV-cannulation procedure in those sentences; LLM-only genuinely
  missed both procedures.
- **Direction:** the defect lowers the rules and hybrid numbers above. They stand as run.
- **Fix:** the converter now maps underscores to spaces, a format mapping only (`458482a`), for any future use.

**After the aggregate (the set is now ordinary dev data), rules extractor.**

The evaluator's expected flags:

- **Met for 9 of 12 cases:**
  - allergy and "never administered" visible;
  - the spoken range flagged;
  - two administrations;
  - unit missing;
  - dose above the IM range;
  - oxygen flow missing;
  - the Hinglish unit;
  - both concentration cases not recorded as 10 mg.
- **Partly met for b18:** "1 mg per kilo" was recorded as 1 mg with `dose_below_range`. It is flagged, but the per-kg
  meaning is lost.
- **Not met for b26: "diclofenac" (not in the lexicon) was dropped silently.** The file requires a visible "drug not in
  lexicon" flag. This is a real gap, logged in `architecture.md` §7 and not fixed (no extractor changes this round).

Other misses:

- **Readings as pseudo-drugs:** the readings the file encodes as pseudo-drugs (blood sugar, SpO₂, BP) are not
  recognised as records.
- **Phonetic false positive:** "pulse ox eighty eight" produced a flagged "furosemide 88" (the sound key of
  "pulseox" vs the alias "lasix").
- **Repeat dose:** "second dose at ten forty eight" is not read as a repeat dose.
- **Unparsed times:** "about five minutes back" and "do minute pehle".
- **Hindi number:** "char milligram".
- **Concentration:** "one in ten thousand, ten ml" was recorded as 10 ml with only `no_reference_range`. This is the one
  stretch dangerous error: concentrations are not modelled.

## 1. Wording

`docs/architecture.md` and `README.md` now say **"rules-first clinical NER (lexicon and patterns), with optional
LLM-assisted NER"**:

- **Entity types:** drug, dose value, dose unit, route, time, procedure, plus a procedure detail (extracted, not
  scored).
- **Status:** each recognised drug or procedure carries an administration status (given / not given / measurement).
- **No trained model claimed:** both files state plainly "There is no trained NER model".
- **Labels kept:** every number keeps its label (synthetic / dev / hand-written / blind / validator only / sealed).

## 2. Per entity type, dev

The tables are in `architecture.md` §6a, from existing dev runs: typed template, speech on the same transcripts, and
off-template; rules, hybrid and LLM-only.

**Procedure is extracted and scored** (60 gold procedures on dev): rules 1.000 typed and 0.750 on speech.

The known gaps are stated plainly there:

- LLM-only recognises few procedures (recall 0.383 typed, 0.233 speech);
- the procedure detail is not scored;
- time is the weakest entity on speech (rules recall 0.381).

## 3. FHIR-lite and the PDF

- **Checked by:** JSON Schema 2020-12 (`jatayu/schemas/fhir_lite.schema.json`, format checking on) via
  `validate_bundle`, every time a bundle is built: per utterance in the pipeline, and per incident at the bundle
  endpoint. Plus the tests `tests/test_fhir.py`, `tests/test_fhir_safety.py` and `tests/test_demo_flow.py`.
- **Same JSON — corrected this round.** Before round 7 the PDF was **not** built from the JSON. Both came from the same
  audit-logged entries, but by two separate code paths. The PDF's entries are now rendered from the same validated
  bundle (one helper, `_bundle`, serves both endpoints). The medic's review status travels in each resource's
  provenance. The new test `tests/test_pdf.py::test_pdf_entries_come_from_the_fhir_bundle` alters a dose in the JSON,
  and the PDF must show the altered value.
- **Not given = not-done.** In the example, the morphine allergy is confirmed by the medic with its high flag
  acknowledged. It is `status: not-done` with a `statusReason` in the JSON, and "NOT GIVEN" in the PDF. The blood
  glucose reading is `not-done` / "READING".
- **Example** (`r7-fhir-pdf-example.report.md`): `example.json` is the bundle, `example.pdf` was rendered from it, and
  `example_pdf.txt` is its text. Checks: schema valid; every bundle entry found in the PDF; no not-given entry is
  `completed`.

## 4. PDF timing (harness-logged)

`python -m scripts.pdf_latency --tag r7-pdf-latency` (`r7-pdf-latency.report.md`, raw `pdf_latency_timings.csv`). It
covers bundle build, schema check, audit-chain verify and render, on synthetic incidents, with 30 timed runs:

| Entries | p50 | p95 |
|---|---|---|
| 10 | **19.8 ms** | 28.6 ms |
| 50 | **87.4 ms** | 111.3 ms |

The earlier unlogged figure (17 / 79 ms) is no longer quoted anywhere.

## 6. Pretrained NER baseline (optional)

`eval/ner_baseline.py` is a separate script, not part of the pipeline (`r7-ner-baseline.report.md`).

- **Baseline:** `d4data/biomedical-ner-all`, used as downloaded: no fine-tuning, nothing run on test or final_test.
- **Data:** the dev typed sentences.
- **Normalisation:** its spans are normalised with our lexicon, so both systems are scored on the same values.

F1, rules-first NER vs pretrained:

| Entity | dev template (480) | off-template, hand-written (56) |
|---|---|---|
| drug | 1.000 vs 0.295 | 1.000 vs 0.382 |
| dose value | 0.950 vs 0.648 | 0.923 vs 0.745 |
| dose unit | 1.000 vs 0.819 | 0.973 vs 0.891 |
| route | 1.000 vs 0.136 | 0.942 vs 0.378 |
| procedure | 1.000 vs 0.278 | 1.000 vs 0.000 |

Caveats, also in the report:

- The template sentences share the rules' lexicon, which favours the rules side.
- The baseline was trained on written case reports, not dictated ambulance notes.
- Time is not scored in this comparison.

## Tests

Full suite at `9d1e699` (packet commit follows): **396 passed, 12 xfailed, 0 skipped, 0 failed**, model tests
included (`pytest_output.txt`).

## Files to attach

The whole folder `results/packets/round7/`:

- `README.md`;
- `r7-blind-v1.report.md`;
- `r7-fhir-pdf-example.report.md`, `example.json`, `example.pdf`, `example_pdf.txt`;
- `r7-pdf-latency.report.md`, `pdf_latency_timings.csv`;
- `r7-ner-baseline.report.md`;
- `architecture.md`, `project_README.md`;
- `pytest_output.txt`, `run_log.jsonl`.
