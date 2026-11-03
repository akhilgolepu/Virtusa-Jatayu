# Evidence packet — M1 (skeleton end to end)

Product: **Scribe108** (decision-support demo, not a clinical device). Branch `f2r-evidence`.
Commit: **`9bfa6c3`** for everything in this folder (evaluator round 3, item 9): `commit.txt`, the ten samples,
`verify_before_after_tamper.txt`, `tamper_suite_pytest.txt`, `worst_failures.json` and `pytest_output.txt` were all
rebuilt in one go by `bash scripts/m1_packet.sh` on a clean tree at that commit (each text file names the commit in its
first line). Tag `m1-pass` points at `9bfa6c3`.

## Files

| File | What |
|---|---|
| `commit.txt` | Commit hash for this packet |
| `pytest_output.txt` | Full `python -m pytest -v -rs` output (text) at `9bfa6c3`: **343 passed, 13 xfailed, 0 skipped, 0 failed, nothing deselected** (GPU free, so the model tests ran). The 13 xfails are the known off-template failures, each with its reason (`eval/offtemplate_dev.yaml`) |
| `record.schema.json` | JSON Schema of a record (pydantic, generated from `jatayu/models.py`) |
| `models.py` | The schema source: `entry id`, `kind`, `drug`/`procedure` (normalised `value` + `raw` transcript words), `dose_value`, `dose_unit`, `route`, `time` + `time_source` (spoken / device_clock / user), per-field `span`, `confidence`, `source`, `flags` |
| `fhir_lite.schema.json` | Output bundle schema |
| `sample_01.json` … `sample_10.json` | Ten `python -m f2r.cli add "<sentence>" --extractor rules` outputs (all appended to one incident, so the history checks fire — e.g. sample 02 repeats sample 01's adrenaline and gets `repeat_too_soon`) |
| `verify_before_after_tamper.txt` | `f2r verify` → ok (exit 0); `scripts/tamper.py` changes fentanyl 150 → 1500 mcg in row 5; `f2r verify` → broken at seq 5, "payload hash mismatch" (exit 1) |
| `tamper_suite_pytest.txt` | `pytest -v tests/test_audit_tamper.py` — 14 passed |
| `worst_failures.json` | The M1 five worst typed-text failures (input, output, expected), outputs re-run at `9bfa6c3` — see below |

The ten sample sentences: "gave 0.3 mg adrenaline IM" · "gave point three milligrams of adrenaline IM two mins
ago" · "pushed 4 mg ondansetron IV" · "aspirin 300 mg PO at 10 40" · "fentanyl one hundred and fifty micrograms IV just
now" · "morphine 5 mg IV, pain score 8, no nausea" · "gave aspirin" · "patient allergic to morphine" · "started CPR and
gave adrenaline 1 mg IV" · "ondansetron 4, no sorry, 2 mg IV".

## Tamper types detected (12) and the pinned blind spot

Each is a separate test in `tests/test_audit_tamper.py`; `verify()` must fail **at the right row**:

1. edit a payload field (dose 0.3 → 3.0)
2. edit the transcript hash
3. edit the timestamp
4. edit the event type (draft → confirm)
5. edit the incident id
6. delete a middle row (detected at the next row: "seq gap")
7. edit prev_hash
8. edit the audio hash
9. insert a forged row (self-consistent payload hash, no valid link)
10. reorder two rows
11. swap two entry hashes
12. edit a row and re-hash it consistently (detected at the next row: "broken link")

**Blind spot (pinned by `test_tail_deletion_is_NOT_detectable_by_the_chain_alone`):** deleting the newest rows leaves
a valid, shorter chain. A bare hash chain cannot detect it; it needs server receipts (Stage 3 S3). Claim wording:
"100 % of tested tamper types", never "100 % of tampered entries".

## Five worst failures (typed text, rules extractor), re-run at `9bfa6c3`

These were the five worst typed-text failures at M1. Round 3 fixed three of them so that they are no longer silent;
all five are also in the off-template dev set (`eval/offtemplate_dev.yaml`, `ot-m1-01`…`05`).

| Input | Output now | Expected | Status |
|---|---|---|---|
| morphine 2 to 4 mg IV | morphine 4 mg IV + **`dose_range_stated` (high)** | the range, or a flag | flagged (was silent) |
| ketamine 1 mg per kg IV | ketamine 1 mg IV, `dose_below_range` | 1 mg/kg, recorded as per-kg | open (xfail): per-kg units not modelled |
| adrenaline 1 mg IV, then another 1 mg two minutes later | **two** epinephrine 1 mg entries; the second flagged `repeat_dose_inferred` (route not said → `field_missing`) | two administrations | fixed (was one entry) |
| adrenaline 1 mg IV at 10:40 and amiodarone 300 mg IV | amiodarone 10:40 + **`time_borrowed` (medium)** | amiodarone time not stated (flagged) | flagged (was silent) |
| gave 4 mg ondansetron 10 mg metoclopramide IV | ondansetron 4 mg (route missing, flagged); metoclopramide dose missing (flagged) | ondansetron 4 mg IV; metoclopramide 10 mg IV | open (xfail), flagged |

No row is silent any more. The "2 minutes later" time of the repeat dose is not parsed (`time_not_stated`).

## Changed beyond the brief

- 36 drugs instead of 10; the extractor, validator, LLM/hybrid, UI and PDF already exist (built before this plan).
- `f2r add` appends to a reusable "f2r-cli" incident so the validator's history checks (repeat / duplicate) run.
- Record schema adds `raw` (transcript words) and `time_source`, which the M1 brief lists, plus `source` and
  per-field `confidence`.
- `results/packets/m1/sample.sqlite` is git-ignored (*.sqlite); the verify transcript is in verify_before_after_tamper.txt.
