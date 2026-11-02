Evaluator round 2: run once on the REGENERATED dev split (gold doses from the lexicon's ranges), validator frozen at
2cbb9a7, harness at cb16546. Strict (headline) and lenient dangerous-error rows are both in metrics.json/report.md.
Commit stamp "cb16546-dirty": the batch wrapper appended a header line to the tracked results/m3-dev-evals.log just
before the first run started; no code differed from cb16546.
Hybrid LLM-failure fallbacks to rules (per results/m3-dev-evals.log): 5 of 480 noisy clips.
