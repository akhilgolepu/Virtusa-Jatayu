import re

import pytest
from fastapi.testclient import TestClient

from jatayu.api import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=tmp_path / "t.sqlite", audio_dir=tmp_path / "audio"))


def _incident(client):
    return client.post("/api/incidents", json={}).json()["id"]


def test_text_flow_and_verify(client):
    inc = _incident(client)
    r = client.post("/api/utterances", data={"incident_id": inc, "text": "aspirin 300 mg PO"})
    assert r.status_code == 200 and r.json()["entries"][0]["drug"]["value"] == "aspirin"
    assert client.get("/api/audit/verify").json()["ok"] is True
    assert [row["seq"] for row in client.get(f"/api/audit?incident_id={inc}").json()] == [1]


def test_blank_text_422(client):
    inc = _incident(client)
    assert client.post("/api/utterances", data={"incident_id": inc, "text": "   "}).status_code == 422


def test_unknown_incident_404(client):
    assert client.post("/api/utterances", data={"incident_id": "nope", "text": "aspirin"}).status_code == 404


def test_bad_audio_400(client):
    inc = _incident(client)
    r = client.post("/api/utterances", data={"incident_id": inc}, files={"audio": ("x.webm", b"junk", "audio/webm")})
    assert r.status_code == 400 and r.json()["detail"] == "could not decode audio"


def test_page_has_no_external_urls(client):
    html = client.get("/").text
    assert "Decision-support demo, not a clinical device." in html
    assert not re.search(r"(src|href)=\"https?://", html)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["offline"] is True
