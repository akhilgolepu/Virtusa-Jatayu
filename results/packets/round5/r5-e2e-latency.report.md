# End-to-end latency (`r5-e2e-latency`, commit `02e6fb0`)

30 runs of a 10-second dictation (8.8 s of Piper speech + silence), extractor **rules**, ASR faster-whisper-small.en on NVIDIA GeForce RTX 5060, 621.01. Timed from the moment the upload leaves the client to the parsed confirm-screen payload, through a real HTTP server on localhost.

| p50 | p95 | mean | min | max | ASR part, p50 | warm-up run (model load) |
|---|---|---|---|---|---|---|
| **0.387 s** | **0.422 s** | 0.387 s | 0.346 s | 0.4264 s | 0.337 s | 2.2079 s |

Not included: the browser's audio encoding and the screen paint. Raw timings: `timings.csv`.
Transcript of the last run: “At 1040 gave adrenaline 0.3 mg IM, vanondensetron 4 mg IV, and aspirin 300 mg by mouth.” (3 entries).
