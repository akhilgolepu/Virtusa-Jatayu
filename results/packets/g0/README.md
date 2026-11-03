# Evidence packet — Gate G0 (set-up and de-risk)

Product: **Scribe108** (decision-support demo, not a clinical device). Branch `f2r-evidence`.

| | |
|---|---|
| Milestone | G0 |
| Commit that produced `setup_check.json` | **`9bfa6c3`** = tag `m1-pass` (re-stamped 2026-11-03 for evaluator round 5: run in a clean worktree checked out at the tag, so the JSON's `commit`, this README and the tag agree; earlier runs `5f8e231`, and `760ebd2` = `9bfa6c3` before the message rewrite, see `docs/commit-map.txt`) |
| Packet assembled at | see `git log -1 -- results/packets/g0` |

## Files

| File | What |
|---|---|
| `setup_check.json` | Written by `python -m scripts.setup_check` (also `python -m f2r.cli setup-check`). **all_pass: true** — gpu, asr, llm, tts, offline. Records `commit` and a `cuda` block (round 3) |
| `nvidia-smi.txt` | Full `nvidia-smi` + query, captured right after the round-5 re-stamp (GPU otherwise idle) |
| `requirements.lock` | 86 pinned packages (dependency walk from requirements.txt; `python -m scripts.make_lock`) |
| `DECISIONS.md` | Full decisions log. Speech backend + language model entries with measured latencies are the rows dated 2026-10-31 (faster-whisper small.en on cuda int8_float16) and 2026-11-01 (Qwen3-4B-Instruct-2507 Q4_K_M via llama.cpp CUDA 13.0 sm_120; both models resident) |

## Measured numbers (all from `setup_check.json`, commit `9bfa6c3`, 2026-11-03)

- GPU: RTX 5060, driver 621.01, torch CUDA available.
- CUDA (round 3): driver supports CUDA **13.5** (nvidia-smi "CUDA UMD Version"; round 1 recorded "unknown" because the
  parser looked for "CUDA Version:"). Runtimes actually loaded: torch **13.0**; llama-cpp-python 0.3.36 on the
  nvidia-cuda-runtime **13.0.96** wheel; CTranslate2 4.8.4 on cuBLAS **12.9.3.13** (CUDA 12, side by side); 1 CUDA device.
- ASR: faster-whisper `small.en`, **device cuda**, warm latency **0.243 s** for a 3.8 s clip (median of 3).
- LLM: Qwen3-4B-Instruct-2507 Q4_K_M, constrained JSON extraction, **30.3 tokens/s**, peak VRAM **5,899 MiB**
  (includes the Windows desktop's share of the 8 GB card).
- TTS: Piper `en_US-lessac-medium`, read-back synthesised.
- Offline (round 3): ASR, **the LLM smoke test** and TTS re-run with every outbound socket blocked (all three pass,
  LLM returned 3 entries); a test connection to 1.1.1.1 was refused.

## TODO — waiting on the human

- [ ] **Real-sentence WER**: record 10 sentences naming drugs (the plan's accuracy smoke test), compute WER with jiwer.
      Not done: no real recordings exist yet.
- [ ] **Real Wi-Fi-off run**: repeat the smoke tests with the laptop's network physically off. Only the
      socket-blocked equivalent has been run.

## Five worst failures

No G0 check fails now. These are the five worst failures met on the way, each still pinned by a test or a decision:

| # | Input | Output | Expected | Resolution |
|---|---|---|---|---|
| 1 | faster-whisper on `device="cuda"` (CTranslate2 4.8.4) | `RuntimeError: Library libcublas.so.12 is not found` | GPU transcription | CUDA 12 cuBLAS installed side by side and preloaded in `jatayu/asr.py` (DECISIONS 2026-10-31) |
| 2 | Any audio decode with PyAV 19.0.2 | `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | decoded 16 kHz samples | PyAV pinned to 18.1.0 |
| 3 | Fixture "…adrenaline I M two minutes ago" | Whisper: "…adrenaline **I am** 2 minutes ago" | "…adrenaline IM…" | route codes added to the vocabulary prompt; "I am" deliberately not an alias |
| 4 | Qwen3-4B, default chat template, JSON schema | `{"dose": "0.3 mg', "}` and the second drug dropped | well-formed quotes, both drugs | `chat_format="chatml"` (test_llm_quotes_cleanly_with_chatml) |
| 5 | llama-cpp-python prebuilt wheels on sm_120 | no Blackwell build available | GPU offload | built from source with CUDA 13.0 in a separate build-only env (DECISIONS 2026-11-01) |

## Changed beyond the brief

- The project was built before this plan existed: package `jatayu/`, not `src/f2r/`; an `f2r` CLI wraps it
  (DECISIONS). Lexicon is YAML in the package, not `data/lexicon.json`.
- Whisper and Qwen are kept resident together (the plan assumed they could not be); measured 7.3 of 8.1 GB.
- `requirements.lock` lists our dependency tree, not a full `pip freeze` (the env holds unrelated packages).
