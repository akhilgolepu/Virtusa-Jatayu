# Scribe108 — architecture

Draft, evaluator round 6. **Decision-support demo, not a clinical device. Adult patients only.** Every number below
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
 EXTRACT — rules-first extractor, LLM optional  (jatayu/extract/)
   rules (default): lexicon phrases + patterns; fuzzy/phonetic drug match (always flagged);
                    context cues (not given / measurement), self-corrections, ranges, repeat doses
   hybrid (optional): the rules layer finds candidate spans, a local LLM (Qwen3-4B, llama.cpp) only LINKS them
   llm (optional, ablation): the LLM quotes the transcript; any quote not in the transcript is rejected
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
   a "not given" or measurement entry is always status not-done, never a completed administration
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
- **Rules-first, LLM optional.** On dev the LLM linker added nothing measurable (table below), so `rules` is the default;
  `hybrid` and `llm` stay selectable and are reported as ablations.

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
| Speech, rules: entity F1 / dangerous / "not given" recorded as given | 0.673 / 1 of 440 / 2 of 40 | dev · synthetic |
| Speech, same transcripts: rules / hybrid / LLM-only entity F1 | 0.673 / 0.673 / 0.527 | dev · synthetic |
| Noise, same 160 utterances (hybrid): clean / 20 / 10 / 5 dB entity F1 | 0.653 / 0.633 / 0.624 / 0.567 | dev · synthetic |
| ASR options (100 clips): drug-term recall small.en / large-v3-turbo / distil-large-v3 | 0.648 / 0.523 / 0.318 | dev · synthetic |
| End of a 10-second dictation → confirm-screen payload: p50 / p95 | 0.387 s / 0.422 s (RTX 5060) | dev · synthetic dictation |
| Seeded dose errors caught (×10, ÷10, mg↔mcg, route) | 99.0% (198/200; 95% CI 96.4-99.7) — circular by construction | test · validator only |
| Harder seeded errors (×2, ×5, digit slip, mg→g) | 78.0% (156/200; 95% CI 71.8-83.2) | test · validator only |
| Correct gold doses flagged by the validator | dev 1.9%, test 0.3%, final_test 1.2% | dev / test · validator only |
| Full pipeline on test or final_test; any real recording | — | sealed / not yet recorded |

## 7. Known limits (each pinned by an expected-failure test or a DECISIONS row)

- Speech is the weak link: the recogniser misses drug names (57% heard exactly) and is much weaker on the
  Indian-accented synthetic voices. Whether this holds for real speakers is unknown until real recordings exist.
- Negation said after the drug ("naloxone was not given", "morphine nahi diya"); route corrections ("IM, sorry, IV");
  Hindi numbers and times ("ek", "do minute pehle"); per-kg doses ("1 mg per kg").
- A wrong dose that is still a legal dose cannot be caught by a range check; the residual risk depends on read-back
  confirmation, whose effectiveness we have not measured.

## 8. Deployment

WSL2 (Ubuntu) on the Windows laptop with an NVIDIA GPU; the browser runs on the Windows side at
`http://localhost:8000`. Whisper small.en and Qwen3-4B fit together in 8 GB. Clean-install steps are in
`DECISIONS.md` (2026-11-02); they have not yet been run on a clean machine.
