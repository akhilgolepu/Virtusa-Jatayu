import pytest

from datagen.doses import dose_specs, in_cited_range
from datagen.generate import generate
from jatayu.lexicon import Lexicon
from jatayu.normalise.text import normalise

FIELDS = ("drug", "procedure", "dose_value", "dose_unit", "route", "detail")


@pytest.fixture(scope="module")
def utts():
    return generate(seed=1234, per_pattern=6)


def test_deterministic(utts):
    again = generate(seed=1234, per_pattern=6)
    assert [u.model_dump_json() for u in utts] == [u.model_dump_json() for u in again]
    assert generate(seed=99, per_pattern=6)[0].model_dump_json() != utts[0].model_dump_json() or \
        [u.text for u in generate(seed=99, per_pattern=6)] != [u.text for u in utts]


def test_all_spans_match_surface(utts):
    for u in utts:
        for e in u.entries:
            for name in FIELDS:
                f = getattr(e, name)
                if f is not None:
                    assert u.text[f.span[0]:f.span[1]] == f.surface, (u.id, name, u.text)
            if e.time.surface is not None:
                assert u.text[e.time.span[0]:e.time.span[1]] == e.time.surface, (u.id, u.text)


def test_gold_reachable(utts):
    lex = Lexicon.load()
    for u in utts:
        for e in u.entries:
            if e.dose_value is not None:
                nums = [t.value for t in normalise(e.dose_value.surface).tokens if t.kind == "number"]
                assert nums == [e.dose_value.value], (u.id, e.dose_value)
            if e.drug is not None:
                assert lex.lookup_drug(e.drug.surface) == e.drug.value, (u.id, e.drug)
            if e.procedure is not None:
                assert lex.lookup_procedure(e.procedure.surface) == e.procedure.value, (u.id, e.procedure)
            if e.dose_unit is not None:
                assert lex.canonical_unit(e.dose_unit.surface) == e.dose_unit.value, (u.id, e.dose_unit)
            if e.route is not None:
                assert lex.canonical_route(e.route.surface) == e.route.value, (u.id, e.route)


def test_coverage(utts):
    drugs = {e.drug.value for u in utts for e in u.entries if e.drug}
    procs = {e.procedure.value for u in utts for e in u.entries if e.procedure}
    cats = {u.category for u in utts}
    patterns = {u.id.rsplit("-", 1)[0] for u in utts}
    families = {u.family for u in utts}
    assert len(drugs) >= 30 and len(procs) >= 12 and len(cats) == 10
    assert len(families) == 73 and 160 <= len(patterns) <= 175
    assert {u.lang for u in utts} == {"en", "hinglish"}


def test_anomaly_rate():
    utts = generate(seed=1234, per_pattern=20)
    given = [e for u in utts for e in u.entries if e.kind == "medication" and e.context == "given" and e.dose_value]
    rate = sum(e.anomaly is not None for e in given) / len(given)
    assert 0.03 <= rate <= 0.08, rate


def test_dose_specs_come_from_the_lexicon():
    lex = Lexicon.load()
    for drug in lex.drug_names():
        specs = dose_specs(lex, drug)
        assert specs, drug
        for s in specs:
            assert s["route"] in lex.drug(drug).routes and s["unit"] in lex.drug(drug).units, (drug, s)
            assert all(in_cited_range(lex, drug, s["route"], s["unit"], v) for v in s["values"]), (drug, s)


def test_every_gold_dose_is_inside_its_cited_range():
    """One source of truth: every generated gold dose lies inside the lexicon range for its drug (and route, when one
    is spoken), except entries deliberately labelled out_of_range_case, which must lie outside it."""
    lex = Lexicon.load()
    checked = 0
    for u in generate(seed=1234, per_pattern=20):
        for e in u.entries:
            if e.kind != "medication" or e.dose_value is None or e.context == "measurement":
                continue
            unit = e.dose_unit.value if e.dose_unit else None
            if unit is None:
                continue
            route = e.route.value if e.route else None
            inside = in_cited_range(lex, e.drug.value, route, unit, e.dose_value.value)
            if e.anomaly:
                assert "out_of_range_case" in u.tags and not inside, (u.id, e.drug.value, e.dose_value.value)
            else:
                assert inside, (u.id, e.drug.value, e.dose_value.value, unit, route)
            checked += 1
    assert checked > 2000


def test_illustrative_rows_only_where_no_cited_row_exists():
    lex = Lexicon.load()
    for drug in lex.drug_names():
        for s in dose_specs(lex, drug):
            rows = lex.dose_ranges(drug, s["route"])
            assert (s["range_class"] == "illustrative") == (not any(not r.illustrative for r in rows)), (drug, s)


def test_measurement_entries_record_the_measured_value(utts):
    meas = [(u, e) for u in utts for e in u.entries if e.context == "measurement"]
    assert meas
    for u, e in meas:
        assert e.measured_value is not None and e.dose_value is None
        assert u.text[e.measured_value.span[0]:e.measured_value.span[1]] == e.measured_value.surface


def test_unit_swap_only_when_a_unit_is_spoken():
    for u in generate(seed=1234, per_pattern=20):
        for e in u.entries:
            if e.anomaly == "unit_swap":
                assert e.dose_unit is not None, u.id


def test_spoken_time_phrases_are_always_gold(utts):
    import re
    for u in utts:
        spans = [e.time.span for e in u.entries if e.time.span]
        for m in re.finditer(r"\b(just now|right now|abhi)\b", u.text):
            assert any(s[0] <= m.start() and m.end() <= s[1] for s in spans), (u.id, u.text)
