# Scribe108 — 5-minute demo script

**Decision-support demo, not a clinical device. Synthetic content only.** Every sentence below is invented. No real
patient and no real recording are used. The incident is labelled "Demo — synthetic patient".

What each sentence produces was checked through the app's typed path on 2026-11-16, at the round-11 code. Spoken
input goes through the speech recogniser first, so a word can be misheard. When that happens, show the flag: that is
the point of the app.

## Before the audience arrives (about 10 minutes before)

| # | Do | Check |
|---|---|---|
| P1 | Laptop on mains power. Close other GPU apps. | — |
| P2 | **Turn Wi-Fi off** (Windows quick settings) and unplug any network cable. | Taskbar shows no network. |
| P3 | In WSL: `cd ~/VirtusaJatayu && export TZ=Asia/Kolkata && ./start_demo.sh` (WSL's clock is UTC; spoken times are read against the device clock). | Every pre-flight line says **PASS**, then "Demo running at http://localhost:8000". The browser opens. |
| P4 | In the browser, allow the microphone once (Record, then stop at once). Set the speaker volume so the read-back is audible. | The header shows "offline · asr cuda". |
| P5 | Open the backup video `docs/demo/demo_typed_flow.webm` on a **second device** (phone or USB stick), paused at 0:00. | It plays. |
| P6 | Leave the terminal with the PASS lines open in a second window. | — |

## The demo (5:00)

| Time | Step | Say into the microphone (press **Space** or **● Record**, speak, press again) | What appears | Point to make |
|---|---|---|---|---|
| 0:00–0:30 | **Offline** | — | The taskbar with Wi-Fi off; the terminal's PASS lines (`offline … sockets blocked`); the header "offline · asr cuda". | "Everything runs on this laptop: speech recognition on its GPU, no network." |
| 0:30–0:45 | New incident | — | Type "Demo — synthetic patient" in the incident box, then click **New incident**. | One incident = one patient contact. |
| 0:45–1:25 | 1. A dose given | "Gave point three milligrams adrenaline IM two minutes ago." | Card **EPINEPHRINE**, heard "adrenaline"; dose 0.3, unit "mg · milligrams", route IM, time two minutes ago; no checks. | The drug is the biggest thing on the card, and the heard word stays visible. Click **▶ Read back**: "Drug: Epinephrine." is said first and slowly. Click **Confirm**. |
| 1:25–2:05 | 2. Not given | "Patient is allergic to morphine." | Card **MORPHINE**, 2 checks: *possible not given* and *field missing* (no dose). | Click **Confirm**: the dialog makes you tick both. The record stays **NOT GIVEN** (FHIR `not-done`), never an administration. |
| 2:05–2:35 | 3. A correction | "Ondansetron eight, no sorry, four milligrams IV." | Card **ONDANSETRON** 4 mg IV, with the note *self correction* ("8 -> 4"). | The later value is used, and the correction is shown, not hidden. |
| 2:35–3:20 | 4. A dangerous dose | "Gave ten milligrams adrenaline IM just now." | Card **EPINEPHRINE** 10 mg IM, 2 checks: *dose out of range* (with the cited source) and *repeat too soon*. | Click **▶ Read back**: the warnings are spoken. Click **Reject**. Nothing is fixed silently; the medic decides. |
| 3:20–3:50 | 5. Unknown drug | "Gave diclofenac seventy five milligrams IM." | Card **DICLOFENAC** 75 mg IM, check *drug not in lexicon*. | A drug the list doesn't know is kept as spoken, never dropped, and it can't be range-checked. |
| 3:50–4:05 | 6. A procedure | "Started CPR at ten forty." | Card **CPR**, time 10:40. | Procedures are recorded the same way. |
| 4:05–4:40 | Record | — | Click **PDF note ↗**: the entries, NOT GIVEN for morphine, the record history and "Chain verified". Then **Audit**, **Verify chain**: "chain verified". | The PDF is drawn from the same FHIR-lite JSON (**Incidents**, **FHIR-lite JSON**). Every step is in a hash-chained log. |
| 4:40–5:00 | Close | — | — | "A decision-support demo, not a clinical device. The numbers so far are on synthetic dev data; real recordings come next." |

If time runs short, drop step 6, then step 3. Never drop steps 2 and 4: they show the safety behaviour.

## Fallbacks

| Failure | What to do | What still works |
|---|---|---|
| **Microphone fails** (no permission, no input, garbled) | **Typed path.** Type the same sentence into "Or type: …" and click **Send**. Use number words or digits ("gave 0.3 mg adrenaline IM two minutes ago"). | Everything after speech: extraction, checks, read-back, confirm, PDF, audit. |
| **GPU or model fails** (pre-flight FAIL on `gpu` or `asr`, or a 400/503 on an utterance) | **Rules only, speech on the CPU:** `JATAYU_ASR_DEVICE=cpu JATAYU_ASR_COMPUTE=int8 uvicorn jatayu.api:app --host 127.0.0.1 --port 8000`. This bypasses the pre-flight, which refuses a CPU recogniser by design; say so. Measured on this laptop: about 1.5 s for a 4-second clip on the CPU, about 2 s for the first one. If the recogniser fails entirely, use the typed path. | Extraction is the rules NER (the default), which needs no GPU and no LLM. If only the LLM fails, nothing in this script changes: it uses rules. |
| **Screen or projector fails** | Play the backup video `docs/demo/demo_typed_flow.webm` (42 s, typed path, no sound) from the second device, and narrate the table above over it. | The same six sentences, both confirmations, the reject, the audit check. |
| **Wi-Fi cannot be switched off** (locked settings) | Airplane mode, or unplug the network cable. If neither is possible, say so and show the pre-flight's `offline` line: Whisper and the voice ran with outbound sockets blocked. | The app makes no outside request: the page has no external URLs (`tests/test_api.py`), and models load from disk. |
| **Read-back silent** | Check the volume. Otherwise open `/api/incidents/<id>/entries/<entry id>/readback.txt` and read it aloud. | — |
| **A word is misheard** (e.g. a drug) | Point at the heard word next to the recorded drug and the flag on it. Reject, then say it again or type it. | This is the designed behaviour. |
| **Wrong incident shown** | Pick "Demo — synthetic patient" in the incident box. | — |

## After the demo

Leave the demo database as it is: it is the audit trail of the demo. Turn Wi-Fi back on only after closing the
browser tab.

## Notes for the presenter

- **The video:** the backup video was recorded automatically with Playwright from the typed path
  (`web/e2e/demo_video.mjs`), against a throwaway server with its own temporary database.
- **Better backup:** record one full rehearsal of this script with sound (Windows: Win+Alt+R), and keep it next to
  the typed-path video.
- **Don't claim:**
  - that the drug-first screen or read-back catches a misheard drug;
  - any accuracy on real speech.
