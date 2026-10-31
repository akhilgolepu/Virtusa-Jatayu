import pytest

from datagen.generate import generate, load_doses
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
    assert len(families) == 60 and 140 <= len(patterns) <= 160
    assert {u.lang for u in utts} == {"en", "hinglish"}


def test_anomaly_rate():
    utts = generate(seed=1234, per_pattern=20)
    given = [e for u in utts for e in u.entries if e.kind == "medication" and e.context == "given" and e.dose_value]
    rate = sum(e.anomaly is not None for e in given) / len(given)
    assert 0.03 <= rate <= 0.08, rate


def test_dose_table_consistent_with_lexicon():
    lex = Lexicon.load()
    doses = load_doses()
    assert set(doses) == set(lex.drug_names())
    for drug, specs in doses.items():
        for s in specs:
            assert s["route"] in lex.drug(drug).routes and s["unit"] in lex.drug(drug).units, (drug, s)
