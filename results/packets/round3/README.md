# Evidence packet — evaluator round 3 (branch `f2r-evidence`)

Product: **Scribe108** (decision-support demo, not a clinical device; adult patients only). Items 1-13 of round 3
only; round-2 items are in `results/packets/round2/`. Every number below was written by the harness, and the reports
next to this README are copies of harness output. **Dev data only**: no pipeline run was made on test or final_test
this round, and no test or final_test record is printed anywhere.

Commits (local, unpushed): `104a0b7` (item 7) · `b56be0a` · `54f5e29` · `988e764` (item 10) · `4351849` (item 8) ·
`f0ae275` · `c0ff23e` (dev runs start here) · `760ebd2` (final code; `m1-pass`) · `dc29f79` (packets).
All round-3 dev runs started on a clean tree (`dirty: false` in `run_log.jsonl`), at `f0ae275` (text rules and
off-template rules) or `c0ff23e` (everything else). The exception is the first ASR diagnosis (`cb82312-dirty`,
explained in its NOTE).

## 1. Speech diagnosis

**Where the 0.63 came from.** Round-2 WER compared the template text word for word with Whisper's output
("seven point five mgs" vs "7.5 MGS"). With reference and hypothesis normalised the same way (`eval/asr_text.py`:
numbers via the pipeline's normaliser, unit/route words → lexicon code), the same 100 dev clips go from 0.616 to
**0.398**. A second cause was in the audio itself: Piper read a bare "iv" as the Roman numeral ("Roman four"; 8 of 9
such clips).

One change at a time on 100 dev clips (seed 3); extraction = rules (deterministic). The same 100 clip identities
before and after the TTS fix (`r3-asr-diag*.report.md`):

| Setting (after the TTS fix) | WER raw | WER normalised | Drug-term recall | Entity F1 (rules) |
|---|---|---|---|---|
| baseline: small.en, beam 5, VAD on, prompt on | 0.603 | **0.366** | 0.648 | 0.704 |
| VAD off | 0.604 | 0.366 | 0.648 | 0.701 |
| vocabulary prompt off | 0.677 | 0.492 | 0.330 | 0.474 |
| beam 1 | 0.598 | 0.366 | 0.659 | 0.690 |
| beam 10 | 0.606 | 0.379 | 0.636 | 0.697 |
| medium.en | 0.585 | 0.353 | 0.659 | 0.693 |
| *before the TTS fix: baseline* | *0.616* | *0.398* | *0.636* | *0.671* |

- **16 kHz mono confirmed.** All 100 files are 16 kHz, mono, 16-bit. Whisper receives 1-D float32 at 16 kHz, with no
  duration mismatch.
- **Fixes applied (only what the evidence supports; DECISIONS 2026-11-02):**
  - normalised WER is the headline, with raw WER reported next to it;
  - the TTS input spells route abbreviations. 153 of 480 dev clips were re-rendered. Before → after on the same 100
    clips: "roman" 8 → 0, WER 0.398 → 0.366, route F1 0.571 → 0.635.
- **Kept:** small.en, beam 5, VAD and the prompt.
  - VAD makes no difference.
  - The prompt is essential.
  - Beam size changes WER by at most ±0.013.
  - medium.en gains 0.013 WER but loses entity F1 and adds about 50% latency.
- **Remaining error by voice.** It sits in the multi-speaker Piper voices: normalised WER 0.193 for the single-speaker
  US/GB voices vs **0.466** for the L2-ARCTIC/VCTK Indian-accented voices. medium.en does not close the gap.
- **Not re-rendered:** test and final_test audio. They must be re-rendered with the same rule before any test speech
  run.

**Full dev speech, hybrid** (`r3-dev-audio-hybrid`, 480 clips, after the fix):

- WER normalised **0.402** (raw 0.634).
- By accent: us 0.260 · gb 0.260 · in 0.522.
- Drug-term recall **0.574** (n = 460 gold drugs named in a form the lexicon recognises).
- Entity F1 0.633.
- Per-field entity F1: drug 0.768 · dose 0.620 · unit 0.620 · route 0.560 · time 0.450 · procedure 0.750.
- Entity F1 by accent: gb 0.795 · us 0.729 · in 0.523.

Ten random dev (reference, transcript) pairs are at the end of `r3-asr-diag.report.md` (before the fix) and
`r3-asr-diag-after-tts-fix.report.md` (after).

## 2. Noise curve, paired

Entity F1 on the **same 160 dev utterances** (one voice each), hybrid extractor, same ASR, at every condition. The
clean condition reuses the clean transcripts of item 1 (`r3-dev-noise-paired-hybrid.report.md`):

| Condition | clean | 20 dB | 10 dB | 5 dB |
|---|---|---|---|---|
| Entity F1 | **0.653** | 0.633 | 0.624 | 0.567 |

The round 2 curve (unpaired, no clean point, before the TTS fix) was 0.636 / 0.611 / 0.550.

## 3. Speech ablation (same ASR transcripts, dev)

All three read `results/r3-dev-audio-hybrid/transcripts.jsonl` (480 clips).

| Extractor | Entity F1 | Exact | Dangerous (strict) | Administration-status | Context |
|---|---|---|---|---|---|
| rules | 0.632 | 0.327 | 1/440 | 4/40 | 10/80 |
| LLM only | 0.526 | 0.165 | 0/440 | **21/40** | 25/80 |
| hybrid | 0.633 | 0.310 | 3/440 | 4/40 | 10/80 |

On speech, hybrid ≈ rules. The LLM-only extractor scores 0/440 dangerous errors because it rejects so many values that
they arrive already flagged. It records 21 of 40 not-given drugs as given.

## 4. Context errors and administration-status error

- **Breakdown of the round-2 20/80** (template dev set, rules):
  - not given: 0/40;
  - refused, other: none in the dev families (dev has one not-given family, cn04, and one measurement family, cm05);
  - **measurement: 20/40**, all one pattern: "serum magnesium 0.7".
- **Fix:** lab and monitor qualifiers added to the measurement cues. Dev rules: **20/80 → 0/80**. This is a dev number by
  construction.
- **New metric:** administration-status error = a not-given gold record emitted without `possible_not_given`. It sits
  next to the dangerous-error row in every report.

| Dev run | Dangerous (strict) | **Administration-status** | Context |
|---|---|---|---|
| text, rules | 0/440 | 0/40 | 0/80 |
| text, hybrid | 5/440 | 0/40 | 0/80 |
| text, LLM only | 3/440 | **37/40** | 37/80 |
| speech, hybrid | 3/440 | 4/40 | 10/80 |
| noisy speech, hybrid (clean + 3 SNR) | 3/240 | 13/120 | 30/240 |

## 5. Dangerous errors, categorised

`r3-dangerous-breakdown.report.md` covers the 7 round-3 dev runs; `r3-dangerous-breakdown-round2-runs.report.md`
covers the 5 round-2 runs. Every record is listed (dev).

- **Round 3: 15 dangerous records.**
  - Field: dose_value 15/15.
  - Why no flag: 15/15 are wrong values that are themselves a valid dose for that drug and route.
  - Origin: **10 extraction**, all self-corrections ("1.5, no, 8 mg") where the LLM (hybrid 7, LLM-only 3) linked the
    value before the correction, although the rules layer reads it correctly. **5 ASR**: "fifty" heard as "15" (one
    utterance, counted 4 times across runs) and "sixty" as "6".
- **Round 2: 14 records.** Same picture: 10 self-corrections, 4 ASR.
- Not fixed (item 5 asked for the breakdown only). The obvious next fix: when the rules layer saw a correction and the
  LLM's dose differs, keep the rules value or flag the disagreement.

## 6. JSON fallbacks

The cause is unconstrained array length. The model repeated one entry until `max_tokens=512` and the JSON was cut off
(`finish_reason == "length"`), as in "started chest compressions at 1028" → `{"procedure": 1}` repeated until the token limit.

- **Fix:** `maxItems` = one entry per drug/procedure candidate, and `LlmRunner` reports truncation explicitly.
- Reproduced on 70 dev transcripts: 3 fallbacks → **0**; the longest output went from 512 to 73 tokens.
- Full reruns: speech 10 → **0**, noise 5 → **0**; text and off-template 0 (`r3_console.log` has no fallback line).

## 7. Reproducibility

- `results/m3-dev-evals.log` is untracked, and `results/*.log` is ignored.
- Every run-log row has `dirty` and `dirty_paths`.
- `eval/runlog.py` **refuses** test/final_test on a dirty tree (`DirtyTreeError`; a refused run is not logged).
  `results/` does not count as dirty.
- Tests: `tests/test_runlog.py`.
- Also: test/final_test pipeline runs now write aggregates only.

## 8. G0 fixes

`results/packets/g0/` was re-run at `760ebd2`: **all_pass**.

- **Offline check:** the socket-blocked check now covers ASR, **the LLM smoke test** (3 entries) and TTS.
- **CUDA versions now recorded:**
  - driver CUDA 13.5 (round 1 recorded "unknown": the parser missed "CUDA UMD Version");
  - torch runtime 13.0;
  - llama-cpp on the cuda-runtime 13.0.96 wheel;
  - CTranslate2 4.8.4 on cuBLAS 12.9.3.13.
- G0 README, DECISIONS copy and nvidia-smi updated.

## 9. M1 packet

Everything in `results/packets/m1/` was rebuilt in one go at **`760ebd2`** by `bash scripts/m1_packet.sh` on a clean
tree:

- `commit.txt`, the 10 samples, verify before/after tamper and the tamper suite (14 passed);
- the worst failures;
- **full pytest: 343 passed, 13 xfailed, 0 skipped, 0 failed, nothing deselected** (GPU free; model tests ran).

**Tag `m1-pass` → `760ebd2`** (local, not pushed).

## 10. FHIR safety

- **Before:** "patient allergic to morphine", confirmed with the high flag acknowledged, became
  `MedicationAdministration status: completed`.
- **Now:** any entry flagged `possible_not_given` or `possible_measurement` gets **`not-done` + `statusReason`**, in the
  draft and after confirm; a rejected entry stays `entered-in-error`. The PDF status reads NOT GIVEN / READING.
- `not-done` and `statusReason` are added to the schema.
- Tests: `tests/test_fhir_safety.py`. Four utterances (allergy, did not give, refused, blood glucose) go through the API,
  are confirmed, and are checked in the bundle and the PDF. A given entry still completes.

## 11. Off-template dev set

`offtemplate_dev.yaml` holds 40 dev-only cases: the 5 M1 worst failures plus 35 hand-written ones (negations, ranges,
"then another", corrections, Hinglish, fillers, borrowed times). There are 13 known rules failures, each
`xfail(strict)` with its reason in `tests/test_offtemplate.py`.

- **Fixed first:**
  - "2 to 4 mg" → `dose_range_stated` (high);
  - "then another X" → a second entry, flagged `repeat_dose_inferred`;
  - a time from another clause → `time_borrowed`.
- **Rules cases passing:** round-2 code 15/40 → **27/40**. The 12 gained are exactly those three classes, and I wrote
  both the cases and the fixes, so that gain is circular.

| Extractor (harness) | Entity F1 | Exact | Dangerous | Administration-status |
|---|---|---|---|---|
| rules | 0.929 | 0.647 | 2/42 | 3/9 |
| LLM only | 0.862 | 0.647 | 1/42 | 3/9 |
| hybrid | 0.938 | 0.686 | 2/42 | 3/9 |

The 2 dangerous errors under rules are the route corrections ("5 mg IM, sorry, IV"). The 3 administration-status
errors are negations said after the drug ("naloxone was not given", "morphine nahi diya") and an abandoned intent.

## 12. DECISIONS.md (rows dated 2026-11-02, round 3)

- **(a) Deployment target: WSL2 on the Windows laptop.** The browser runs on the Windows side. The clean-install plan
  has 8 steps and has **not yet been run on a clean machine**.
- **(b) Adult patients only.**
- **(c) The seeded-error numbers are circular by construction.** The better indicator is the gold-audit false-flag
  rate: dev 7/359 (1.9%), test 1/291 (0.3%), final_test 2/168 (1.2%).

## 13. Wording

`wording_draft.md` is the README/slides draft. It covers 81.5 → 98.5 (tuned on its own set) → 94.5 (superseded data)
→ 99.0 (circular), and the harder set at 78.0% with its miss breakdown, each with its caveat.

## Still waiting on the human

- Real-recording WER.
- A Wi-Fi-off run.
- `gh auth login` and push. Nothing has been pushed; `0f1b65e` is kept local.
