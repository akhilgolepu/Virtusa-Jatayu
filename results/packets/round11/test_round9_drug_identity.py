"""Round 9 (general rules, new sentences — none from dev, blind v1 or the round-8 tests):
1. a drug matched only by sound, below SOUND_ACK_BELOW (spelling similarity to the drug's nearest name), carries a HIGH
   sound_alike_drug flag ("heard X — did you mean Y?"); the heard word is kept in the drug field, the bundle and the PDF,
   and the entry cannot be confirmed without ticking the flag;
2. junk guard for drug_not_in_lexicon: an ordinary English word (the recogniser's own vocabulary) is an unknown drug only
   with a dose AND a unit after it; a word shaped like a route or unit is never one. True unknown drugs stay flagged."""
import io
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from jatayu.api import create_app
from jatayu.extract.rules import COMMON_ENGLISH, SOUND_ACK_BELOW, RulesExtractor
from jatayu.validate import validate_all

CAP = datetime(2026, 11, 15, 10, 45).astimezone()


def ext(lexicon, raw):
    return validate_all(RulesExtractor(lexicon).extract(raw, CAP), lexicon, [])


def codes(e):
    return {f.code for f in e.flags}


def _client(tmp_path):
    return TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))


# ---- 1. matched by sound -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,heard,recorded", [  # round 10: brand / alias variants and look-alikes keep the tick
    ("gave zofren 4 mg IV", "zofren", "ondansetron"),
    ("gave lasicks 40 mg IV", "lasicks", "furosemide"),
    ("gave ketalor 20 mg IV", "ketalor", "ketamine"),
    ("adrenelin 0.3 mg IM given", "adrenelin", "epinephrine"),
])
def test_sound_match_needs_acknowledgement_and_keeps_the_heard_word(lexicon, raw, heard, recorded):
    [e] = ext(lexicon, raw)
    assert e.drug.value == recorded and e.drug.raw == heard
    [f] = [f for f in e.flags if f.code == "sound_alike_drug"]
    assert f.severity == "high" and f"Heard '{heard}'" in f.message and f"did you mean {recorded}?" in f.message
    assert "low_confidence" not in codes(e)  # replaced by the stronger flag, not stacked


@pytest.mark.parametrize("raw,heard,recorded", [  # round 11: generic-name spelling variants need the tick again
    ("gave ondansatron 4 mg IV", "ondansatron", "ondansetron"),
    ("gave furosemid 40 mg IV", "furosemid", "furosemide"),
    ("gave kettamin 20 mg IV", "kettamin", "ketamine"),
])
def test_spelling_variant_of_the_generic_name_needs_the_tick(lexicon, raw, heard, recorded):
    [e] = ext(lexicon, raw)
    assert e.drug.value == recorded and e.drug.raw == heard
    [f] = [f for f in e.flags if f.code == "sound_alike_drug"]
    assert f.severity == "high" and f"Heard '{heard}'" in f.message and "low_confidence" not in codes(e)


def test_near_identical_spelling_stays_low_confidence(lexicon):
    """A one-letter slip in a long name scores >= SOUND_ACK_BELOW: flagged medium, no forced tick."""
    [e] = ext(lexicon, "gave hydrocortisonne 100 mg IV")
    assert e.drug.value == "hydrocortisone" and "low_confidence" in codes(e) and "sound_alike_drug" not in codes(e)
    assert SOUND_ACK_BELOW == 0.95


def test_exact_lexicon_word_has_no_sound_flag(lexicon):
    [e] = ext(lexicon, "gave ondansetron 4 mg IV")
    assert not codes(e) & {"sound_alike_drug", "low_confidence"}


def test_sound_match_blocks_confirm_until_ticked_and_shows_everywhere(tmp_path):
    from pypdf import PdfReader

    from jatayu.output.fhir import provenance

    c = _client(tmp_path)
    inc = c.post("/api/incidents", json={}).json()["id"]
    [e] = c.post("/api/utterances", data={"incident_id": inc, "text": "gave zofren 4 mg IV"}).json()["entries"]
    assert e["drug"] == {**e["drug"], "value": "ondansetron", "raw": "zofren"}
    r = c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": []})
    assert r.status_code == 409 and "sound_alike_drug" in r.text
    high = [f["code"] for f in e["flags"] if f["severity"] == "high"]
    assert c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": [e["id"]], "acknowledged": high}).status_code == 200
    res = next(x["resource"] for x in c.get(f"/api/incidents/{inc}/bundle").json()["entry"]
               if x["resource"]["resourceType"] == "MedicationAdministration")
    assert provenance(res)["drug"]["raw"] == "zofren"  # the heard word travels with the record
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(c.get(f"/api/incidents/{inc}/note.pdf").content)).pages)
    assert "heard “zofren”" in text and "ondansetron" in text


def test_correcting_the_drug_clears_the_sound_flag(tmp_path):
    c = _client(tmp_path)
    inc = c.post("/api/incidents", json={}).json()["id"]
    [e] = c.post("/api/utterances", data={"incident_id": inc, "text": "gave kettamin 20 mg IV"}).json()["entries"]
    edited = c.post(f"/api/incidents/{inc}/entries/{e['id']}/edit",
                    json={"entry": {**e, "drug": {**e["drug"], "value": "midazolam"}}}).json()["entry"]
    assert edited["drug"]["value"] == "midazolam" and "sound_alike_drug" not in [f["code"] for f in edited["flags"]]


def test_hybrid_keeps_the_sound_flag(lexicon):
    from jatayu.extract.hybrid import HybridExtractor

    class Stub:
        def complete_json(self, system, prompt, schema):
            return {"entries": [{"drug": 1, "dose": 2, "unit": 3, "route": 4}]}

    rules = RulesExtractor(lexicon)
    [e] = HybridExtractor(lexicon, lambda: Stub(), rules).extract("gave lasicks 40 mg IV", CAP)
    assert e.drug.value == "furosemide" and "sound_alike_drug" in codes(e) and "low_confidence" not in codes(e)


def test_ui_shows_heard_word_and_did_you_mean():
    from pathlib import Path

    card = Path(__file__).resolve().parents[1].joinpath("web/src/components/EntryCard.tsx").read_text()
    assert "did you mean" in card and "heard “{heard}”" in card and "sound_alike_drug" in card


# ---- 2. junk guard -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw", [
    "BP stable 120 over 80, aspirin 300 mg PO",   # ordinary word + bare number
    "gave fresh IV, then morphine 5 mg IV",       # ordinary word + route
    "morphine 5 mg intramuskular 10 minutes ago",  # misheard route + number
    "pushed 1 mg ivpusch 2 minutes ago",          # misheard route
    "naloxone 0.4 mg, milligramms 2 more ready",  # misheard unit + number
])
def test_junk_words_are_not_unknown_drugs(lexicon, raw):
    assert all("drug_not_in_lexicon" not in codes(e) for e in ext(lexicon, raw))


@pytest.mark.parametrize("raw,name", [
    ("gave levetiracetam 500 mg IV", "levetiracetam"),   # not an English word: as before
    ("gave heparin 5000 units subcut", "heparin"),
    ("patient got candle 300 mg orally", "candle"),     # an English word WITH dose and unit: kept, flagged
])
def test_true_unknown_drugs_stay_flagged(lexicon, raw, name):
    [e] = ext(lexicon, raw)
    assert e.drug.value == name and "drug_not_in_lexicon" in codes(e)


def test_common_word_list_is_the_recognisers_vocabulary_without_lexicon_words(lexicon):
    assert {"stable", "fresh", "spring"} <= COMMON_ENGLISH and len(COMMON_ENGLISH) > 20000
    assert not COMMON_ENGLISH & {"morphine", "aspirin", "ondansetron", "levetiracetam", "buscopan"}
