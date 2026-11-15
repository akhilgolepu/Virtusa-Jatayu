"""Round-8 safety fixes (general rules, new sentences — none from the blind set):
a. a drug-like word the lexicon does not know, followed by a dose, unit or route, is kept with its spoken name and a
   visible drug_not_in_lexicon flag — never dropped;
b. a concentration ("x mg per ml", "x mg/ml", "1 in 10000") is never recorded as the dose: concentration_not_dose,
   and the entry cannot be confirmed until the responder enters the dose."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from jatayu.api import create_app
from jatayu.extract.hybrid import HybridExtractor
from jatayu.extract.rules import RulesExtractor
from jatayu.output.fhir import to_bundle, validate_bundle
from jatayu.validate import validate_all

CAP = datetime(2026, 11, 15, 10, 45).astimezone()


def ext(lexicon, raw):
    return validate_all(RulesExtractor(lexicon).extract(raw, CAP), lexicon, [])


def codes(e):
    return {f.code for f in e.flags}


@pytest.mark.parametrize("raw,name,dose", [
    ("buscopan 20 mg IM given", "buscopan", 20.0),
    ("1 g ceftriaxone IV over 30 minutes", "ceftriaxone", 1.0),
    ("gave labetalol IV for the pressure", "labetalol", None),
])
def test_unknown_drug_is_kept_and_flagged(lexicon, raw, name, dose):
    [e] = ext(lexicon, raw)
    assert e.drug.value == name and e.drug.raw.lower() == name and e.dose_value.value == dose
    [f] = [f for f in e.flags if f.code == "drug_not_in_lexicon"]
    assert f.severity == "high" and name in f.message.lower()
    assert not lexicon.has_drug(name)  # the fix is general: nothing was added to the lexicon


@pytest.mark.parametrize("raw", ["pulse 110, aspirin 300 mg PO", "patient weighs about 70 kilos, ketamine 1 mg IV",
                                 "pain score 8 then morphine 5 mg IV", "tibial IO in, adrenaline 1 mg IO",
                                 "so we gave like 0.4 mg of naloxone IV", "between 160 and 325 mg aspirin PO"])
def test_ordinary_words_before_numbers_are_not_drugs(lexicon, raw):
    assert all("drug_not_in_lexicon" not in codes(e) for e in ext(lexicon, raw))


def test_unknown_drug_bundle_is_valid_without_a_code(lexicon, sample_utterance):
    entries = ext(lexicon, "buscopan 20 mg IM given")
    b = to_bundle(sample_utterance, entries, lexicon)
    validate_bundle(b)
    med = b["entry"][0]["resource"]["medicationCodeableConcept"]
    assert med == {"text": "buscopan"}


def test_unknown_drug_reaches_the_confirm_screen_and_needs_acknowledging(tmp_path):
    c = TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))
    inc = c.post("/api/incidents", json={}).json()["id"]
    [e] = c.post("/api/utterances", data={"incident_id": inc, "text": "1 g ceftriaxone IV over 30 minutes"}).json()["entries"]
    assert e["drug"]["value"] == "ceftriaxone" and "drug_not_in_lexicon" in [f["code"] for f in e["flags"]]
    assert c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": []}).status_code == 409
    assert c.post(f"/api/incidents/{inc}/confirm",
                  json={"entry_ids": [e["id"]], "acknowledged": ["drug_not_in_lexicon"]}).status_code == 200


def test_hybrid_keeps_an_unknown_drug_the_llm_links_or_skips(lexicon):
    class Stub:
        def __init__(self, out):
            self.out = out

        def complete_json(self, system, user, schema, max_tokens=512):
            return self.out
    rules = RulesExtractor(lexicon)
    raw = "buscopan 20 mg IM given"  # candidates: 1 drug buscopan, 2 number 20, 3 unit mg, 4 route IM
    for out in ({"entries": [{"drug": 1, "dose": 2, "unit": 3, "route": 4}]}, {"entries": []}):
        [e] = validate_all(HybridExtractor(lexicon, lambda: Stub(out), rules).extract(raw, CAP), lexicon, [])
        assert e.drug.value == "buscopan" and "drug_not_in_lexicon" in codes(e)


@pytest.mark.parametrize("raw,drug", [
    ("atropine 0.6 mg per ml, 1 ml IV", "atropine"),
    ("ketamine 50 mg/ml, 2 ml IM", "ketamine"),
    ("noradrenaline 1 in 10000, 5 ml IV", "norepinephrine"),
])
def test_concentration_is_not_a_dose(lexicon, raw, drug):
    [e] = ext(lexicon, raw)
    assert e.drug.value == drug and e.dose_value.value is None and e.dose_unit.value is None
    [f] = [f for f in e.flags if f.code == "concentration_not_dose"]
    assert f.severity == "high" and "enter the dose" in f.message


def test_plain_doses_are_not_concentrations(lexicon):
    for raw in ("morphine 5 mg IV", "oxygen 10 litres per minute via mask", "fentanyl 50 mcg IN"):
        assert all("concentration_not_dose" not in codes(e) for e in ext(lexicon, raw)), raw


def test_hybrid_never_keeps_a_linked_dose_for_a_concentration(lexicon):
    class Stub:
        def complete_json(self, system, user, schema, max_tokens=512):
            return {"entries": [{"drug": 1, "dose": 2, "unit": 3, "route": 7}]}  # links the 0.6 of "0.6 mg per ml"
    raw = "atropine 0.6 mg per ml, 1 ml IV"
    [e] = HybridExtractor(lexicon, lambda: Stub(), RulesExtractor(lexicon)).extract(raw, CAP)
    assert e.dose_value.value is None and "concentration_not_dose" in codes(e)


def test_concentration_must_be_replaced_by_a_dose_before_confirming(tmp_path):
    c = TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))
    inc = c.post("/api/incidents", json={}).json()["id"]
    [e] = c.post("/api/utterances", data={"incident_id": inc, "text": "ketamine 50 mg/ml, 2 ml IM"}).json()["entries"]
    high = [f["code"] for f in e["flags"] if f["severity"] == "high"]
    r = c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": high})
    assert r.status_code == 409 and "needs_dose" in r.json()["detail"]  # acknowledging is not enough
    e["dose_value"]["value"], e["dose_unit"]["value"] = 100, "mg"
    edited = c.post(f"/api/incidents/{inc}/entries/{e['id']}/edit", json={"entry": e}).json()["entry"]
    assert "concentration_not_dose" not in [f["code"] for f in edited["flags"]]
    high = [f["code"] for f in edited["flags"] if f["severity"] == "high"]
    assert c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": high}).status_code == 200
