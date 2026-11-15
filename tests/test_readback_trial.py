"""Round 12, item 3: the read-back test harness, exercised with DUMMY testers only (no human data)."""
import io
import json
import wave
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from eval.stats import wilson
from jatayu.readback_trial import MIX, TrialStore, aggregate, create_readback_app, pool, trials_for

KEY_WORDS = ("correct", "wrong", "error", "type", "said", "key", "flag", "count", "mix")


def _silence(record):  # the read-back voice is tested separately (models); here any WAV will do
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000), w.writeframes(b"\x00\x00" * 1600)
    return buf.getvalue()


@pytest.fixture
def client(tmp_path):
    return TestClient(create_readback_app(tmp_path / "store", synth=_silence)), tmp_path / "store"


def _assert_no_key(payload):
    """Nothing the page receives may name a trial's type, the mix, the said-vs-recorded key, or a count."""
    text = json.dumps(payload).lower()
    for w in KEY_WORDS:
        assert f'"{w}' not in text, w  # no key of that name
    if payload.get("trial"):
        assert set(payload) == {"done", "trial"} and set(payload["trial"]) == {"token", "say", "record"}
        assert set(payload["trial"]["record"]) == {"drug", "dose", "unit", "route", "unit_words", "route_words"}


def _run(c, tester, policy):
    """A dummy tester answering every trial with policy(say, record) -> 'confirm' | 'needs_correction'."""
    state = c.post("/api/readback-test/session", json={"tester_id": tester}).json()
    seen = 0
    while not state["done"]:
        _assert_no_key(state)
        t = state["trial"]
        state = c.post("/api/readback-test/answer", json={"tester_id": tester, "token": t["token"],
                                                           "answer": policy(t["say"], t["record"]), "ms": 1500}).json()
        seen += 1
    return seen


# ---- trials ------------------------------------------------------------------------------------------------------
def test_each_tester_gets_24_records_in_the_stated_mix_and_a_seeded_order():
    a, b = trials_for("T01"), trials_for("T02")
    assert len(a) == 24 and Counter(t["type"] for t in a) == Counter(MIX)
    assert trials_for("T01") == a  # same code -> same records, same order
    assert [t["record"] for t in a] != [t["record"] for t in b]  # another code -> another set and order
    assert len({t["said"]["drug"] for t in a}) == 24  # one record per drug


def test_every_wrong_record_differs_in_exactly_its_field_and_stays_valid(lexicon):
    from jatayu.readback_trial import _clean
    field = {"wrong_drug": "drug", "wrong_dose": "dose", "wrong_route": "route"}
    for tester in ("T01", "T02", "T03", "AB123"):
        for t in trials_for(tester):
            r, s = t["record"], t["said"]
            diff = {k for k in r if r[k] != s[k]}
            assert diff == (set() if t["type"] == "correct" else {field[t["type"]]})
            assert _clean(lexicon, r["drug"], r["dose"], r["unit"], r["route"])  # no flag would fire on it
    assert len(pool()) > 100


@pytest.mark.parametrize("bad", ["Akhil", "akhil k", "t01", "Dr Rao", "", "T1", "TOOLONG01"])
def test_only_anonymous_codes_are_accepted(client, bad):
    c, _ = client
    assert c.post("/api/readback-test/session", json={"tester_id": bad}).status_code == 422


# ---- the page never gets the key ---------------------------------------------------------------------------------
def test_the_page_and_every_response_carry_no_key(client):
    c, _ = client
    html = c.get("/readback-test").text
    for w in ("wrong_drug", "wrong_dose", "wrong_route", "flag", "correct record", "of 24"):
        assert w not in html
    assert "http://" not in html and "https://" not in html  # offline: nothing external
    assert _run(c, "T01", lambda say, rec: "confirm") == 24


def test_answers_must_follow_the_order_and_tokens_are_opaque(client):
    c, _ = client
    first = c.post("/api/readback-test/session", json={"tester_id": "T05"}).json()["trial"]
    assert len(first["token"]) == 24 and all(ch in "0123456789abcdef" for ch in first["token"])
    r = c.post("/api/readback-test/answer", json={"tester_id": "T05", "token": "0" * 24, "answer": "confirm"})
    assert r.status_code == 409
    assert c.post("/api/readback-test/answer", json={"tester_id": "T05", "token": first["token"],
                                                     "answer": "maybe"}).status_code == 422
    # resuming with the same code continues at the same trial
    again = c.post("/api/readback-test/session", json={"tester_id": "T05"}).json()["trial"]
    assert again["token"] == first["token"]


def test_store_holds_no_names_audio_or_transcripts(client):
    c, store = client
    _run(c, "T07", lambda say, rec: "confirm")
    c.get(f"/api/readback-test/audio/T07/{trials_for('T07') and TrialStore(store).sessions()[0]['trials'][0]['token']}")
    files = sorted(p.relative_to(store).as_posix() for p in store.rglob("*") if p.is_file())
    assert files == ["responses.jsonl", "sessions/T07.json"]  # no audio file anywhere
    rows = [json.loads(l) for l in (store / "responses.jsonl").read_text().splitlines()]
    assert len(rows) == 24 and set(rows[0]) == {"tester", "token", "answer", "ms", "at"}


# ---- aggregate ---------------------------------------------------------------------------------------------------
def test_aggregate_with_dummy_testers_and_wilson_intervals(client):
    c, store = client
    _run(c, "T01", lambda say, rec: "confirm")                       # never flags anything
    _run(c, "T02", lambda say, rec: "needs_correction")              # flags everything

    def drug_checker(say, rec):                                       # catches only a wrong drug
        return "confirm" if rec["drug"].lower() in say.lower() else "needs_correction"
    _run(c, "T03", drug_checker)
    _run(c, "T04", lambda say, rec: "confirm")
    c.post("/api/readback-test/session", json={"tester_id": "T09"})  # started, never answered
    agg = aggregate(TrialStore(store))
    assert agg["testers"] == 5 and agg["testers_complete"] == 4
    cr = agg["catch_rate"]
    assert (cr["wrong_drug"]["count"], cr["wrong_drug"]["denominator"]) == (2 * 6, 4 * 6)  # T02 + T03
    assert (cr["wrong_dose"]["count"], cr["wrong_dose"]["denominator"]) == (4, 16)        # T02 only
    assert (cr["wrong_route"]["count"], cr["wrong_route"]["denominator"]) == (4, 16)
    fa = agg["false_alarm_rate"]
    assert (fa["count"], fa["denominator"]) == (10, 40)                                    # T02 only
    assert tuple(fa["wilson95"]) == pytest.approx(wilson(10, 40))
    assert tuple(cr["wrong_drug"]["wilson95"]) == pytest.approx(wilson(12, 24))


def test_report_is_aggregate_only(client, tmp_path):
    c, store = client
    _run(c, "T01", lambda say, rec: "needs_correction")
    from eval.readback_test_report import main
    assert main(["--tag", "dummy-rb", "--store", str(store), "--label", "DUMMY testers",
                 "--out", str(tmp_path / "results")]) == 0
    text = (tmp_path / "results" / "dummy-rb" / "report.md").read_text()
    assert "DUMMY testers" in text and "T01" not in text and "Gave" not in text


@pytest.mark.models
def test_the_audio_is_the_real_read_back(tmp_path):
    c = TestClient(create_readback_app(tmp_path / "store"))
    t = c.post("/api/readback-test/session", json={"tester_id": "T11"}).json()["trial"]
    wav = c.get(f"/api/readback-test/audio/T11/{t['token']}").content
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getframerate() == 16000 and w.getnframes() > 16000  # more than a second of speech
    assert not list((tmp_path / "store").rglob("*.wav"))
