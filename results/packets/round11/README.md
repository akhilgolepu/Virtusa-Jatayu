# Evidence packet — evaluator round 11 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only).

What this round did not touch:

- No pipeline run on test or final_test, no real test clip read, and no release file created
  (`eval/real_test_release.json` does not exist).
- No merge into `main`, no force push, no history rewrite.

| # | Item | Status |
|---|---|---|
| 1 | Restore the tick for generic-name spelling variants; rerun dev speech | Done. Headline 5 of 480; 10 wrong drugs; sound ticks per note 0.11 / 1 / 2 (in-sample) |
| 2 | "Not stated" row per field, apart from the dangerous count; why 440 vs 480 | Done (`architecture.md` §6c, every run report) |
| 3 | `docs/demo_script.md`: 5-minute flow, timings, sentences, fallbacks | Done, plus a typed-path backup video |
| 4 | freeze_check and full tests | **FREEZE CHECK PASSED**; 460 passed, 12 xfailed, 0 skipped, 0 failed |

## 1. Generic-name spelling variants need the tick again (IN-SAMPLE)

The round-10 exemption is removed (`jatayu/extract/rules.py`). Every drug matched by sound with a spelling similarity
below 0.95 gets `sound_alike_drug` (high), generic-name variants and alias/brand variants alike. Alias/brand ticks are
unchanged.

**Tests:** the generic-name variants "ondansatron", "furosemid" and "kettamin" must be ticked; brand variants are
unchanged (`test_round9_drug_identity.py`).

Dev speech, rules, round-11 code, same saved transcripts; **in-sample**:

| | Round 10 (with the exemption) | **Round 11** |
|---|---|---|
| Headline dangerous errors (`r11-dev-audio-rules`) | 6 of 480 | **5 of 480**: 4 wrong dose/unit/route, 1 wrong drug; old matched-drug-only 1 of 440 |
| Wrong drugs recorded as a known drug (`r11-drug-identity`) | 10 | **10**: 4 matched by sound, all ticked; 6 an exact wrong word, no identity flag, 1 of those 6 with no high flag at all |
| Sound ticks per note, mean / p90 / max (`r11-tick-cost-final`) | 0.069 / 0 / 2 | **0.11 / 1 / 2** |
| All high-flag ticks per note, mean / p90 / max | 0.719 / 2 / 5 | **0.76 / 2 / 5** |
| Correct sound matches that need a tick | 29 | **49** |

One note = one dev speech clip, one dictated utterance.

- The extra headline error in round 10 ("furosenide 14 mg" for furosemide 40 mg) is covered again by the drug's tick.
- **Also at round-11 code:** noisy speech 6 of 360 (old 3 of 240); blind v1 rules 1 of 37 (old 0 of 34); typed dev 0 of
  480; off-template 3 of 71 (old 2 of 59). Entity F1 is unchanged (speech 0.644, typed 1.000, off-template 0.952).
- **Label fix:** `r11-tick-cost` was run before its option label was corrected ("round 9/10 code"); its numbers are
  identical to `r11-tick-cost-final`, which is the one reported.

## 2. "Not stated" per field, shown apart

**New in the scorer:** `not_stated` in `eval/metrics.py`; every run report now has the row. An empty field shows "not
stated" on the confirm screen, so it is an omission, never a wrong value, and never in the dangerous-error count.
The counts cover given and not-given **medication** records (procedures have no dose, unit or route):

- **drug:** no entry recorded at all;
- **dose, unit and route:** the recorded entry left the field empty, counted over records with an entry and that field
  in gold;
- **time:** the entry used the device clock.

Rules, round-11 code, exact:

| Not stated | Dev speech | Noisy speech | Blind v1 | Dev typed text |
|---|---|---|---|---|
| Drug (no entry at all) | 96 of 420 | 102 of 360 | 1 of 34 | 0 of 420 |
| Dose | 25 of 299 | 30 of 258 | 1 of 27 | 0 of 380 |
| Unit | 84 of 299 | 85 of 258 | 5 of 27 | 0 of 380 |
| Route | 89 of 276 | 64 of 122 | 3 of 30 | 0 of 360 |
| Time | 67 of 169 | 38 of 75 | 2 of 6 | 0 of 213 |
| *Dangerous errors (headline), for comparison* | *5 of 480* | *6 of 360* | *1 of 37* | *0 of 480* |

On speech these are mostly records the recogniser lost (96 of 420 medication records got no entry). That is the recall
problem (drug-term recall 0.574), shown so it is not mistaken for safety.

**Why the denominators differ** (checked against the dev split):

- **Old metric, 440:** gold records whose context is **given**: 380 medications and 60 procedures. It asks whether a
  given dose was recorded wrong, so a not-given record cannot be in it.
- **Headline, 480:** adds the **40 not-given** medications, because recording "not given" as given is a wrong status.
- **Measurement readings (40):** in neither; they are scored as context errors.
- **Noisy speech:** 240 given + 120 not-given = 360.
- **Blind v1:** 34 + 3 = 37.
- **Not-stated drug row:** its denominator (420) is the 380 + 40 medication records; procedures are excluded.

## 3. Demo script (`demo_script.md`)

**Structure:**

- a pre-demo checklist: power, **Wi-Fi off**, `./start_demo.sh` with every pre-flight line PASS, microphone permission,
  the backup video ready on a second device;
- a **5:00 flow with timings**, table form.

**Sentences:** six synthetic sentences to say into the microphone, with the card and checks each one produces. All were
checked through the app's typed path at round-11 code.

1. Adrenaline 0.3 mg IM, two minutes ago. A clean card; the read-back says the drug first.
2. "Allergic to morphine": two ticks, and it stays NOT GIVEN.
3. Ondansetron, "eight, no sorry, four": the correction is shown.
4. Adrenaline 10 mg: out of range and too soon, with spoken warnings; rejected.
5. Diclofenac: not in the drug list, kept as spoken.
6. "Started CPR at ten forty."

**Then:** the PDF and FHIR-lite JSON, Audit **Verify chain**, and a close that makes no accuracy claim on real speech.

**Fallbacks:**

- **Microphone fails:** the typed path, same sentences.
- **GPU or model fails:** rules only, with speech on the CPU
  (`JATAYU_ASR_DEVICE=cpu JATAYU_ASR_COMPUTE=int8 uvicorn …`). Measured: about 1.5 s for a 4-second clip, about 2 s for
  the first. This bypasses the pre-flight, which refuses a CPU recogniser by design, and the script says so. If speech
  fails entirely, use the typed path.
- **Screen fails:** the backup video.
- **Wi-Fi can't be switched off:** airplane mode or unplug, plus the pre-flight's sockets-blocked line.
- **Also covered:** a silent read-back, a misheard word, the wrong incident on screen.

**Backup video:** `docs/demo/demo_typed_flow.webm`. It is 42 s with no sound: the six sentences typed, both
confirmations including the two-tick dialog, the reject, Verify chain and the Incidents page. It was recorded
automatically with Playwright (`web/e2e/demo_video.mjs`) against a throwaway server with its own temporary database;
the demo database was not touched. The script recommends also recording one full spoken rehearsal with sound.

## 4. Freeze check and tests

- **Full suite at `4ea667c`:** **460 passed, 12 xfailed, 0 skipped, 0 failed**, model tests included
  (`pytest_output.txt`).
- **`python -m scripts.freeze_check --pytest`** on the pushed tree (`e4f7ead`): **FREEZE CHECK PASSED**
  (`freeze_check.json`):

  | Check | Result |
  |---|---|
  | tree | clean, pushed |
  | frozen | test + final_test text and audio match |
  | lock | 86 pins |
  | models | Whisper, LLM and voice hashes match |
  | config | rules, LLM-only off |
  | run_log | 134 rows; the 12 on test/final_test are all from clean trees |
  | tests | 460 passed |

- **Still open before the freeze:**
  - B1: real recordings not imported;
  - B2: their manifest hash, frozen after import;
  - B5: the evaluator's sign-off.

## Files changed (code, tests, docs; results not listed)

- **Code:** `jatayu/extract/rules.py` (exemption removed).
- **Evaluation:** `eval/metrics.py` (`not_stated`), `eval/run.py` and `eval/blind.py` (report row), `eval/tick_cost.py`
  (option label).
- **Tests:** `tests/test_metric_r10.py` (not-stated test), `tests/test_round9_drug_identity.py` (generic variants
  ticked again).
- **Demo:** `web/e2e/demo_video.mjs` (new), `docs/demo/demo_typed_flow.webm` (new), `docs/demo_script.md` (new).
- **Docs:** `docs/architecture.md`, `README.md`, `DECISIONS.md`.

## Files to attach

The whole folder `results/packets/round11/`, plus the video `docs/demo/demo_typed_flow.webm` (5.6 MB; not duplicated
into the packet):

- `README.md`;
- item 1: `r11-dev-audio-rules`, `r11-drug-identity`, `r11-tick-cost-final` (`.report.md`), `test_round9_drug_identity.py`;
- item 2: `r11-dev-noise-rules`, `r11-blind-v1-rules`, `r11-dev-text-rules`, `r11-offtemplate-rules` (`.report.md`),
  `test_metric_r10.py`, `architecture.md` (§6c);
- item 3: `demo_script.md`;
- item 4: `pytest_output.txt`, `freeze_check.json`;
- `project_README.md`, `run_log.jsonl`.
