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


def test_kind_is_inferred_from_the_anchor_not_trusted(lexicon):
    runner = StubRunner({"entries": [{"kind": "procedure", "drug": 1, "dose": 2, "unit": 3, "route": 4}]})
    [e] = hybrid(lexicon, runner).extract("morphine 5 mg IM", CAP)
    assert e.kind == "medication" and e.dose_value.value == 5.0


def test_omitted_fields_mean_not_said(lexicon):
    runner = StubRunner({"entries": [{"drug": 1, "route": 2}]})
    [e] = hybrid(lexicon, runner).extract("aspirin PO", CAP)
    assert e.route.value == "PO" and e.dose_value.value is None


def test_schema_keeps_output_short(lexicon):
    from jatayu.extract.hybrid import schema_for
    cands = RulesExtractor(lexicon).candidates("aspirin 300 mg PO", CAP)
    item = schema_for(cands)["properties"]["entries"]["items"]
    assert "kind" not in item["properties"] and item.get("required", []) == []


def test_schema_caps_entries_at_one_per_anchor(lexicon):
    """A repeat loop ran to max_tokens and cut the JSON off (all 15 round-2 fallbacks); the array is now bounded."""
    from jatayu.extract.hybrid import schema_for
    ex = RulesExtractor(lexicon)
    assert schema_for(ex.candidates("started chest compressions at 10 28", CAP))["properties"]["entries"]["maxItems"] == 1
    assert schema_for(ex.candidates("aspirin 300 mg PO then ondansetron 4 mg IV", CAP))["properties"]["entries"]["maxItems"] == 2


def test_truncated_llm_output_is_an_llm_error(monkeypatch):
    from jatayu.llm import LlmError, LlmRunner

    class Fake:
        def create_chat_completion(self, **kw):
            return {"choices": [{"finish_reason": "length", "message": {"content": '{"entries": [{"drug": 1}, {'}}]}
    r = LlmRunner("x")
    monkeypatch.setattr(r, "_load", lambda: Fake())
    with pytest.raises(LlmError, match="truncated"):
        r.complete_json("s", "u", {})


def test_schema_only_offers_right_kind_ids(lexicon):
    seen = {}

    class Spy(StubRunner):
        def complete_json(self, system, user, schema, max_tokens=512):
            seen["schema"] = schema
            return {"entries": [{"drug": 1, "dose": 2, "unit": 3, "route": 4}]}

    hybrid(lexicon, Spy()).extract("aspirin 300 mg PO", CAP)
    props = seen["schema"]["properties"]["entries"]["items"]["properties"]
    assert props["drug"]["enum"] == [1, None] and props["dose"]["enum"] == [2, None]
    assert "time" not in props and "procedure" not in props and "detail" not in props


def test_one_time_phrase_can_cover_two_drugs(lexicon):
    raw = "at 10 40 aspirin 300 mg PO and 4 mg ondansetron IV"
    # 1 time, 2 drug aspirin, 3 number 300, 4 unit, 5 route PO, 6 number 4, 7 unit, 8 drug ondansetron, 9 route IV
    runner = StubRunner({"entries": [{"drug": 2, "dose": 3, "unit": 4, "route": 5, "time": 1},
                                     {"drug": 8, "dose": 6, "unit": 7, "route": 9, "time": 1}]})
    a, b = hybrid(lexicon, runner).extract(raw, CAP)
    assert a.time.value == b.time.value and not any(f.code == "llm_unsupported" for f in a.flags + b.flags)


def test_exact_drug_match_is_not_low_confidence(lexicon):
    [e] = hybrid(lexicon, StubRunner({"entries": [{"drug": 1, "dose": 2, "unit": 3, "route": 4}]})).extract("morphine 5 mg IV", CAP)
    assert not any(f.code == "low_confidence" for f in e.flags)
    [f] = hybrid(lexicon, StubRunner({"entries": [{"drug": 1, "dose": 2, "unit": 3, "route": 4}]})).extract("ondansatron 4 mg IV", CAP)
    assert any(x.code == "low_confidence" for x in f.flags)


def test_fields_outside_the_entry_kind_are_ignored_not_consumed(lexicon):
    raw = "gave point three milligrams of adrenaline IM two minutes ago and started CPR"
    out = {"entries": [{"drug": 3, "dose": 1, "unit": 2, "route": 4, "time": 5, "procedure": 6}, {"procedure": 6}]}
    med, proc = hybrid(lexicon, StubRunner(out)).extract(raw, CAP)
    assert med.drug.value == "epinephrine" and proc.kind == "procedure" and proc.procedure.value == "cpr"
    assert not any(f.code == "llm_unsupported" for f in med.flags + proc.flags)


def test_drugs_the_llm_leaves_out_are_kept_from_rules(lexicon):
    entries, warnings = hybrid(lexicon, StubRunner({"entries": []})).extract_with_warnings(
        "gave 1 mg adrenaline IV and 10 mg morphine IV", CAP)
    assert sorted(e.drug.value for e in entries) == ["epinephrine", "morphine"]
    assert all(any(f.code == "llm_omitted" for f in e.flags) for e in entries) and warnings


def test_hybrid_carries_raw_words(lexicon):
    [e] = hybrid(lexicon, StubRunner({"entries": [{"drug": 1, "dose": 2, "unit": 3, "route": 4}]})).extract("Emeset 4 mg IV", CAP)
    assert (e.drug.raw, e.drug.value, e.dose_unit.raw) == ("Emeset", "ondansetron", "mg")


def test_time_linked_from_another_clause_is_flagged(lexicon):
    raw = "at 10 40 aspirin 300 mg PO and ondansetron 4 mg IV"
    # candidates: 1 time, 2 aspirin, 3 300, 4 mg, 5 PO, 6 ondansetron, 7 4, 8 mg, 9 IV
    runner = StubRunner({"entries": [_e(drug=2, dose=3, unit=4, route=5, time=1), _e(drug=6, dose=7, unit=8, route=9, time=1)]})
    a, b = hybrid(lexicon, runner).extract(raw, CAP)
    assert not any(f.code == "time_borrowed" for f in a.flags)
    assert any(f.code == "time_borrowed" for f in b.flags)


def test_rules_repeat_dose_survives_single_link(lexicon):
    raw = "morphine 4 mg IV then another 2 mg IV"
    runner = StubRunner({"entries": [_e(drug=1, dose=2, unit=3, route=4)]})
    entries = hybrid(lexicon, runner).extract(raw, CAP)
    assert [(e.drug.value, e.dose_value.value) for e in entries] == [("morphine", 4.0), ("morphine", 2.0)]
    assert any(f.code == "repeat_dose_inferred" for f in entries[1].flags)


def test_dose_range_flag_carried_into_hybrid(lexicon):
    runner = StubRunner({"entries": [_e(drug=1, dose=3, unit=4, route=5)]})
    [e] = hybrid(lexicon, runner).extract("morphine 2 to 4 mg IV", CAP)
    assert any(f.code == "dose_range_stated" for f in e.flags)


def test_rules_correction_overrides_the_llm_dose(lexicon):
    raw = "given morphine 1.5, no, 8 milligramme intramuscularly"
    # candidates: 1 morphine, 2 1.5, 3 8, 4 mg, 5 IM -- the LLM links the pre-correction 1.5
    runner = StubRunner({"entries": [_e(drug=1, dose=2, unit=4, route=5)]})
    [e] = hybrid(lexicon, runner).extract(raw, CAP)
    assert e.dose_value.value == 8.0 and e.dose_value.source == "rules" and e.dose_unit.value == "mg"
    assert any(f.code == "self_correction" for f in e.flags)


def test_agreeing_llm_keeps_its_fields_and_gets_the_correction_note(lexicon):
    runner = StubRunner({"entries": [_e(drug=1, dose=3, unit=4, route=5)]})
    [e] = hybrid(lexicon, runner).extract("given morphine 1.5, no, 8 milligramme intramuscularly", CAP)
    assert e.dose_value.value == 8.0 and e.dose_value.source == "llm"
    assert any(f.code == "self_correction" for f in e.flags)


def test_correction_override_keeps_the_missing_unit_flag(lexicon):
    raw = "administered furosemide 30, no 25, empty IVP"
    # candidates: 1 furosemide, 2 30, 3 25, 4 IV(P) -- the LLM links 30 and no unit
    runner = StubRunner({"entries": [_e(drug=1, dose=2, route=4)]})
    [e] = hybrid(lexicon, runner).extract(raw, CAP)
    assert e.dose_value.value == 25.0 and e.dose_unit.value is None
    assert any(f.code == "field_missing" and f.field == "dose_unit" for f in e.flags)
