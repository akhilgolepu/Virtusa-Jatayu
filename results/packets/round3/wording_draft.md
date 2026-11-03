# Wording draft — seeded-error results (for README and slides)

Draft text for the README and slides. Every number traces to a file in `results/`; the caveat goes with each number,
not in a footnote.

---

**How often does the dose checker catch a deliberately corrupted dose?**

We take correct records and corrupt one value the way a dictation slip would (×10, ÷10, mg↔mcg, wrong route), then
count how often the checker flags the corrupted record. Four measurements, in the order they were made:

| Step | Catch rate | What it is, and why it is not the headline on its own |
|---|---|---|
| 1. First run, dev | **81.5%** (163/200) | Dev records, first try of the checker. Older data in which some correct doses were themselves outside the cited range (since fixed). Stricter "new flag" definition: 79.5% |
| 2. After tuning, same dev records | **98.5%** (197/200) | The checker was improved **on these same 200 records**, so this shows the tuning worked on what it was tuned on, not how it generalises |
| 3. First test run (fresh records, checker frozen) | **94.5%** (189/200) | Held-out test, checker not changed afterwards. But the test data had the same dose-table bug as step 1 and was regenerated; this run is superseded. Stricter definition: 93.0% (95% CI 88.6-95.8) |
| 4. Regenerated test, new seed, checker frozen | **99.0%** (198/200; 95% CI 96.4-99.7) | Same corruption kinds the checker was written for, on doses drawn from the same table it checks: **circular by construction** (see below). 200 draws with replacement = 173 distinct records, so the interval is somewhat narrow. False flags on the uncorrupted records: 0/200 |

**Harder corruptions** (×2, ×5, a slipped digit, mg→g), regenerated test, checker frozen: **78.0%** (156/200;
95% CI 71.8-83.2). By kind: mg→g 50/50, ×5 44/50, ×2 34/50, digit slip 28/50. Of the 44 misses, 35 got no flag
at all because the corrupted dose is still inside the published range, and 9 got only the informational weight-based
note. A corrupted dose that is still a legal dose cannot be seen by a range check, and that residual risk depends on
read-back confirmation, whose effectiveness we have not measured.

**Why the 99% is not the number to quote alone.** The corruptions are the error kinds the checker's rules were written
for, and the correct doses come from the same lexicon ranges the checker uses, so a high catch rate mostly confirms
that the generator and the checker share one table. A more honest indicator of how the checker treats **correct**
records is how often it flags them: on every correct dose in our synthetic sets it flagged **7 of 359 (1.9%)** on dev,
**1 of 291 (0.3%)** on test and **2 of 168 (1.2%)** on final_test.

All of this is synthetic, template-generated data; nothing here has been measured on real ambulance speech.
Decision-support demo, not a clinical device. Adult patients only.

---

Sources: `results/m3-seeded-dev-seed7-FIRST-RUN-RESCORE/`, `results/m3-seeded-dev-seed7-TUNED-RESCORE/`,
`results/m3-seeded-test-seed2026-FRESH-RESCORE/`, `results/m3-seeded-test-seed2028-FRESH-regenerated/`,
`results/m3-seeded-test-seed2029-HARDER-regenerated/`, `results/m4dev-gold-dose-audit-AFTER-weight-range/`.
