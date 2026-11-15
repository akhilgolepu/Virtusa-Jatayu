# Evidence packet — evaluator round 12 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only).

What this round did not touch:

- No pipeline run on test or final_test, no real test clip read, and no release file created
  (`eval/real_test_release.json` does not exist).
- No merge into `main`, no force push, no history rewrite.
- No extractor, validator or confirm-flow change this round.

| # | Item | Status |
|---|---|---|
| 1 | Docs: different metrics, not "down from"; PDF timings from the logged round-7 run | Done |
| 2 | Required fields per note; confirm-time enforcement test | Done. **Not enforced** (stated, pinned by tests, not fixed) |
| 3 | Read-back test harness | Done. Tested with dummy testers only |
| 4 | Real recordings: `eval/real_wer.py` per speaker | **Waiting**: no real recordings have been imported (`data/real` does not exist) |

## 1. Docs

- **"down from":** no current document contained it.
- **Comparing the two metrics:** the places that framed the headline against the old metric as a change are reworded
  to say they are **different metrics, not a before and after**:
  - `architecture.md` §6c ("the counts grow because…");
  - the round-10 `DECISIONS.md` row (arrows from old to new);
  - `README.md`, a new sentence under the extractor table.
- **Unchanged:** arrows that compare one metric with itself across rounds, and the earlier packets, which are left as
  reviewed.
- **PDF timings:** both rows already gave 19.8 ms / 87.4 ms. They now cite the source: the round-7 logged run
  `r7-pdf-latency`, 30 timed runs, p95 28.6 / 111.3 ms. The unlogged re-timing (17 / 79 ms) is in no current document;
  it appears only in the round-6 packet, which says it was left out.

## 2. Required fields (drug, dose, unit, route)

`eval/required_fields.py` (`r12-required-fields.report.md`) runs on dev speech: rules NER, saved transcripts, 480
clips; one note = one clip.

| Per note | Mean | p90 | Max | Notes with any |
|---|---|---|---|---|
| Required fields left empty on the recorded entries | **0.81** | **2** | **7** | 228 of 480 |
| Medication records with no entry at all (apart) | 0.20 | 1 | 2 | 93 of 480 (96 records) |

- **Empty fields by type** (out of 370 recorded medication entries): drug 0, dose 51, unit 155, route 182.
- **Lost records:** the 96 medication records with no entry have nothing on the confirm screen to fill. They would have
  to be re-dictated or typed, so they are not mixed into the per-note figure.

**Enforcement** (`test_required_fields_confirm.py`): **not enforced**. Each requirement is written as an
`xfail(strict=True)` test. Both fail today (recorded as `XFAIL` in `pytest_output.txt`), and they will turn into errors
the day it is enforced:

- **A dose with no unit:** `field_missing` (high) blocks confirmation until it is **ticked**, but the tick is enough.
  The entry is confirmed with the unit still empty; no unit entry or explicit "unknown" is required.
- **An entry with no drug:** the extractors never create one, but an edit can blank the drug. Nothing then flags it,
  and it **confirms with no tick at all**.
- **The UI:** the unit and route lists offer "not stated", never "unknown", and the edit form has no drug field.

Three plain tests pin down today's behaviour exactly. Not fixed this round, as asked. The limitation is in
`architecture.md` §7.

## 3. Read-back test harness

A separate small app, `jatayu/readback_trial.py`:

- **Running it:** `python -m scripts.readback_test_server`, then open `http://localhost:8010/readback-test`.
- **Isolation:** it binds 127.0.0.1 and has its own store. It only reuses the read-back voice and the lexicon; nothing
  in the pipeline changed.

**Testers:** an anonymous code (capital letters then digits, e.g. T01). Names, lower case and spaces are refused.

**Records:** 24 synthetic records per tester in a seeded random order (seed `scribe108-readback-v1` + code). The same
code always gets the same set and order. One record per drug, so a tester cannot judge one record by remembering
another.

| Records | Count | How it differs from the order |
|---|---|---|
| Correct | 10 | — |
| Wrong but valid drug | 6 | another drug valid at the same dose and route |
| In-range wrong dose | 4 | another dose inside the drug's cited range |
| Wrong route | 4 | another route the drug is given by |

The validator raises **no flag** on any record, so only the tester can catch an error.

**A trial** (`readback-test-say.png`, `readback-test-confirm.png`):

1. "Say this aloud: Gave 50 milligrams diphenhydramine intravenous."
2. The order is hidden. The record appears on a confirm-style card, drug first and units in full, while the real
   read-back speaks it.
3. **Confirm** or **Needs correction**, enabled after the read-back ends; replay is allowed.

**Nothing about errors, flags, the mix or counts is shown:** no progress counter, no feedback.

**Answer key:** stays in the server's store (`sessions/<code>.json`). The page receives only an opaque token, the order
text and the record. A test scans every response for any type or key field.

**Stored:** tester code, token, answer, response time. No names, no audio (the read-back is synthesised on request and
never written), no transcripts.

**Output:** `python -m eval.readback_test_report --tag …` gives the catch rate per error type and the false-alarm rate
on correct records, each with a Wilson 95% interval, aggregate only.

**Tests** (`test_readback_trial.py`, 15 tests, dummy testers only):

- the mix, the seeded order and one drug per tester;
- each wrong record differs in exactly its field and stays validator-clean;
- names refused;
- the page and every response carry no key, and the page has no external URL;
- order enforcement, opaque tokens, resuming a session;
- the store holds no audio and no extra fields;
- the aggregate's numbers and Wilson intervals are exact for scripted testers;
- the report is aggregate only;
- the audio is the real read-back (model test).

**Example report** (`r12-readback-test-DUMMY.report.md`), from 4 dummy testers with scripted answer policies. It is a
**format check, not a result**: wrong drug 18 of 24, wrong dose 8 of 16, wrong route 4 of 16, false alarms 10 of 40,
each with its Wilson interval. These are exactly what the four policies imply. **No human has taken the test yet.**

## 4. Real recordings

Not imported yet: `data/real` does not exist. So `eval/real_wer.py` (real dev against Piper dev, per speaker) was not
run, and nothing was tuned.

Once the takes are imported (`python -m scripts.import_real --from-recordings --speaker S01`), the run is:

`python -m eval.real_wer --tag r12-real-vs-piper --piper results/r11-dev-audio-rules`

It reports normalised WER, raw WER and drug-term recall, overall and per speaker. Real test takes stay sealed:
`real_wer` refuses them. Per the evaluator, no tuning on these numbers until the report has been reviewed.

## Tests and freeze check

- **Full suite at `52a0729`:** **478 passed, 14 xfailed, 0 skipped, 0 failed**, model tests included. The 2 new
  expected failures are the item-2 enforcement tests (`pytest_output.txt`).
- **`python -m scripts.freeze_check --pytest`** on the pushed tree (`41d79da`): **FREEZE CHECK PASSED**
  (`freeze_check.json`).

## Files changed (no pipeline code)

- **Docs:** `README.md`, `docs/architecture.md` (§6 row, new §6d, §7 limitation, §6c wording, PDF citation),
  `DECISIONS.md`.
- **Evaluation:** `eval/required_fields.py` (new), `eval/readback_test_report.py` (new).
- **Read-back harness:** `jatayu/readback_trial.py` (new; the separate app), `scripts/readback_test_server.py` (new).
- **Tests:** `tests/test_required_fields_confirm.py` (new), `tests/test_readback_trial.py` (new).

## Files to attach

The whole folder `results/packets/round12/`:

- `README.md`;
- `r12-required-fields.report.md`, `test_required_fields_confirm.py`;
- `readback-test-say.png`, `readback-test-confirm.png`, `r12-readback-test-DUMMY.report.md`, `test_readback_trial.py`;
- `architecture.md`, `project_README.md`;
- `pytest_output.txt`, `freeze_check.json`, `run_log.jsonl`.
