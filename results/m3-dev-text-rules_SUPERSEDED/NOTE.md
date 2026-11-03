# SUPERSEDED

Split: **dev** (verified in metrics.json). Superseded because it ran **before** the measurement-scoring fix (commit ac339c6, spec §13: a reading such as "magnesium level 0.6" is not a dose). The old harness stamped the commit at the END of the run, so a folder stamped ac339c6 may still have loaded the pre-fix code (true for m3-dev-text-hybrid). It also predates: no_reference_range excluded from catching flags, source labels, commit_at_start. Replaced by the rerun with the same tag (no suffix).
