from datetime import datetime, timedelta

import pytest

from jatayu import config
from jatayu.extract.llm import LlmExtractor
from jatayu.llm import LlmRunner

CAP = datetime(2026, 11, 1, 10, 45).astimezone()


class StubRunner:
    def __init__(self, returns):
        self.returns, self.calls = returns, []

    def complete_json(self, system, user, schema, max_tokens=512):
        self.calls.append(user)
        return self.returns


def _e(**kw):
    base = {"kind": "medication", "context": "given", "drug": None, "dose": None, "unit": None, "route": None,
            "time": None, "procedure": None, "detail": None}
    return {**base, **kw}


def ext(lexicon, raw, entries):
    return LlmExtractor(lexicon, lambda: StubRunner({"entries": entries})).extract(raw, CAP)


def test_values_are_derived_from_quotes_with_raw_spans(lexicon):
    raw = "uh gave point five mg of adrenaline IM two mins ago"
    [e] = ext(lexicon, raw, [_e(drug="adrenaline", dose="point five", unit="mg", route="IM", time="two mins ago")])
    assert (e.drug.value, e.dose_value.value, e.dose_unit.value, e.route.value) == ("epinephrine", 0.5, "mg", "IM")
    assert e.time.value == CAP - timedelta(minutes=2) and e.drug.source == "llm"
    for f in (e.drug, e.dose_value, e.dose_unit, e.route, e.time):
        assert raw[f.span[0]:f.span[1]].lower() in raw.lower()
    assert raw[e.dose_value.span[0]:e.dose_value.span[1]] == "point five"
    assert e.flags == []


def test_invented_drug_is_rejected(lexicon):
    assert ext(lexicon, "gave aspirin 300 mg", [_e(drug="amiodarone", dose="300", unit="mg")]) == []


def test_quote_not_in_transcript_drops_the_field(lexicon):
    [e] = ext(lexicon, "gave aspirin 300 mg PO", [_e(drug="aspirin", dose="325", unit="mg", route="PO")])
    assert e.dose_value.value is None
    assert any(f.code == "llm_unsupported" and f.field == "dose_value" and f.severity == "high" for f in e.flags)


def test_unparseable_quote_drops_the_field(lexicon):
    [e] = ext(lexicon, "gave aspirin 300 mg PO", [_e(drug="aspirin", dose="gave", unit="mg", route="PO")])
    assert e.dose_value.value is None and any(f.code == "llm_unsupported" for f in e.flags)


def test_whole_tokens_only(lexicon):
    [e] = ext(lexicon, "gave atropine 10 mg IV", [_e(drug="atropine", dose="1", unit="mg", route="IV")])
    assert e.dose_value.value is None


def test_context_flags(lexicon):
    [e] = ext(lexicon, "patient allergic to morphine", [_e(drug="morphine", context="not_given")])
    assert any(f.code == "possible_not_given" and f.severity == "high" for f in e.flags)


def test_procedure(lexicon):
    [p] = ext(lexicon, "tubed him with a size 7.5 tube at 10:30",
              [_e(kind="procedure", procedure="tubed", detail="size 7.5", time="at 10:30")])
    assert (p.procedure.value, p.detail.value, p.time.value.hour) == ("endotracheal intubation", "size 7.5", 10)


@pytest.mark.models
@pytest.mark.skipif(not config.LLM_MODEL_PATH.exists(), reason="LLM not downloaded")
def test_real_llm_on_two_drugs(lexicon):
    runner = LlmRunner(config.LLM_MODEL_PATH)
    got = LlmExtractor(lexicon, lambda: runner).extract("aspirin 300 mg PO and 4 mg ondansetron IV", CAP)
    assert [(e.drug.value, e.dose_value.value, e.dose_unit.value, e.route.value) for e in got] == \
        [("aspirin", 300.0, "mg", "PO"), ("ondansetron", 4.0, "mg", "IV")]


def test_stray_fields_outside_the_kind_do_not_flag(lexicon):
    [e] = ext(lexicon, "gave aspirin 300 mg PO", [_e(drug="aspirin", dose="300", unit="mg", route="PO", procedure="gave")])
    assert not any(f.code == "llm_unsupported" for f in e.flags)
