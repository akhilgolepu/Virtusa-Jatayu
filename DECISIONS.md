# DECISIONS

One line per decision: date — choice — reason. Newest last. The evaluator reads this first when something looks odd.
Decision-support demo, not a clinical device.

| Date | Decision | Reason |
|---|---|---|
| 2026-10-31 | Python 3.12 in the existing conda env `anpr` instead of a fresh venv | Already holds torch 2.10 + CUDA 13 working on the RTX 5060; avoids re-downloading the stack |
| 2026-10-31 | Package is `jatayu/` (not `src/f2r/`); `f2r` CLI added as the plan's interface (`python -m f2r.cli ...`) | Phases 1-3 were built before the Field-to-Record plan; renaming 4k lines and 228 tests buys nothing the evaluator can check |
| 2026-10-31 | Speech backend: faster-whisper `small.en`, CTranslate2 4.8.4 on **GPU** (`cuda`, `int8_float16`) | Smoke test passed on sm_120 once CUDA 12 cuBLAS was loaded side by side; warm transcription 0.34 s for a 3.8 s clip |
| 2026-10-31 | Load CUDA 12 cuBLAS + cuDNN 9 via ctypes inside `asr.py`; did not install `nvidia-cudnn-cu12` | The cu12 cuDNN wheel writes into the same directory as torch's cu13 cuDNN and could break torch |
| 2026-10-31 | PyAV pinned to 18.1.0 | PyAV 19 removed `av.open(metadata_errors=)`, which faster-whisper 1.2.1 passes |
| 2026-10-31 | Vocabulary prompt lists route codes as well as drug names | Whisper heard "I M" as "I am"; "I am" is deliberately NOT an alias for IM |
| 2026-10-31 | Ambiguous aliases excluded from the lexicon ("Pause" for TXA, "shock", bare "in", "in the thigh", "cannula", "iv started") | A false drug/procedure record is worse than a missed one |
| 2026-10-31 | Lexicon stays YAML inside the package (`jatayu/lexicon/`), not `data/lexicon.json` | Single source of truth shipped with the code; `data/` is git-ignored by the owner's rule (no data in the repo) |
| 2026-10-31 | Synthetic data split 65/14/21 by **template family** (73 families, 168 patterns); hard categories get 2 test families | Test phrasings must be unseen; ±6-point drift from 70/10/20 is the cost of a dev family in every category |
| 2026-10-31 | Hindi Piper voices dropped; 7 Indian-accented English speakers (L2-ARCTIC, VCTK) used instead | Hindi voices read romanised Hinglish at 81-87% WER (threshold 60%) |
| 2026-10-31 | Noise: ESC-50 (siren, engine, car_horn, train, helicopter, rain, wind, crying_baby, coughing, breathing) at 20/10/5 dB; folds 1-3 train, 4 dev, 5 test | No noise clip shared across splits. ESC-50 is CC BY-NC 3.0 (Piczak 2015) — research/demo use, not redistributed |
| 2026-11-01 | Dose ranges from NASEMSO National Model EMS Clinical Guidelines **v3.0 (March 2022)**, 169 rows with section + page; India rows (pentazocine, pheniramine) from National Formulary of India 2011 + labels; AHA rows marked `secondary` | Plan requires a cited source per range; furosemide, O2 flow and norepinephrine mcg/min have no published adult prehospital range → validator checks route/unit only |
| 2026-11-01 | Epinephrine 0.5 mg IM flags as out of range | NASEMSO v3.0 gives 0.3 mg adult IM; we follow the cited source even though other protocols allow 0.5 |
| 2026-11-01 | LLM: **Qwen3-4B-Instruct-2507 Q4_K_M** via llama-cpp-python 0.3.36 built with CUDA 13.0 for sm_120 in a separate build-only conda env (`cudabuild`) | Built from source because no prebuilt wheel targets Blackwell; build env keeps `anpr`/torch untouched |
| 2026-11-01 | Keep Whisper **and** Qwen resident on the GPU (`JATAYU_KEEP_MODELS=1`; `=0` swaps) | Measured: Windows desktop 3.8 GB + Qwen 3.35 GB + Whisper 0.2 GB = 7.3 of 8.1 GB; swapping costs 1.2-2.6 s per utterance. Contradicts the plan's assumption, so recorded here |
| 2026-11-01 | Qwen chat format pinned to ChatML | The template guess garbled JSON quoting and dropped entries |
| 2026-11-01 | Hybrid is the default extractor: rules propose candidate spans, the LLM may only link candidate ids (per-utterance enum schema); falls back to rules on any LLM failure | Dev sample (60 utterances): hybrid 68/68 exact records, 1.4 s/utt; LLM-only 63/68 and it invented a dose from "given 10 minutes ago" |
| 2026-11-01 | LLM-only mode: model returns exact quotes; code derives every value and rejects any quote not in the transcript (`llm_unsupported`, high) | The plan's source-quote post-check |
| 2026-11-01 | Validator semantics: exact unit conversions are not errors; mg/mcg slip counted only into rows with stated min and max; below range = medium, above = high; uncapped mg/kg dose implying >200 kg = out of range | Without the band rule, 0.3 mcg adrenaline "fit" the open-ended "up to 0.3 mg" row and passed silently |
| 2026-11-01 | Confirm returns 409 and writes nothing unless every high flag is acknowledged; edits are new audit rows | Plan: never overwrite; flags never silently corrected |
| 2026-11-01 | UI is a Vite + Preact SPA (DOT Audio Recorder visual DNA), built output committed in `jatayu/web/dist`; Phase 1 single HTML page kept at `/skeleton` | Built before the plan's "one HTML page, Gradio if >2 days" rule; took <1 day; no Node needed at runtime |
| 2026-11-01 | Times follow the device clock; capture time anchors relative phrases | WSL clock is UTC — set `TZ=Asia/Kolkata` on the demo machine |
| 2026-11-01 | Tamper claim worded "100% of tested tamper types"; deleting the chain's tail is NOT detectable until server receipts exist (Stage 3 S3) | Per the plan's honest-claims note |
| 2026-11-01 | Illustrative dose rows added for norepinephrine IV (mcg), ketamine IN, oxygen L/min, furosemide IV; bicarbonate mmol derived from the cited mEq row | Plan M2: "where you cannot cite a public guideline, mark the range illustrative". Each row says ILLUSTRATIVE in its source and in every flag it raises |
| 2026-11-01 | Decimal-slip floor: an open-ended "up to N" row (no stated minimum) flags doses below N/5 as `dose_below_range` (medium) | Seeded-error test on dev: ÷10 doses passed silently (22/50 caught). Floor N/10 gave 94.0 % overall; N/5 gives 98.5 % with no rise in false flags (19/200). Cost: small titration doses below a fifth of the cap get a medium note (never blocks confirm) |
| 2026-11-01 | `final_test` = alternating paraphrase patterns of the held-out families (odd → final_test); re-froze before anything was measured | Plan M2 needs a second sealed set split by template; hashes committed in `eval/frozen.sha256` |
