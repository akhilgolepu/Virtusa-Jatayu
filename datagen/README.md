# datagen — synthetic EMS utterances, speech and noise

Everything here is seeded and reproducible. Outputs go to `data/` (git-ignored); only code and the
template/dose YAML are committed.

## Rebuild from scratch (offline once models/ESC-50 are downloaded)

```bash
conda activate anpr
python -m datagen.build --seed 1234                 # text + gold, splits, frozen test, STATS.md, review sheet
python -m datagen.render --noise                    # Piper speech for every split + noisy dev/test (20/10/5 dB)
python -m datagen.prompts                           # 240 recording prompts for /record
```

`datagen.build` refuses to overwrite a frozen test split; `--refreeze` regenerates it and invalidates every
result measured on the old one.

## What gets built

| Path | Content |
|---|---|
| `data/synth/{train,dev}.jsonl` | `GoldUtterance` per line (schema: `datagen/schema.py`) |
| `data/test/test.jsonl` + `FROZEN.json` | the test split and its sha256; `load_split("test")` needs `final=True` |
| `data/synth/STATS.md` | counts per split / category / drug / language / anomaly |
| `data/review/sample50.md` | 50-utterance spot-check sheet for a human |
| `data/audio/tts/<split>/` + `<split>.jsonl` | 16 kHz mono WAV per (utterance, voice) + manifest |
| `data/audio/noisy/<split>/<snr>/` + `<split>.jsonl` | dev/test clips with ESC-50 noise at 20, 10, 5 dB |
| `data/recordings/prompts.jsonl` | sentences Akhil reads at `/record` (180 test, 60 dev, 40 Hinglish) |
| `data/recordings/audio/`, `manifest.jsonl` | real takes (never overwritten) and their append-only log |

## Design rules

- **Gold is correct by construction**: spans are recorded as each surface is appended (`compose.py`), and every
  surface comes from the same lexicon/number forms the extractor understands (tested on every utterance).
- **Splits are by template family** (60 families, 142 paraphrase patterns), stratified by category, so test
  phrasings never appear in training.
- **Contexts**: `not_given` (allergy, refused, home medication) and `measurement` (blood glucose, O2 sats)
  entries must be *flagged* by the extractor, not recorded as administrations.
- **Anomalies**: 5% of given doses are deliberately implausible (`10x`, mg↔mcg swap) to measure the validator.
- **Voices**: 14 Piper voice/speakers — US, GB, and 7 Indian-accented English speakers (L2-ARCTIC Hindi-L1
  ASI/RRBI/SVBI/TNI, VCTK p248/p251/p376). Test utterances get 3 voices, at least 2 Indian-accented. The Hindi
  Piper voices were dropped: 81-87% WER reading romanised Hinglish (threshold 60%).
- **Noise**: ESC-50 siren, engine, car_horn, train, helicopter, rain, wind, crying_baby, coughing, breathing;
  folds 1-3 train, 4 dev, 5 test — no noise clip is shared across splits.
- `doses.yaml` values are for generating text only. They are **not** clinical ranges; the validator's ranges
  come from the NASEMSO National Model EMS Clinical Guidelines. Decision-support demo, not a clinical device.
