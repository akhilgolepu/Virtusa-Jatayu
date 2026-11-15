# Evidence packet — evaluator round 8 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only). Ground rules this round:

- No pipeline run on test or final_test. No merge into `main`, no force push, no history rewrite.
- The only extractor/validator changes are the two safety fixes of item 2.

| # | Item | Status |
|---|---|---|
| 1 | Blind set, converter-corrected rerun next to the as-run numbers | Done |
| 2 | Safety fixes: drug not in lexicon; concentration ≠ dose | Done, unit-tested on new sentences |
| 3 | Regression on dev | Done: no change on typed text; a stated trade-off on speech |
| 4 | Baseline mapping check, rerun, plus blind v1 | Done: the 0.000 was word-piece merging, not a missing label |
| 5 | FHIR wording; strict R4 check (optional) | Done (about 5 minutes) |
| 6 | Known limits | Done |

## 1. Blind set — as-run (official) and converter-corrected

The corrected run was done **once**, at `746c000`: before any round-8 code change, with a clean tree, logged
`r8-blind-v1-converter-corrected-*`. Extractor, lexicon, validator, prompt and gold were all unchanged. The flag counts
are identical to the as-run, which confirms the extractor was the same. The as-run numbers stay the official ones.

| Tier | Extractor | Entity F1, as-run → corrected | Exact match | Dangerous (strict) | Admin-status | Flags raised |
|---|---|---|---|---|---|---|
| core | rules | **0.840 → 0.892** | 21/36 → 24/36 | 0/30 → 0/30 | 0/3 → 0/3 | 57 → 57 |
| core | hybrid | 0.805 → 0.858 | 19/36 → 22/36 | 0/30 → 0/30 | 0/3 → 0/3 | 62 → 62 |
| core | LLM-only | 0.747 → 0.780 | 19/36 → 20/36 | 0/30 → 0/30 | 1/3 → 1/3 | 62 → 62 |
| stretch | rules | 0.857 → 0.857 | 1/4 → 1/4 | 1/4 → 1/4 | 0/0 | 7 → 7 |
| stretch | hybrid | 0.857 → 0.857 | 1/4 → 1/4 | 1/4 → 1/4 | 0/0 | 7 → 7 |
| stretch | LLM-only | 0.812 → 0.812 | 1/4 → 1/4 | 0/4 → 0/4 | 0/0 | 12 → 12 |

Reports: `r7-blind-v1-as-run.report.md` and `r8-blind-v1-converter-corrected.report.md`.

## 2. Safety fixes (general rules; diclofenac was NOT added to the lexicon)

**a. Drug not in the lexicon.**

- **Rules NER:** a drug-like word is kept as a medication entry under its **spoken name**, with `drug_not_in_lexicon`
  (high), which appears on the confirm screen and must be acknowledged before confirming. A drug-like word means:
  4+ letters; not a lexicon word; not a common English, vital-sign or cue word; and followed by a number or unit, or
  by a route when an administration verb or a dose comes before it.
- **Validator:** owns the flag, so hybrid entries and user edits get it too. It skips the range check instead of
  crashing.
- **FHIR:** the record keeps the spoken name with no ATC code.
- **Hybrid:** keeps the entry whether or not the LLM links it.

**b. Concentration is not a dose.**

- **What counts:** a ratio ("1 in 10000", "1:1000") or an amount per volume ("0.6 mg per ml", "50 mg/ml").
- **Effect:** no dose or unit is recorded, and the entry gets `concentration_not_dose` (high).
- **Confirming:** the API refuses with `needs_dose` (acknowledging is not enough) until the responder enters a dose.
  The edit clears the flag.
- **Hybrid:** clears any dose the LLM linked.

**Tests:** `tests/test_safety_fixes.py`, 18 tests on new sentences, none in blind v1 (checked):

- buscopan, ceftriaxone, labetalol;
- "atropine 0.6 mg per ml", "ketamine 50 mg/ml", "noradrenaline 1 in 10000";
- negative cases: pulse, weight, pain score, "tibial IO", "like 0.4 mg", "between 160 and 325";
- FHIR validity, the confirm-screen API path, and the hybrid.

**Files changed:**

- `jatayu/extract/rules.py`, `jatayu/extract/hybrid.py`, `jatayu/validate.py`;
- `jatayu/lexicon/__init__.py` (a `has_drug` method only; no lexicon data);
- `jatayu/output/fhir.py`, `jatayu/incident.py`, `jatayu/api.py`;
- `tests/test_safety_fixes.py` (new).

## 3. Regression (dev; nothing on test or final_test)

`*-before` runs are at `746c000`, before the fixes; `*-after` runs are at `b081f3c`.

| Run | Entity F1 | Precision | Exact | Dangerous | Admin-status |
|---|---|---|---|---|---|
| dev typed text, rules | 1.000 → 1.000 | 1.000 → 1.000 | 520/520 → 520/520 | 0/440 → 0/440 | 0/40 → 0/40 |
| dev typed text, hybrid | 0.992 → 0.992 | 1.000 → 1.000 | 489/520 → 489/520 | 0/440 → 0/440 | 0/40 → 0/40 |
| off-template dev, rules | 0.952 → 0.952 | 0.946 → 0.946 | 54/71 → 54/71 | 2/59 → 2/59 | 3/12 → 3/12 |
| dev speech, rules (same transcripts; before = `r5-dev-audio-rules`) | 0.673 → **0.640** | 0.928 → **0.811** | 181/520 → 181/520 | 1/440 → 1/440 | 2/40 → 2/40 |

Flags raised by the rules NER, before → after, counted on all outputs by `eval/flag_counts.py`. The before-count ran in
a worktree at `746c000` with the counting script copied in, hence its `-dirty` stamp:

| Input | Entries | Flags | `drug_not_in_lexicon` | `concentration_not_dose` |
|---|---|---|---|---|
| dev typed text (480) | 520 → 520 | 641 → 641 | 0 → 0 | 0 → 0 |
| off-template dev (56) | 71 → 71 | 122 → 122 | 0 → 0 | 0 → 0 |
| dev speech transcripts (480) | 364 → 413 | 779 → 928 | 0 → **49** | 0 → 0 |

On typed text nothing changes. On speech, misheard drug names followed by a dose are now kept as visible
"not in lexicon" entries ("Vomicind 7.5 mg" is the brand Vomikind; "Tixa 8 mg" is TXA) instead of being dropped. This
is the intended safety behaviour, but the scorer counts them as extra predictions. A few are ordinary misheard words
("fine", "rise"). Dangerous errors are unchanged.

## 4. Pretrained NER baseline — NOT FOR SLIDES

- **Mapping:** it covers both of the model's procedure labels (`Diagnostic_procedure`, `Therapeutic_procedure`).
- **Cause of the round-7 0.000:** our harness merged the model's word pieces with aggregation "simple", which split
  "CPR" into "cp" and "aspirin" into "as / ##pi / ##rin". The lexicon could not normalise those fragments.
- **Fix:** merge per word (aggregation "first"). Rerun at `c391366`, now including blind v1
  (`r8-ner-baseline.report.md`; every table labelled "NOT FOR SLIDES").

Pretrained F1, round 7 → round 8:

| Set | drug | route | procedure |
|---|---|---|---|
| dev template | 0.295 → 0.693 | 0.136 → 0.422 | 0.278 → 0.365 |
| off-template | 0.382 → 0.780 | 0.378 → 0.466 | 0.000 → 0.118 |

Blind v1 (spent, now dev; rules column on round-8 code), rules vs pretrained F1:

| Entity | Rules | Pretrained |
|---|---|---|
| drug | 0.892 | 0.645 |
| dose value | 0.839 | 0.520 |
| dose unit | 0.902 | 0.682 |
| route | 0.949 | 0.263 |
| procedure | 1.000 | 0.095 |

Procedure stays low for the baseline. It labels many non-procedure spans as procedures and tags "IV access" as a
medication.

## 5. FHIR

- **Wording:** the docs now say **"our FHIR-lite JSON Schema"** (`jatayu/schemas/fhir_lite.schema.json`).
- **Strict R4 check (optional):** `fhir.resources` 6.5.0 R4 models with pydantic 1.10, in a separate virtual
  environment, on the round-7 example (`r8-fhir-r4-check.report.md`).
- **Result:** the example is **not** strict R4. All 6 resources fail on exactly one listed error, the missing `subject`
  (patient reference). With a placeholder subject, **all 6 validate as R4**. The bundle wrapper also has our extra
  fields (`incident`, `meta.device`, …).
- **Limits:** this is a data-model check, not the official HL7 validator, so no terminology or profile checks.

## 6. Known limits

`architecture.md` §7 now lists:

- the round-8 fixes;
- time as the weakest entity on speech (rules recall 0.38);
- the procedure detail, which is not scored.

It also lists what is still open:

- sound-alike substitution ("tramadol" → ketorolac, flagged `low_confidence`);
- false unknown-drug entries on speech;
- readings not recorded as readings, and reading cues spilling onto a nearby drug;
- "second dose at …";
- negation after the drug, route corrections, Hindi numbers and times, "five minutes back", per-kg doses;
- LLM-only does not have the round-8 fixes;
- FHIR-lite is not strict R4.

## Tests

Full suite at `6df47b2`, model tests included: **414 passed, 12 xfailed, 0 skipped, 0 failed** (`pytest_output.txt`).

## Files to attach

The whole folder `results/packets/round8/`:

- `README.md`;
- blind reports: `r7-blind-v1-as-run.report.md`, `r8-blind-v1-converter-corrected.report.md`;
- regression reports: `r8-dev-text-*`, `r8-offtemplate-rules-*`, `r8-dev-audio-rules-after`;
- `r8-ner-baseline.report.md`, `r8-fhir-r4-check.report.md`;
- `test_safety_fixes.py`, `architecture.md`, `project_README.md`;
- `pytest_output.txt`, `run_log.jsonl`.
