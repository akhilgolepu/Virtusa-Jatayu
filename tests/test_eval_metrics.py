from datetime import datetime, timedelta

from datagen.schema import GoldEntry, GoldField, GoldTime, GoldUtterance
from eval.metrics import Scorer
from jatayu.models import Field, Flag, MedicationEntry

CAP = "2026-10-31T10:45:00+05:30"
T = datetime.fromisoformat(CAP)


def gf(v):
    return GoldField(value=v, surface=str(v), span=(0, 1))


def gold(drug="epinephrine", dose=0.3, unit="mg", route="IM", ctx="given", offset=-120):
    return GoldEntry(kind="medication", context=ctx, drug=gf(drug), dose_value=gf(dose) if dose else None,
                     dose_unit=gf(unit) if unit else None, route=gf(route) if route else None,
                     time=GoldTime(kind="relative", offset_s=offset, surface="x", span=(0, 1)))


def pred(drug="epinephrine", dose=0.3, unit="mg", route="IM", t=T - timedelta(seconds=120), flags=()):
    f = lambda v: Field(value=v, span=(0, 1), confidence=1.0, source="rules", raw="x")  # noqa: E731
    return MedicationEntry(drug=f(drug), dose_value=f(dose), dose_unit=f(unit), route=f(route), time=f(t), flags=list(flags))


def utt(entries, uid="u1"):
    return GoldUtterance(id=uid, family="f", category="med_basic", lang="en", text="x", capture_time=CAP, entries=entries)


def test_perfect_prediction():
    s = Scorer()
    s.add(utt([gold()]), [pred()])
    m = s.metrics()
    assert m["entity"]["micro"]["f1"] == 1.0 and m["record_exact_match"]["rate"] == 1.0
    assert m["dangerous_error"] == {"count": 0, "denominator": 1, "rate": 0.0}


def test_unflagged_wrong_dose_is_dangerous_flagged_is_not():
    s = Scorer()
    s.add(utt([gold()], "a"), [pred(dose=0.5)])
    s.add(utt([gold()], "b"), [pred(dose=3.0, flags=[Flag(code="dose_out_of_range", field="dose_value", severity="high", message="")])])
    m = s.metrics()
    assert m["dangerous_error"]["count"] == 1 and m["dangerous_error"]["denominator"] == 2
    assert m["entity"]["per_field"]["dose_value"]["tp"] == 0
    assert s.errors()[0]["id"] == "a" and s.errors()[0]["dangerous"] is True


def test_time_within_60s_counts_and_missing_entry_is_a_miss_not_dangerous():
    s = Scorer()
    s.add(utt([gold(), gold(drug="aspirin", dose=300, unit="mg", route="PO")]), [pred(t=T - timedelta(seconds=150))])
    m = s.metrics()
    assert m["entity"]["per_field"]["time"]["tp"] == 1
    assert m["dangerous_error"]["count"] == 0 and m["record_exact_match"]["rate"] == 0.5
    assert m["entity"]["per_field"]["drug"]["recall"] == 0.5


def test_context_entries_scored_separately():
    s = Scorer()
    s.add(utt([gold(ctx="not_given", dose=None, unit=None, route=None)], "a"), [pred(dose=None, unit=None, route=None)])
    s.add(utt([gold(ctx="not_given", dose=None, unit=None, route=None)], "b"),
          [pred(dose=None, unit=None, route=None, flags=[Flag(code="possible_not_given", field="drug", severity="high", message="")])])
    s.add(utt([gold(ctx="measurement", dose=None, unit=None, route=None)], "c"), [])
    m = s.metrics()
    assert m["context_error"] == {"count": 1, "denominator": 3, "rate": round(1 / 3, 4)}
    assert m["dangerous_error"]["denominator"] == 0


def test_extra_prediction_is_a_false_positive():
    s = Scorer()
    s.add(utt([gold()]), [pred(), pred(drug="aspirin", dose=300, unit="mg", route="PO")])
    assert s.metrics()["entity"]["per_field"]["drug"]["precision"] == 0.5


def test_measurement_reading_in_dose_field_is_not_an_entity_error():
    s = Scorer()
    meas = Flag(code="possible_measurement", field="drug", severity="high", message="")
    s.add(utt([gold(drug="magnesium sulfate", dose=None, unit=None, route=None, ctx="measurement")]),
          [pred(drug="magnesium sulfate", dose=0.6, unit=None, route=None, flags=[meas])])
    m = s.metrics()
    assert m["record_exact_match"]["rate"] == 1.0 and m["entity"]["per_field"]["dose_value"]["pred"] == 0


def test_not_range_checked_flag_does_not_catch_a_dangerous_error():
    s = Scorer()
    unchecked = Flag(code="no_reference_range", field="dose_value", severity="medium", message="")
    s.add(utt([gold()]), [pred(dose=5.0, flags=[unchecked])])
    assert s.metrics()["dangerous_error"]["count"] == 1
