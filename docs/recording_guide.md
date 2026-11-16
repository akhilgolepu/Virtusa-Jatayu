# Recording guide — three speakers

**Synthetic sentences only:** every sentence is an invented medication or procedure note, with no real patient. The
voices you record are personal data. They stay on this laptop, under an anonymous code, never a name.

## Where the sentences are

- **The list:** 240 sentences, in `data/recordings/prompts.jsonl`. 180 come from the sealed **test** set and 60 from the
  **dev** set; 40 are Hinglish.
- **Printable sheets for three speakers:** `data/recordings/recording_sheets.md`. Rebuild them with
  `python -m scripts.recording_sheets`.
  - The split is balanced: each part has 80 sentences (60 test, 20 dev), 13-14 Hinglish, and every recording condition.
  - The file is git-ignored. **Do not commit, share or post it.** Read the test sentences aloud, but never use them to
    tune anything.
- **The `/record` page** shows each speaker the same sentences in the same order as their sheet.

| Speaker | Code | Part | Page | Sentences |
|---|---|---|---|---|
| Person 1 | S01 | 1 | `http://localhost:8000/record?part=1&parts=3` | 80 |
| Person 2 | S02 | 2 | `http://localhost:8000/record?part=2&parts=3` | 80 |
| Person 3 | S03 | 3 | `http://localhost:8000/record?part=3&parts=3` | 80 |

Keep a private note of which person has which code, off this laptop and out of the repository. The code is the only
thing stored with the audio.

## Before recording

1. Each speaker agrees that their recordings are kept on this laptop to measure speech recognition, under the code
   only.
2. Start the app: `conda activate anpr && export TZ=Asia/Kolkata && ./start_demo.sh`. The browser opens on the Windows
   side. The microphone needs `localhost`, not an IP address.
3. Use the same microphone for all three speakers if you can, and note which one it was.

## Recording (per speaker, about 30 minutes)

1. Open your part's page from the table above. The top line says "Part N of 3".
2. Read the condition shown, and set it up as well as you can:
   - **quiet:** a quiet room;
   - **fan:** a fan or AC running nearby;
   - **street:** outdoors or traffic noise;
   - **siren-playback:** a siren sound playing from a phone;
   - **fast:** speak quickly;
   - **mumbled:** speak less clearly.
3. Read the sentence **exactly as written**, including "uh" or Hindi words. Keys:
   - **Space:** start / stop;
   - **Enter:** next;
   - **R:** re-record.
4. **Dev sentences** get an automatic check after each take. If it shows **review**:
   - you misspoke: press **R** and read it again;
   - you said something different on purpose or by habit: press **E** ("Said it differently") and type exactly what you
     said;
   - you read it right and the recogniser simply misheard: just press **Enter**, and the take is kept.

   **Test sentences** show no check: they are sealed ("Test take saved, sealed"). Listen back if unsure, and press R
   to redo.
5. Tick each sentence on your sheet as you go. You can stop and come back: the page resumes at your first unrecorded
   sentence.

## After each speaker finishes

Import only that speaker's part under their code:

```bash
python -m scripts.import_real --from-recordings --speaker S01 --part 1 --parts 3   # S02 --part 2, S03 --part 3
```

Re-running is harmless; the same audio is never imported twice.

## When all three are imported

```bash
python -m eval.real_wer --tag r13-real-vs-piper --piper results/r11-dev-audio-rules
```

This compares the speech recogniser on the real **dev** takes with the synthetic dev voices: normalised and raw WER and
drug-term recall, overall and per speaker. The real **test** takes stay sealed: `real_wer` refuses them, and they are
scored only once, by `eval/real_test.py`, after the freeze and the evaluator's release. Nothing is tuned on the real
dev numbers until the evaluator has reviewed the report.
