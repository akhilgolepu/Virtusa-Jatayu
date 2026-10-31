from datagen.compose import Composer
from datagen.schema import GoldUtterance

CAP = "2026-10-31T10:45:00+05:30"


def _spans_ok(u: GoldUtterance):
    for e in u.entries:
        for name in ("drug", "procedure", "dose_value", "dose_unit", "route", "detail"):
            f = getattr(e, name)
            if f is not None:
                assert u.text[f.span[0]:f.span[1]] == f.surface, (name, f)
        if e.time.surface is not None:
            assert u.text[e.time.span[0]:e.time.span[1]] == e.time.surface


def test_single_entry_spans_and_roundtrip():
    c = Composer()
    c.add("uh gave ")
    c.new_entry("medication")
    c.field("dose_value", "point three", 0.3)
    c.add(" ")
    c.field("dose_unit", "milligrams", "mg")
    c.add(" of ")
    c.field("drug", "adrenaline", "epinephrine")
    c.add(" ")
    c.field("route", "IM", "IM")
    c.add(", ")
    c.time("relative", surface="two mins ago", offset_s=-120)
    u = c.build(id="x-0-000", family="x", category="med_basic", lang="en", capture_time=CAP)
    assert u.text == "uh gave point three milligrams of adrenaline IM, two mins ago"
    _spans_ok(u)
    assert GoldUtterance.model_validate_json(u.model_dump_json()) == u
    assert u.entries[0].time.offset_s == -120 and u.entries[0].dose_value.value == 0.3


def test_two_entries_keep_separate_fields_and_no_double_spaces():
    c = Composer()
    c.new_entry("medication")
    c.field("drug", "aspirin", "aspirin")
    c.add("  and ")
    c.new_entry("procedure")
    c.field("procedure", "CPR", "cpr")
    c.time("none")
    u = c.build(id="y-0-000", family="y", category="med_multi", lang="en", capture_time=CAP)
    assert "  " not in u.text
    assert [e.kind for e in u.entries] == ["medication", "procedure"]
    assert u.entries[0].procedure is None and u.entries[1].drug is None
    assert u.entries[0].time.kind == "none"
    _spans_ok(u)
