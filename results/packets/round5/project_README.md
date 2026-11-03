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
uvicorn jatayu.api:app --port 8000       # then open http://localhost:8000 in the Windows browser
```

## Extractor: rules by default

Three extractors turn a transcript into records: `rules` (lexicon + patterns), `hybrid` (rules find the spans, a
local Qwen3-4B links them) and `llm` (LLM only, quotes checked against the transcript). **`rules` is the default**
(`JATAYU_EXTRACTOR`, the selector on the capture screen); the other two stay selectable.

Why (measured on dev, evaluator round 4; DECISIONS 2026-11-03):

| Extractor | Speech entity F1 | Off-template F1 | Speech dangerous errors | Speech "not given" recorded as given |
|---|---|---|---|---|
| rules | 0.673 | 0.948 | 1/440 | 4/40 |
| hybrid | 0.673 | 0.950 | 1/440 | 4/40 |
| LLM only | 0.527 | 0.894 | 0/440 | 21/40 |

The LLM added nothing measurable, and costs ~0.6-0.9 s per utterance and 3.35 GB of GPU memory. The LLM remains as an
optional linker and is reported as an ablation.

```bash
JATAYU_EXTRACTOR=hybrid uvicorn jatayu.api:app --port 8000   # to run with the LLM linker instead
```

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
