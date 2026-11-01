from datetime import datetime

import pytest

from jatayu import config
from jatayu.extract.hybrid import HybridExtractor
from jatayu.extract.rules import RulesExtractor
from jatayu.llm import LlmError, LlmRunner

CAP = datetime(2026, 11, 1, 10, 45).astimezone()


class StubRunner:
    def __init__(self, returns=None, error=None):
        self.returns, self.error, self.calls = returns, error, []

    def complete_json(self, system, user, schema, max_tokens=512):
        self.calls.append(user)
        if self.error:
            raise self.error
        return self.returns


def _e(**kw):
    base = {"kind": "medication", "context": "given", "drug": None, "dose": None, "unit": None, "route": None,
            "time": None, "procedure": None, "detail": None}
    return {**base, **kw}


def hybrid(lexicon, runner):
    return HybridExtractor(lexicon, lambda: runner, RulesExtractor(lexicon))


def test_links_two_drugs_from_candidates(lexicon):
    raw = "aspirin 300 mg PO and 4 mg ondansetron IV"
    # candidates: 1 drug aspirin, 2 number 300, 3 unit mg, 4 route PO, 5 number 4, 6 unit mg, 7 drug ondansetron, 8 route IV
    runner = StubRunner({"entries": [_e(drug=1, dose=2, unit=3, route=4), _e(drug=7, dose=5, unit=6, route=8)]})
    entries, warnings = hybrid(lexicon, runner).extract_with_warnings(raw, CAP)
    assert warnings == [] and '[7] drug "ondansetron"' in runner.calls[0]
    assert [(e.drug.value, e.dose_value.value, e.route.value) for e in entries] == \
        [("aspirin", 300.0, "PO"), ("ondansetron", 4.0, "IV")]
    assert raw[entries[1].dose_value.span[0]:entries[1].dose_value.span[1]] == "4"


def test_wrong_kind_and_unknown_ids_are_dropped(lexicon):
    runner = StubRunner({"entries": [_e(drug=1, dose=4, unit=99, route=4)]})  # dose->route candidate, unit->no such id
    [e] = hybrid(lexicon, runner).extract("aspirin 300 mg PO", CAP)
    assert e.dose_value.value is None and e.dose_unit.value is None and e.route.value == "PO"
    assert {f.field for f in e.flags if f.code == "llm_unsupported"} == {"dose_value", "dose_unit"}


def test_a_candidate_is_used_once(lexicon):
    runner = StubRunner({"entries": [_e(drug=1, dose=2, unit=3), _e(drug=1, dose=2, unit=3)]})
    entries = hybrid(lexicon, runner).extract("aspirin 300 mg PO", CAP)
    assert len(entries) == 1


def test_llm_failure_falls_back_to_rules(lexicon):
    entries, warnings = hybrid(lexicon, StubRunner(error=LlmError("boom"))).extract_with_warnings("aspirin 300 mg PO", CAP)
    assert entries[0].drug.value == "aspirin" and entries[0].drug.source == "rules"
    assert warnings and warnings[0].startswith("llm unavailable")


def test_no_drug_means_no_llm_call(lexicon):
    runner = StubRunner({"entries": []})
    assert hybrid(lexicon, runner).extract("patient is breathing fine", CAP) == [] and runner.calls == []


def test_rules_context_cues_are_kept(lexicon):
    runner = StubRunner({"entries": [_e(drug=1)]})  # LLM says "given" but the rules see "allergic to"
    [e] = hybrid(lexicon, runner).extract("patient allergic to morphine", CAP)
    assert any(f.code == "possible_not_given" for f in e.flags)


@pytest.mark.models
@pytest.mark.skipif(not config.LLM_MODEL_PATH.exists(), reason="LLM not downloaded")
def test_real_llm_hybrid(lexicon):
    runner = LlmRunner(config.LLM_MODEL_PATH)
    got = HybridExtractor(lexicon, lambda: runner, RulesExtractor(lexicon)).extract(
        "aspirin 300 mg PO and 4 mg ondansetron IV", CAP)
    assert [(e.drug.value, e.dose_value.value, e.dose_unit.value, e.route.value) for e in got] == \
        [("aspirin", 300.0, "mg", "PO"), ("ondansetron", 4.0, "mg", "IV")]
