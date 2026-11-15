"""Round 10 headline dangerous error: a wrong drug, dose, unit, route or status recorded without a flag that must be
ticked (severity high). The old matched-drug metric is kept as a secondary row."""
import json

from eval.metrics import Scorer, high_codes
from jatayu.models import Flag
from test_eval_metrics import gold, pred, utt  # tests/ is on sys.path (no package)

HIGH = Flag(code="sound_alike_drug", field="drug", severity="high", message="")
MEDIUM = Flag(code="low_confidence", field="drug", severity="medium", message="")


def _m(*cases):
    s = Scorer()
    for i, (golds, preds) in enumerate(cases):
        s.add(utt(golds, f"u{i}"), preds)
    return s, s.metrics()


def test_wrong_drug_is_dangerous_in_the_new_metric_and_invisible_in_the_old():
    s, m = _m(([gold(drug="ondansetron", dose=4, unit="mg", route="IV")],
               [pred(drug="salbutamol", dose=4, unit="mg", route="IV", flags=[MEDIUM])]))
    assert m["dangerous_error"]["count"] == 0  # old: a miss plus an extra prediction
    assert m["dangerous_error_r10"]["count"] == 1 and m["dangerous_error_r10"]["uncaught_by_kind"] == {"wrong drug": 1}
    row = next(e for e in s.errors() if e.get("recorded_instead"))
    assert row["recorded_instead"]["drug"] == "salbutamol" and row["dangerous_r10"] is True


def test_a_flag_that_must_be_ticked_catches_a_medium_one_does_not():
    _, m = _m(([gold(drug="ondansetron")], [pred(drug="salbutamol", flags=[HIGH])]),
              ([gold()], [pred(dose=0.5, flags=[MEDIUM])]),
              ([gold()], [pred(dose=0.5, flags=[Flag(code="dose_out_of_range", field="dose_value", severity="high", message="")])]))
    assert m["dangerous_error_r10"]["count"] == 1 and m["dangerous_error_r10"]["uncaught_by_kind"] == {"wrong dose/unit/route": 1}
    assert m["dangerous_error"]["count"] == 0  # old: the medium flag caught it


def test_status_and_denominator():
    ng = dict(ctx="not_given", dose=None, unit=None, route=None)
    _, m = _m(([gold(**ng)], [pred(dose=None, unit=None, route=None)]),
              ([gold(**ng)], [pred(dose=None, unit=None, route=None,
                                   flags=[Flag(code="possible_not_given", field="drug", severity="high", message="")])]),
              ([gold()], [pred()]))
    r = m["dangerous_error_r10"]
    assert (r["count"], r["denominator"]) == (1, 3) and r["uncaught_by_kind"] == {"status (not given recorded as given)": 1}


def test_an_empty_field_is_an_omission_not_a_wrong_value():
    _, m = _m(([gold()], [pred(route=None)]))
    assert m["dangerous_error_r10"]["count"] == 0
    assert m["dangerous_error_r10"]["errors_by_kind"] == {"omitted dose/unit/route (shown as not stated; not counted)": 1}


def test_high_codes_reads_field_missing_from_the_output():
    assert high_codes(["field_missing"], {"drug": "x", "dose_value": 1, "dose_unit": "mg"}) == set()  # route: medium
    assert high_codes(["field_missing"], {"drug": "x"}) == {"field_missing"}
    assert high_codes(["low_confidence", "sound_alike_drug"], {}) == {"sound_alike_drug"}


def test_offline_rescore_matches_the_scorer_on_new_rows_and_bounds_old_ones(lexicon):
    from eval.rescore_r10 import rescore_rows

    s, m = _m(([gold(drug="ondansetron", dose=4, unit="mg", route="IV")],
               [pred(drug="salbutamol", dose=5, unit="mg", route="NEB")]),  # in range: no certain high flag
              ([gold()], [pred(dose=0.5)]))
    rows = json.loads(json.dumps(s.errors(), default=str))
    r = rescore_rows(rows, m["dangerous_error"]["denominator"], m["administration_status_error"], lexicon)
    assert r["new"]["count"] == m["dangerous_error_r10"]["count"] == 2 and not r["new"]["is_upper_bound"]
    for row in rows:  # an old-style file: extra rows without flags -> the wrong drug becomes a bound
        if row["kind"] == "extra_prediction":
            row.pop("high_flags"), row.pop("flags")
    old = rescore_rows(rows, 2, m["administration_status_error"], lexicon)
    assert old["new"]["is_upper_bound"] and old["uncaught_bounded_by_kind"] == {"wrong drug": 1}
