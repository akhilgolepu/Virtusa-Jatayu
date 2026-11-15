# Evidence packet — evaluator round 6 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only). No extractor, lexicon,
validator, prompt or threshold was changed in this round. No pipeline run on test or final_test. No force push, no
history rewrite, no merge.

| # | Item | Status |
|---|---|---|
| 1 | Blind set | **Not done — the file is not in the repo** |
| 2 | Push `f2r-evidence` | Done |
| 3 | Test / final_test audio with the spelled-route rule | Already done in round 4; verified now |
| 4 | Real-recording dry run, test sealed | Done, all checks pass |
| 5 | Architecture document and README | Done (drafts) |

## 1. Blind set — not done

`eval/offtemplate_blind_v1.yaml` is not in the repository, nor anywhere else on this machine:

- not in the working tree, and not in any branch or stash of git history;
- not in the Windows Downloads, Desktop or Documents folders (searched by name, `*blind*`).

It is evaluator-authored, so I have not written it. As soon as the file is placed at `eval/offtemplate_blind_v1.yaml`,
I will follow its header protocol exactly:

- read only the header first;
- convert the cases with a script, without touching the gold;
- run rules, hybrid and LLM-only once each, logged in `run_log.jsonl`;
- report aggregates per tier (core, stretch): entity F1, exact match, dangerous errors, administration-status errors,
  flags raised;
- read individual errors only after that report. No tuning on it.

## 2. Push

`f2r-evidence` is pushed to `origin` as its own branch at `af8b816` (this packet's commit follows, same branch).
`main` is untouched (`5713056`). Before pushing I checked four things:

- `origin/main` is an ancestor, so no force was needed;
- 0 co-author lines;
- no data, planning docs, models or databases are tracked;
- no individual test or final_test record is in any tracked file: 0 test/final_test ids. The only sentence-level match
  is one 43-character test sentence that also occurs as a clause inside a longer dev sentence (counts only, nothing
  printed).

The `m1-pass` tag and the two `backup/*-pre-strip` branches (old history with co-author lines) stay local.

Commit maps for the earlier message rewrite:

- `commit-map-full-76.txt` (= `results/commit_map_2026-11-03.txt`): every rewritten commit, old → new, with the
  unchanged tree hash.
- `commit-map.txt` (= `docs/commit-map.txt`): every hash referenced in run logs, setup_check.json, metrics files,
  packet READMEs and DECISIONS → current hash. 0 not found.

## 3. Audio

Yes: test and final_test audio was re-rendered with `datagen/tts.py::speakable` (route abbreviations spelled) in
round 4, commit `f64572b`, and frozen by per-clip manifest. Re-verified today, counts only:

| Split | Clean clips rendered from the spoken-rule text | Clips whose text the rule changes | Manifest + every clip vs `eval/frozen.sha256` |
|---|---|---|---|
| test | 1,200 / 1,200 | 357 | verified |
| final_test | 900 / 900 | 273 | verified |

Nothing was re-rendered and no pipeline was run on them.

## 4. Real recordings — dry run

`python -m scripts.recording_dry_run --tag r6-recording-dry-run` (`r6-recording-dry-run.report.md`) uses a dummy
2-second tone in a throwaway folder; `data/real/` is never touched and no real clip exists.

- **Recording page:** `/record` loads (200). The real prompts (60 dev, 180 test) are all still to be recorded.
- **Upload:** the dummy DEV take is transcribed and checked. The dummy TEST take is saved **sealed**: not transcribed,
  no WER.
- **Import:** `python -m scripts.import_real --from-recordings --speaker DRY01` imports 1 dev and 1 test take;
  re-running it imports 0.
- **Sealing:** `load_real("dev")` returns 1 clip. `load_real("test")` **refuses**: "real test recordings are sealed
  until the evaluator says so".

## 5. Docs (drafts)

- `architecture.md` (= `docs/architecture.md`) covers the pipeline, the design rules, knowledge, the evaluation design,
  measured numbers and known limits.
- `project_README.md` (= `README.md`) covers run, extractor, what has been measured, recording and evaluation.
- Every number is labelled **[dev · synthetic]**, **[dev · hand-written]**, **[test · validator only]** or
  **[sealed]**.
- The wording is "rules-first extractor, LLM optional"; neither file says "small LLM" or "NER".
- One number measured this round is left out because no harness wrote it: the PDF note took 17 ms for a 10-entry
  incident and 79 ms for a 50-entry one (an in-process check).

## Files to attach

The whole folder `results/packets/round6/`:

- `README.md` (this file);
- `r6-recording-dry-run.report.md`;
- `architecture.md`;
- `project_README.md`;
- `commit-map.txt`;
- `commit-map-full-76.txt`.
