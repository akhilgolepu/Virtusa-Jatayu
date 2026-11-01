"""Validator: checks an entry against the cited dose table and the incident history. It only adds flags;
it never changes a value (a doubtful dose is shown to the medic, never silently fixed)."""
from __future__ import annotations

from collections.abc import Sequence

from jatayu.lexicon import DoseRange, Lexicon
from jatayu.models import Entry, Flag, MedicationEntry

DUPLICATE_WINDOW_S = 120
MAX_PLAUSIBLE_WEIGHT_KG = 200  # an uncapped mg/kg dose implying a heavier patient is treated as out of range
CONTEXT_CODES = {"possible_not_given", "possible_measurement"}
VALIDATOR_CODES = {"no_reference_range", "dose_out_of_range", "dose_below_range", "possible_mg_mcg_confusion", "unit_not_allowed",
                   "route_not_allowed", "duplicate_dose", "repeat_too_soon", "weight_based_dose"}
TO_MG = {"mcg": 0.001, "mg": 1.0, "g": 1000.0}  # exact equivalences, not errors


def _convert(value: float, unit: str, target: str) -> float | None:
    if unit == target:
        return value
    if unit in TO_MG and target in TO_MG:
        return value * TO_MG[unit] / TO_MG[target]
    return None


def _fits(value: float, r: DoseRange) -> bool:
    return (r.min is None or value >= r.min) and (r.max is None or value <= r.max)


def _cite(rows: list[DoseRange]) -> str:
    sources = sorted({r.source for r in rows if not r.secondary}) or sorted({r.source for r in rows})
    return "; ".join(sources[:2])


def _no_reference(e: MedicationEntry, why: str) -> list[Flag]:
    return [Flag(code="no_reference_range", field="dose_value", severity="medium",
                 message=f"{e.dose_value.value:g} {e.dose_unit.value} {e.drug.value} was not range-checked: {why}.")]


def _range_flags(e: MedicationEntry, lexicon: Lexicon) -> list[Flag]:
    value, unit = e.dose_value.value, e.dose_unit.value
    if value is None or unit is None:
        return []
    # No route spoken: compare against every route the drug has a cited range for, so an unspoken route can
    # never hide a 10x dose ("gave 100 mg morphine").
    info = lexicon.drug(e.drug.value)
    rows = lexicon.dose_ranges(e.drug.value, e.route.value) if e.route.value else list(info.dose_ranges)
    if not rows:
        return _no_reference(e, f"no published adult range for {e.route.value or 'any route'}")
    # Express the dose in each row's unit by exact conversion (300 mcg == 0.3 mg is not an error).
    comparable = [(r, v) for r in rows if (v := _convert(value, unit, r.unit)) is not None]
    if not comparable:
        return _no_reference(e, f"the cited ranges are not in {unit}")
    checkable = [(r, v) for r, v in comparable if not (r.max is None and r.per_kg is not None)]
    # Order matters: a real dose band (stated min and max) first, then a x1000 slip into a band, and only then
    # an open-ended "up to N" row — otherwise 0.3 mcg of adrenaline "fits" "up to 0.3 mg" and passes silently.
    bands = [(r, v) for r, v in checkable if r.min is not None and r.max is not None]
    if any(_fits(v, r) for r, v in bands):
        return []
    for factor in (1000.0, 0.001):
        if any(_fits(v * factor, r) for r, v in bands):
            return [Flag(code="possible_mg_mcg_confusion", field="dose_unit", severity="high",
                         message=f"{value:g} {unit} is outside the range but would fit if mg and mcg were swapped. "
                                 f"Source: {_cite([r for r, _ in bands])}.")]
    if any(_fits(v, r) for r, v in checkable):
        return []
    uncapped = [(r, v) for r, v in comparable if r.max is None and r.per_kg is not None]
    if uncapped and any(v / r.per_kg <= MAX_PLAUSIBLE_WEIGHT_KG for r, v in uncapped):
        r = uncapped[0][0]
        return [Flag(code="weight_based_dose", field="dose_value", severity="low",
                     message=f"Weight-based dose ({r.per_kg:g} {r.unit}/kg, no adult cap) — check against weight. "
                             f"Source: {r.source}.")]
    if not checkable:
        checkable = comparable
    rows_only = [r for r, _ in checkable]
    if all(r.min is not None and v < r.min for r, v in checkable):
        return [Flag(code="dose_below_range", field="dose_value", severity="medium",
                     message=f"{value:g} {unit} is below the published adult dose. Source: {_cite(rows_only)}.")]
    return [Flag(code="dose_out_of_range", field="dose_value", severity="high",
                 message=f"{value:g} {unit} is outside the published adult dose range. Source: {_cite(rows_only)}.")]


def _history_flags(e: MedicationEntry, lexicon: Lexicon, history: Sequence[Entry]) -> list[Flag]:
    out = []
    min_repeat = lexicon.min_repeat_s(e.drug.value, e.route.value) if e.route.value else None
    for h in history:
        if not isinstance(h, MedicationEntry) or h.id == e.id or h.drug.value != e.drug.value:
            continue
        if any(f.code in CONTEXT_CODES for f in h.flags):
            continue
        gap = abs((e.time.value - h.time.value).total_seconds())
        same = (h.dose_value.value, h.dose_unit.value, h.route.value) == (e.dose_value.value, e.dose_unit.value,
                                                                        e.route.value)
        if same and gap <= DUPLICATE_WINDOW_S and not any(f.code == "duplicate_dose" for f in out):
            out.append(Flag(code="duplicate_dose", field="drug", severity="medium",
                            message=f"Same {e.drug.value} dose recorded {gap:.0f} s apart — possibly the same dose twice."))
        if min_repeat and gap < min_repeat and h.route.value == e.route.value \
                and not any(f.code == "repeat_too_soon" for f in out):
            out.append(Flag(code="repeat_too_soon", field="time", severity="high",
                            message=f"{e.drug.value} repeated after {gap:.0f} s; the published minimum interval "
                                    f"is {min_repeat} s."))
    return out


def validate(entry: Entry, lexicon: Lexicon, history: Sequence[Entry] = ()) -> list[Flag]:
    if not isinstance(entry, MedicationEntry) or entry.drug.value is None:
        return []
    if any(f.code == "possible_measurement" for f in entry.flags):
        return []  # a reading (blood glucose, sats), not a dose: nothing to range-check
    # possible_not_given entries ARE range-checked: if the medic acknowledges "it was given", the dose must
    # already have been judged.
    info = lexicon.drug(entry.drug.value)
    flags = []
    if entry.dose_unit.value is not None and entry.dose_unit.value not in info.units:
        flags.append(Flag(code="unit_not_allowed", field="dose_unit", severity="high",
                          message=f"{entry.dose_unit.value} is not a unit {entry.drug.value} is given in."))
    if entry.route.value is not None and entry.route.value not in info.routes:
        flags.append(Flag(code="route_not_allowed", field="route", severity="high",
                          message=f"{entry.route.value} is not a route {entry.drug.value} is given by."))
    if not flags:
        flags += _range_flags(entry, lexicon)
    return flags + _history_flags(entry, lexicon, history)


def validate_all(entries: list[Entry], lexicon: Lexicon, history: Sequence[Entry] = ()) -> list[Entry]:
    """Copies of `entries` with validator flags refreshed. Earlier entries in the same utterance count as history."""
    out: list[Entry] = []
    for e in entries:
        kept = [f for f in e.flags if f.code not in VALIDATOR_CODES]
        new = validate(e.model_copy(update={"flags": kept}), lexicon, [*history, *out])
        out.append(e.model_copy(update={"flags": kept + new}))
    return out
