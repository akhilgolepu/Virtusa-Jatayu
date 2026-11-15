# Scribe108

Offline voice scribe for ambulance medication and procedure notes. A responder speaks ("gave 0.3 mg adrenaline IM two
minutes ago"); the app transcribes on the laptop, extracts drug / dose / unit / route / time, checks the dose against
a cited adult range, shows every value with the words it came from for confirmation, and writes a FHIR-lite record and
a PDF. Every step is appended to a hash-chained audit log.

**Decision-support demo, not a clinical device. Adult patients only.** All accuracy numbers so far come from synthetic
(template and Piper TTS) data; nothing has been measured on real ambulance speech yet.

## Run it

Target: WSL2 (Ubuntu) on the Windows laptop with an NVIDIA GPU; the browser runs on the Windows side.

```bash
conda activate anpr
bash scripts/download_assets.sh          # once, online: models, voices, noise
python -m scripts.setup_check            # every line must say PASS (GPU, ASR, LLM, TTS, offline)
export TZ=Asia/Kolkata                   # WSL's clock is UTC; times are read relative to the device clock
./start_demo.sh                          # pre-flight (fails loudly), then the server on 127.0.0.1:8000, then the browser
```

`./start_demo.sh --check-only` runs only the pre-flight. It checks:
- the GPU;
- that the Whisper model, the LLM file and the read-back voice are present;
- that Whisper transcribes a clip on the GPU and the voice speaks, both with the network blocked;
- the offline variables;
- the demo config;
- the audit chain;
- the port.

The server alone is still `uvicorn jatayu.api:app --host 127.0.0.1 --port 8000`. The read-back test harness is a
separate app: `python -m scripts.readback_test_server`, then open `http://localhost:8010/readback-test`
(`docs/architecture.md` §6d). Before the one test run, follow
`docs/freeze_checklist.md`.

## NER: rules-first clinical NER, with optional LLM-assisted NER

Entities are recognised by a **rules-first clinical NER (lexicon and patterns), with optional LLM-assisted NER**. The
entity types are **drug, dose value, dose unit, route, time and procedure** (plus a procedure detail such as a tube size,
which is extracted but not scored); each recognised drug or procedure also gets an administration status (given / not
given / measurement). Every value points at the transcript words it came from. There is no trained NER model. In the
optional modes a local LLM (Qwen3-4B via llama.cpp) either links the spans the rules found (`hybrid`) or quotes the
transcript directly (`llm`; quotes are checked).
- `rules` is the default (`JATAYU_EXTRACTOR`, the selector on the capture screen).
- `hybrid` stays selectable.
- **LLM-only (`llm`) is experimental.** It is off the demo path and the app offers it only when started with
  `JATAYU_EXPERIMENTAL=1`; the UI then labels it "experimental". It has none of the round-8/9 safety fixes. It is
  still scored on dev for comparison.

Why — measured on the dev split, synthetic speech (Piper voices) and our own hand-written sentences, evaluator round 4
(DECISIONS 2026-11-03). Labels: **[dev · synthetic]**, **[dev · hand-written]**.

| Extractor | Speech entity F1 [dev · synthetic] | Off-template F1 [dev · hand-written] | Speech dangerous errors, **headline** (round-10 definition, re-scored, upper bound) [dev · synthetic] | Speech dangerous errors, matched-drug only (old, secondary) | Speech "not given" recorded as given [dev · synthetic] |
|---|---|---|---|---|---|
| rules | 0.673 | 0.948 | ≤ 8/480 | 1/440 | 4/40 (2/40 after round 5) |
| hybrid | 0.673 | 0.950 | ≤ 11/480 | 1/440 | 4/40 |
| LLM only (experimental) | 0.527 | 0.894 | ≤ 16/480 | 0/440 | 21/40 |

The headline dangerous error (round 10) is a wrong drug, dose, unit, route or status recorded without a flag the medic
must tick. The old, secondary metric only looked at records whose drug matched, so it could not see a wrong drug.
They are **different metrics**: the two columns are not a before and after, and neither is a change of the other. The
round-4 runs did not store everything the headline needs, so these are upper bounds (`docs/architecture.md` §6c).

The LLM added nothing measurable, and costs ~0.6-0.9 s per utterance and 3.35 GB of GPU memory.

```bash
JATAYU_EXTRACTOR=hybrid uvicorn jatayu.api:app --port 8000   # to run with LLM-assisted NER (hybrid) instead
```

## What has been measured

All numbers so far are labelled **[dev · synthetic]** (template sentences, Piper voices; we tuned on dev),
**[dev · hand-written]** (our own sentences), or **[test · validator only]** (the dose checker on gold labels; the full
pipeline has never been run on test). The full pipeline on test and final_test, and every real recording, are
**[sealed]**: not measured yet.

| Measure | Result | Label |
|---|---|---|
| Speech: normalised word error rate | 0.406 (US 0.26, GB 0.26, Indian-accented 0.53) | dev · synthetic |
| Speech: drug names heard (target 0.90) | 0.574 — target not met | dev · synthetic |
| Speech, rules: entity F1 | 0.644 after the round-9 junk guard (0.640 after the round-8 unknown-drug fix, 0.673 before it) | dev · synthetic |
| Speech, rules: dangerous errors, **headline** / matched-drug only (secondary) | **5 of 480** / 1 of 440 (round-11 code). Of the 10 wrong drugs recorded as known drugs, 6 came from an exact wrong word and are not flagged as to identity. Shown apart: fields left "not stated" (e.g. 96 of 420 medication records got no entry at all), see `docs/architecture.md` §6c | dev · synthetic |
| Off-template sentences, rules: entity F1 | 0.952 (59 records) | dev · hand-written |
| End of a 10-second dictation to the confirm screen, p50 / p95 | 0.387 s / 0.422 s | dev · synthetic dictation |
| Seeded dose errors caught / harder ones | 99.0% / 78.0% (circular by construction) | test · validator only |
| Correct doses wrongly flagged | 0.3% test, 1.2% final_test, 1.9% dev | test / dev · validator only |
| PDF note for a 10 / 50-entry incident, p50 | 19.8 ms / 87.4 ms (round 7, logged run `r7-pdf-latency`, 30 timed runs) | synthetic incidents |
| Blind evaluator-authored sentences (32), entity F1 core / stretch, rules | 0.840 / 0.857 as run; 0.892 / 0.857 converter-corrected | blind · single author, sanity check only |
| Full pipeline on test, final_test; real speech | — | sealed |

How it works, per-entity-type scores, the FHIR-lite/PDF example and the full table: `docs/architecture.md`.

## Recording real speech (dev and test)

Real recordings are what the speech numbers need. Two ways to record; both end in `data/real/{dev,test}/` with an
anonymous speaker id, a SHA-256 manifest and the reference text. **Test clips stay sealed**: they can be recorded and
imported, but no tool will transcribe or score them until the evaluator says so (the record page does not transcribe
test takes either).

**A. In the app (recommended).** Start the server (above), open `http://localhost:8000/record` in the Windows browser
and allow the microphone. Each prompt shows a sentence (60 dev, 180 test) and a suggested condition (quiet, fan,
street, siren playback, fast, mumbled). Press record, read the sentence as you would on a call, stop. Dev takes are
checked immediately (the page shows what was heard); test takes are saved sealed — listen back if unsure, and use
"re-record" for a bad take. Then import, using your own anonymous id:

```bash
conda activate anpr
python -m scripts.import_real --from-recordings --speaker S01
```

**B. Any recorder.** Record WAV files (e.g. Windows Voice Recorder or Audacity, any sample rate; they are converted to
16 kHz mono), put them in a folder, and write a tab-separated `refs.tsv` with one line per clip:
`<path to file><TAB><exact sentence that was read>`. From WSL, Windows folders are under `/mnt/c/...`.

```bash
python -m scripts.import_real --split dev --speaker S01 --refs /mnt/c/Users/<you>/recordings/refs.tsv
python -m scripts.import_real --split test --speaker S01 --refs /mnt/c/Users/<you>/recordings/test_refs.tsv
```

Re-importing the same audio does nothing; a clip changed after import is detected. Then compare real dev speech with
the synthetic voices:

```bash
python -m eval.real_wer --tag real-vs-piper --piper results/r4-dev-audio-hybrid-v2
```

## Evaluate

```bash
python -m eval.run --split dev --mode text  --extractor rules --tag my-dev-text
python -m eval.run --split dev --mode audio --extractor rules --tag my-dev-speech
python -m eval.run --split offtemplate_dev --extractor rules --tag my-offtemplate
python -m pytest
```

Every run is logged in `results/run_log.jsonl`. test and final_test are frozen (SHA-256 of the sentences and of every
audio clip in `eval/frozen.sha256`), refused on a dirty working tree, and write aggregates only; final_test is sealed
until the last stage. Decisions and their measured reasons: `DECISIONS.md`. Evidence packets: `results/packets/`.
