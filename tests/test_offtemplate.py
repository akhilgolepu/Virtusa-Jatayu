"""Rules extractor on the hand-written off-template DEV set (eval/offtemplate_dev.yaml). A case passes when every
gold record is found with the right values (or with the flag the case accepts instead) and nothing extra is emitted.
Known failures are xfail(strict) with the reason from the YAML, so a fix shows up as XPASS."""
from datetime import datetime

import pytest

from eval.metrics import gold_values, pred_values, same
from eval.offtemplate import _entry, cases
from jatayu.extract.rules import RulesExtractor
from jatayu.validate import validate_all

CONTEXT = {"not_given": "possible_not_given", "measurement": "possible_measurement"}


def _params():
    for c in cases():
        marks = [pytest.mark.xfail(reason=c["xfail"], strict=True)] if c.get("xfail") else []
        yield pytest.param(c, id=c["id"], marks=marks)


@pytest.mark.parametrize("case", _params())
def test_offtemplate_rules(case, lexicon):
    cap = datetime.fromisoformat(case["capture_time"])
    preds = validate_all(RulesExtractor(lexicon).extract(case["text"], cap), lexicon, [])
    free = list(preds)
    ok_if = case.get("ok_if_flagged", {})
    for e in case["entries"]:
        g = _entry(e)
        gv = gold_values(g, cap)
        anchor = "drug" if g.kind == "medication" else "procedure"
        match = next((p for p in free if pred_values(p)[anchor] == gv[anchor]), None)
        assert match is not None, f"{gv[anchor]} not found in {[pred_values(p)[anchor] for p in preds]}"
        free.remove(match)
        codes = {f.code for f in match.flags}
        if g.context != "given":
            assert CONTEXT[g.context] in codes, f"{gv[anchor]}: missing {CONTEXT[g.context]}"
            continue
        assert not codes & set(CONTEXT.values()), f"{gv[anchor]} given but flagged {codes}"
        pv = pred_values(match)
        for f in ("dose_value", "dose_unit", "route", "time"):
            if not same(f, gv[f], pv[f]):
                assert ok_if.get(f) in codes, f"{gv[anchor]}.{f}: expected {gv[f]}, got {pv[f]} (flags {sorted(codes)})"
    assert not free, f"extra entries: {[pred_values(p) for p in free]}"
