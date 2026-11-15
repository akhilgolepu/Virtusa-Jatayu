# PDF note generation time (`r7-pdf-latency`, commit `cb1de5e`)

GET note.pdf through the API in-process (bundle build + schema validation + audit-chain verify + render), 30 timed runs after one warm-up. Synthetic incidents. Raw: `timings.csv`.

| Entries | p50 | p95 | max | PDF size |
|---|---|---|---|---|
| 10 | 19.8 ms | 28.6 ms | 37.2 ms | 4.1 KB |
| 50 | 87.4 ms | 111.3 ms | 111.5 ms | 11.6 KB |
