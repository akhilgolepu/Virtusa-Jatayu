# Freeze checklist — before the one test run

Scribe108 is a decision-support demo, not a clinical device. This list says what must be true before the single
evaluation on the sealed **test** split, and how to run it once. The **final_test** split stays sealed until Stage 3
week 7 (S7).

The mechanical items are checked by one command. Each line prints PASS or FAIL, and the command exits 1 on any FAIL:

```bash
conda activate anpr && source scripts/env.sh
python -m scripts.freeze_check --pytest --out results/<freeze-tag>/freeze_check.json
```

`freeze_check` never prints a test or final_test record, and never reads the real recordings.

## A. Mechanical — `scripts/freeze_check.py` must pass every line

| # | Item | What must be true | Checked by |
|---|---|---|---|
| A1 | Clean tree | `git status` is clean except `results/` (results are outputs, as in `eval/runlog.py`). HEAD is pushed to `origin/f2r-evidence`. | `tree` |
| A2 | Tests | The full suite passes, model tests included: 0 failed and 0 skipped (the GPU, Whisper, the LLM and the voice are all present). | `tests` (`--pytest`) |
| A3 | Frozen hashes | `data/test/test.jsonl` and `data/final_test/final_test.jsonl` match `eval/frozen.sha256`. Every test and final_test audio clip matches its frozen manifest. The file has not changed since `f64572b` (`git log -- eval/frozen.sha256`). | `frozen` |
| A4 | Pinned versions | Every package that `requirements.txt` pulls in is installed at its `requirements.lock` version (86 pins). llama-cpp-python is the CUDA 13.0 / sm_120 source build (DECISIONS.md). | `lock` |
| A5 | Model files | Whisper `model.bin`, the Qwen3-4B GGUF and the read-back voice match `eval/models.sha256`, which was recorded in round 9 with `--record-models`. Re-record only if a model is deliberately changed **before** the freeze. | `models` |
| A6 | Config | The committed defaults are in force: no `JATAYU_*` variable in the environment, extractor `rules`, LLM-only experimental switch off. The snapshot (ASR model, device, compute type, word-probability threshold, LLM file) is written to the JSON. | `config` |
| A7 | run_log | No row of `results/run_log.jsonl` on test or final_test comes from a dirty tree. `eval/runlog.py` already refuses such a run. | `run_log` |

The thresholds frozen with the code are in code, not in the environment:

| Threshold | Value | Defined in |
|---|---|---|
| ASR word probability (`low_asr_confidence`) | 0.2 | `jatayu/config.py` |
| Fuzzy drug match | 88 | `RulesExtractor` |
| Phonetic drug match | 84 | `rules.py` |
| Low-confidence line | 0.95 | `rules.py` |
| Sound-alike acknowledgement (`SOUND_ACK_BELOW`) | 0.95 | `rules.py` |
| Route/unit-shaped junk guard (`ROUTE_LIKE`) | 75 | `rules.py` |
| Duplicate-dose window | 120 s | `validate.py` |
| Dose ranges | cited per row | `jatayu/lexicon/dose_ranges.yaml` |

## B. Before the freeze commit — not automatic

| # | Item | Must be true | Status in round 9 |
|---|---|---|---|
| B1 | Real recordings | Takes are recorded on `/record` and imported with `python -m scripts.import_real --from-recordings --speaker S0x` (anonymous ids). The real test takes land in `data/real/test`, which is sealed. | **Open.** No real clips have been imported yet (`data/real` does not exist). |
| B2 | Real test frozen | The real test manifest's SHA-256 is added to `eval/frozen.sha256`. Today `load_real` checks clips against their manifest, but nothing pins the manifest itself. | **Open.** Add it at import time, before the freeze commit. |
| B3 | Real test scoring path | `load_real("test")` refuses without `sealed_ok`, and no runner passes it yet. A reviewed runner (aggregate output only, dirty-tree refusal, run_log row) must exist **in the freeze commit**. | **Open.** Code, so it must land before the freeze. |
| B4 | No tuning on sealed data | No real clip's transcript has been read for tuning. No test or final_test record has been printed. Dev, off-template and blind v1 (spent) are the only data that informed the code. | Holds. |
| B5 | Evaluator sign-off | The evaluator has the freeze commit hash and has said to run. | Pending. |
| B6 | Docs | Every number in `README.md`, `docs/architecture.md` and the slides is labelled (synthetic / dev / hand-written / blind / sealed) and traces to a clean run_log row. The known limits are current. | Round-9 docs updated. |
| B7 | Demo path | `./start_demo.sh --check-only` passes on the demo laptop: GPU, models, voice, offline, config, audit chain, port. | Passes (round 9, `results/r9-preflight/`). |

## C. The freeze

1. `python -m scripts.freeze_check --pytest --out results/freeze-v1/freeze_check.json` reports **FREEZE CHECK PASSED**.
2. Tag the commit: `git tag -a freeze-v1 -m "code freeze for the test run"`. Push the branch and the tag (no force).
3. From here on, nothing in `jatayu/`, `eval/`, `datagen/` or the lexicon changes until the test results are reported.

## D. The one test run

Run each line **once**, from the tagged commit with a clean tree. The harness refuses a dirty tree, verifies the
frozen hashes and the audio manifest, writes aggregates only (no per-record errors, no transcripts), and logs a
run_log row with the commit.

```bash
python -m eval.run --split test --tag freeze-v1-test-text-rules  --extractor rules --mode text
python -m eval.run --split test --tag freeze-v1-test-audio-rules --extractor rules --mode audio
# hybrid only if agreed with the evaluator beforehand; LLM-only is experimental and is not run on test
# real test clips: only through the B3 runner, once B1-B3 are closed
```

Rules for the run:

- **No re-runs.** If a run crashes, the crash and its run_log row are reported. A second attempt is made only with the
  evaluator's agreement, and it is labelled as a second attempt.
- **Commit at once.** The results and run_log rows are committed straight away and reported as they come out, next
  to the dev numbers. They are not compared run by run against anything tuned.
- **Aggregates only.** Never print or read individual test records, and never read a real test transcript.
- **final_test:** not before S7, and only with `--sealed-ok`.
