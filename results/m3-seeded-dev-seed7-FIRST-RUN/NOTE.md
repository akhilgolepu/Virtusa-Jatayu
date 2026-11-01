# Seeded-error test — FIRST RUN (before any validator change)

163/200 flagged (81.5 %), false flags 19/200 · split **dev** · seed 7.

The original first-run folder was overwritten by the tuned run. This folder is an exact, deterministic
reproduction: the seeded-error script as committed in 1d28b10 (`git show 1d28b10:eval/seeded_errors.py`) run on a
git worktree at **d05ea05** — the validator and dose table as they were *before* the decimal-slip floor and the
illustrative ranges — against the same frozen dev split and seed. Same records, same corruptions, same result as
the original run (163/200).

Misses were: drugs with no cited range (dose x10) and dose /10 under open-ended "up to N" rows. The validator was
then changed **using this same set** — see `m3-seeded-dev-seed7-TUNED`.
