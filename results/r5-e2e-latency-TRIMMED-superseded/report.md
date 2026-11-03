# End-to-end latency (`r5-e2e-latency`, commit `0904591`)

30 runs of a 10-second dictation (11.3 s of Piper speech + silence), extractor **rules**, ASR faster-whisper-small.en on NVIDIA GeForce RTX 5060, 621.01. Timed from the moment the upload leaves the client to the parsed confirm-screen payload, through a real HTTP server on localhost.

| p50 | p95 | mean | min | max | ASR part, p50 | warm-up run (model load) |
|---|---|---|---|---|---|---|
| **0.502 s** | **0.542 s** | 0.503 s | 0.4597 s | 0.5865 s | 0.45 s | 2.5834 s |

Not included: the browser's audio encoding and the screen paint. Raw timings: `timings.csv`.
Transcript of the last run: “At 1040 gave adrenaline 0.3 milligrams IM, then ondansetron 4 milligrams IV, aspirin 300 milligrams by mouth, and started at 12 lead ECG.” (4 entries).
