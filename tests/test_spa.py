import re

import pytest
from fastapi.testclient import TestClient

from jatayu import config
from jatayu.api import create_app

DIST = config.ROOT / "jatayu/web/dist/index.html"


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=tmp_path / "j.sqlite", audio_dir=tmp_path / "a", recordings_dir=tmp_path / "r"))


def test_lexicon_endpoint(client):
    lex = client.get("/api/lexicon").json()
    epi = next(d for d in lex["drugs"] if d["name"] == "epinephrine")
    assert "IM" in epi["routes"] and "mg" in epi["units"] and "adrenaline" in epi["aliases"]
    assert "cpr" in lex["procedures"] and "IV" in lex["routes"]


@pytest.mark.skipif(not DIST.exists(), reason="frontend not built")
@pytest.mark.parametrize("path", ["/", "/incidents", "/audit", "/record", "/incidents/abc"])
def test_spa_routes_serve_the_built_app_offline(client, path):
    r = client.get(path)
    assert r.status_code == 200 and '<div id="app">' in r.text
    assert not re.search(r"(src|href)=\"https?://", r.text)


@pytest.mark.skipif(not DIST.exists(), reason="frontend not built")
def test_assets_and_fonts_are_local(client):
    html = client.get("/").text
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
    assert assets and all(client.get(a).status_code == 200 for a in assets)
    css = next(client.get(a).text for a in assets if a.endswith(".css"))
    assert "woff2" in css and "fonts.googleapis" not in css


def test_skeleton_page_still_available(client):
    assert "Decision-support demo" in client.get("/skeleton").text
