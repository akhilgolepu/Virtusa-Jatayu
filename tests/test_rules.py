from datetime import datetime, timedelta

from jatayu.extract.rules import RulesExtractor

CAP = datetime(2026, 10, 31, 10, 45).astimezone()


def ext(lexicon, raw):
    return RulesExtractor(lexicon).extract(raw, CAP)


def test_messy_adrenaline(lexicon):
    raw = "gave point three milligrams of adrenaline IM two mins ago"
    [e] = ext(lexicon, raw)
    assert (e.drug.value, e.dose_value.value, e.dose_unit.value, e.route.value) == ("epinephrine", 0.3, "mg", "IM")
    assert e.time.value == CAP - timedelta(minutes=2)
    assert raw[slice(*e.drug.span)] == "adrenaline" and raw[slice(*e.dose_value.span)] == "point three"
    assert e.flags == []


def test_two_drugs_no_borrowing(lexicon):
    raw = "gave aspirin and 4 mg ondansetron IV"
    a, o = ext(lexicon, raw)
    assert a.drug.value == "aspirin" and a.dose_value.value is None
    assert {f.code for f in a.flags} >= {"field_missing"}
    assert (o.drug.value, o.dose_value.value, o.dose_unit.value, o.route.value) == ("ondansetron", 4.0, "mg", "IV")


def test_dose_without_unit_flags_not_guesses(lexicon):
    [e] = ext(lexicon, "gave 0.3 of adrenaline IM")
    assert e.dose_value.value == 0.3 and e.dose_unit.value is None
    assert any(f.code == "field_missing" and f.field == "dose_unit" and f.severity == "high" for f in e.flags)


def test_clock_time_not_taken_as_dose(lexicon):
    [e] = ext(lexicon, "at 10 42 gave 2 mg morphine IV")
    assert e.dose_value.value == 2.0 and (e.time.value.hour, e.time.value.minute) == (10, 42)


def test_self_correction_takes_later_number(lexicon):
    [e] = ext(lexicon, "ondansetron 4, no sorry, 2 mg IV")
    assert e.dose_value.value == 2.0


def test_brand_and_fuzzy(lexicon):
    [e] = ext(lexicon, "Emeset 4 mg IV")
    assert e.drug.value == "ondansetron" and e.drug.confidence == 1.0
    [f] = ext(lexicon, "ondansatron 4 mg IV")
    assert f.drug.value == "ondansetron" and f.drug.confidence < 1.0


def test_procedure_with_detail(lexicon):
    [p] = ext(lexicon, "tubed him with a size 7.5 tube at 10:30")
    assert p.kind == "procedure" and p.procedure.value == "endotracheal intubation"
    assert "7.5" in p.detail.value


def test_no_time_stated_flag(lexicon):
    [e] = ext(lexicon, "aspirin 300 mg PO")
    assert e.time.span is None and e.time.value == CAP
    assert any(f.code == "time_not_stated" for f in e.flags)


def test_every_span_is_valid_raw_slice(lexicon):
    raw = "Adrenaline 1 mg IV push at 10:40 then started CPR, amiodarone 300 mg IV"
    entries = ext(lexicon, raw)
    assert [getattr(e, "drug", None) and e.drug.value or e.procedure.value for e in entries] == ["epinephrine", "cpr", "amiodarone"]
    for e in entries:
        for name in ("drug", "dose_value", "dose_unit", "route", "procedure", "time"):
            f = getattr(e, name, None)
            if f is not None and f.span is not None:
                s, t = f.span
                assert 0 <= s < t <= len(raw)


def test_no_separator_chain_stays_with_its_drug(lexicon):
    a, o = ext(lexicon, "aspirin 300 mg PO ondansetron 4 mg IV")
    assert (a.drug.value, a.dose_value.value, a.route.value) == ("aspirin", 300.0, "PO")
    assert (o.drug.value, o.dose_value.value, o.route.value) == ("ondansetron", 4.0, "IV")


def test_hinglish_filler_ignored(lexicon):
    raw = "adrenaline 0.3 mg IM de diya"
    [e] = ext(lexicon, raw)
    assert (e.drug.value, e.dose_value.value, e.dose_unit.value, e.route.value) == ("epinephrine", 0.3, "mg", "IM")


def test_dangerous_number_forms(lexicon):
    assert ext(lexicon, "adrenaline .5 mg IM")[0].dose_value.value == 0.5
    assert ext(lexicon, "adrenaline point 5 mg IM")[0].dose_value.value == 0.5
    [f] = ext(lexicon, "fentanyl one hundred and fifty micrograms IV")
    assert (f.dose_value.value, f.dose_unit.value) == (150.0, "mcg")
    [s] = ext(lexicon, "normal saline 1,000 ml IV")
    assert (s.dose_value.value, s.dose_unit.value, s.route.value) == (1000.0, "ml", "IV")


def test_correction_marker_must_sit_between_numbers(lexicon):
    assert ext(lexicon, "morphine 5 mg IV, pain score 8, no nausea")[0].dose_value.value == 5.0
    assert ext(lexicon, "morphine 5 mg IV, pain 3 out of 10, no further dose")[0].dose_value.value == 5.0


def test_several_unitless_numbers_flag_the_dose(lexicon):
    [e] = ext(lexicon, "10 42 morphine 2 IV")
    assert e.dose_value.value == 2.0
    assert any(f.field == "dose_value" and f.severity == "high" for f in e.flags)


def test_not_given_contexts_are_flagged(lexicon):
    for raw in ("did not give aspirin 300 mg", "patient allergic to morphine", "patient takes aspirin 75 mg daily"):
        [e] = ext(lexicon, raw)
        assert any(f.code == "possible_not_given" and f.severity == "high" for f in e.flags), raw


def test_measurements_are_flagged_not_silent(lexicon):
    for raw in ("blood glucose 3.2 mmol", "O2 sats 88", "serum magnesium 0.7", "ionised calcium 1.1"):
        [e] = ext(lexicon, raw)
        assert any(f.code == "possible_measurement" and f.severity == "high" for f in e.flags), raw
    [d] = ext(lexicon, "gave dextrose 25 g IV")
    assert not any(f.code == "possible_measurement" for f in d.flags)


def test_ambiguous_procedure_aliases_removed(lexicon):
    assert all(e.kind != "procedure" for e in ext(lexicon, "oxygen 4 litres per minute via nasal cannula"))
    a, c = ext(lexicon, "adrenaline 1 mg IV started compressions")
    assert (a.drug.value, a.route.value) == ("epinephrine", "IV") and c.procedure.value == "cpr"


def test_raw_name_and_time_source(lexicon):
    [e] = ext(lexicon, "gave 0.3 mg Adrenaline IM two mins ago")
    assert (e.drug.raw, e.drug.value) == ("Adrenaline", "epinephrine")
    assert e.time_source == "spoken" and e.model_dump()["time_source"] == "spoken"
    [f] = ext(lexicon, "aspirin 300 mg PO")
    assert f.time_source == "device_clock"


def test_dose_range_is_flagged_not_silently_resolved(lexicon):
    for raw in ("morphine 2 to 4 mg IV", "fentanyl 50-100 mcg IV", "between 2 and 4 mg morphine IV"):
        [e] = ext(lexicon, raw)
        assert any(f.code == "dose_range_stated" and f.severity == "high" for f in e.flags), raw
    [e] = ext(lexicon, "morphine 4 mg IV at 10 20")
    assert not any(f.code == "dose_range_stated" for f in e.flags)


def test_then_another_gives_a_second_flagged_entry(lexicon):
    a, b = ext(lexicon, "morphine 4 mg IV at 10 30 then another 2 mg IV at 10 40")
    assert (a.drug.value, a.dose_value.value) == ("morphine", 4.0) and not any(f.code == "repeat_dose_inferred" for f in a.flags)
    assert (b.drug.value, b.dose_value.value, b.route.value) == ("morphine", 2.0, "IV")
    assert any(f.code == "repeat_dose_inferred" for f in b.flags)


def test_time_from_another_clause_is_flagged(lexicon):
    a, b = ext(lexicon, "at 10 40 aspirin 300 mg PO and ondansetron 4 mg IV")
    assert not any(f.code == "time_borrowed" for f in a.flags)
    assert b.time.value.strftime("%H:%M") == "10:40" and any(f.code == "time_borrowed" for f in b.flags)
