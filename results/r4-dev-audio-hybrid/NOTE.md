# NOTE — BEFORE the correction-pick fix
Run at `212d5e3`. It exposed two bugs in the round-4 self-correction change (the correction took the clause's last
number, "800, sorry, 1000 mg ... 10 men ago" -> 10; the hybrid dropped a missing-unit flag). Fixed in `4b95fa2`;
the run after the fix is `results/r4-dev-audio-hybrid-v2/`. Kept as evidence.
