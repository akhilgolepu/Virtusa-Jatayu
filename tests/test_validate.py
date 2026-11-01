from datetime import datetime, timedelta

from jatayu.models import Field, Flag, MedicationEntry
from jatayu.validate import validate, validate_all

T0 = datetime(2026, 11, 1, 10, 0).astimezone()


def med(drug, dose, unit, route, t=T0, flags=()):
    f = lambda v: Field(value=v, span=None, confidence=1.0, source="rules")  # noqa: E731
    return MedicationEntry(drug=f(drug), dose_value=f(dose), dose_unit=f(unit), route=f(route), time=f(t),
                           flags=list(flags))


def codes(flags):
    return sorted(f.code for f in flags)


def test_in_range_no_flags(lexicon):
    assert validate(med("epinephrine", 0.3, "mg", "IM"), lexicon) == []


def test_above_range_is_high(lexicon):
    [f] = validate(med("epinephrine", 3, "mg", "IM"), lexicon)
    assert (f.code, f.severity, f.field) == ("dose_out_of_range", "high", "dose_value")
    assert "p.67" in f.message or "p.192" in f.message  # cites the guideline page


def test_exact_unit_conversion_is_not_an_error(lexicon):
    assert validate(med("epinephrine", 300, "mcg", "IM"), lexicon) == []


def test_mg_mcg_confusion(lexicon):
    assert "possible_mg_mcg_confusion" in codes(validate(med("epinephrine", 0.3, "mcg", "IM"), lexicon))
    assert "possible_mg_mcg_confusion" in codes(validate(med("epinephrine", 300, "mg", "IM"), lexicon))


def test_route_and_unit_not_allowed(lexicon):
    assert "route_not_allowed" in codes(validate(med("aspirin", 300, "mg", "IV"), lexicon))
    assert "unit_not_allowed" in codes(validate(med("aspirin", 300, "puffs", "PO"), lexicon))


def test_below_range_is_medium(lexicon):
    [f] = validate(med("aspirin", 75, "mg", "PO"), lexicon)
    assert (f.code, f.severity) == ("dose_below_range", "medium")


def test_uncapped_weight_based_dose(lexicon):
    assert codes(validate(med("ketamine", 150, "mg", "IV"), lexicon)) == ["weight_based_dose"]
    assert "dose_out_of_range" in codes(validate(med("ketamine", 1000, "mg", "IV"), lexicon))  # implies >200 kg


def test_no_cited_range_checks_route_and_unit_only(lexicon):
    assert codes(validate(med("atropine", 1, "mg", "IO"), lexicon)) == ["no_reference_range"]


def test_repeat_too_soon_and_duplicate(lexicon):
    first = med("epinephrine", 0.5, "mg", "IM", T0)
    second = med("epinephrine", 0.5, "mg", "IM", T0 + timedelta(minutes=2))
    got = codes(validate(second, lexicon, history=[first]))
    assert "repeat_too_soon" in got and "duplicate_dose" in got
    later = med("epinephrine", 0.3, "mg", "IM", T0 + timedelta(minutes=6))
    assert "repeat_too_soon" not in codes(validate(later, lexicon, history=[first]))


def test_measurement_entries_are_not_range_checked(lexicon):
    ctx = Flag(code="possible_measurement", field="drug", severity="high", message="x")
    assert validate(med("aspirin", 3000, "mg", "PO", flags=[ctx]), lexicon) == []


def test_validate_never_mutates_and_validate_all_merges_without_duplicates(lexicon):
    e = med("epinephrine", 3, "mg", "IM")
    snapshot = e.model_dump()
    validate(e, lexicon)
    assert e.model_dump() == snapshot
    once = validate_all([e], lexicon, history=[])[0]
    twice = validate_all([once], lexicon, history=[])[0]
    assert codes(twice.flags) == codes(once.flags) == ["dose_out_of_range"]
    assert e.flags == []


def test_no_route_is_still_range_checked(lexicon):
    f = lambda v: Field(value=v, span=None, confidence=1.0, source="rules")  # noqa: E731
    e = MedicationEntry(drug=f("morphine"), dose_value=f(100), dose_unit=f("mg"), route=Field.missing("rules"), time=f(T0))
    assert "dose_out_of_range" in codes(validate(e, lexicon))
    ok = MedicationEntry(drug=f("morphine"), dose_value=f(5), dose_unit=f("mg"), route=Field.missing("rules"), time=f(T0))
    assert "dose_out_of_range" not in codes(validate(ok, lexicon))


def test_not_given_entries_are_still_range_checked_measurements_are_not(lexicon):
    ng = Flag(code="possible_not_given", field="drug", severity="high", message="x")
    assert "dose_out_of_range" in codes(validate(med("morphine", 100, "mg", "IV", flags=[ng]), lexicon))
    meas = Flag(code="possible_measurement", field="drug", severity="high", message="x")
    assert validate(med("dextrose", 3.2, "mmol", "IV", flags=[meas]), lexicon) == []


def test_unchecked_dose_is_marked_not_silent(lexicon):
    for args in [("atropine", 10, "mg", "IO"), ("epinephrine", 10, "ml", "IV"), ("naloxone", 40, "mg", "SC")]:
        assert "no_reference_range" in codes(validate(med(*args), lexicon)), args


def test_decimal_slip_floor_on_open_ended_rows(lexicon):
    assert "dose_below_range" in codes(validate(med("diphenhydramine", 2.5, "mg", "IV"), lexicon))
    assert validate(med("fentanyl", 25, "mcg", "IV"), lexicon) == []          # small titrated dose still fine
    assert validate(med("morphine", 2, "mg", "IV"), lexicon) == []


def test_illustrative_ranges_are_used_and_labelled(lexicon):
    [f] = validate(med("furosemide", 400, "mg", "IV"), lexicon)
    assert f.code == "dose_out_of_range" and "ILLUSTRATIVE" in f.message
    assert validate(med("oxygen", 4, "L/min", "INH"), lexicon) == []
    assert any(r.illustrative for r in lexicon.dose_ranges("oxygen", "INH"))
    assert "dose_out_of_range" in codes(validate(med("sodium bicarbonate", 500, "mmol", "IV"), lexicon))
