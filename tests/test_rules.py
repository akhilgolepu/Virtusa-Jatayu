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
