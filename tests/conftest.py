import socket

import pytest



def pytest_collection_modifyitems(config, items):
    from jatayu import config as jconfig

    if jconfig.ASR_MODEL_DIR.exists():
        return
    skip = pytest.mark.skip(reason=f"model not downloaded: {jconfig.ASR_MODEL_DIR}")
    for item in items:
        if "models" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def no_network(monkeypatch):
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        if self.family == socket.AF_UNIX:
            return real_connect(self, address)
        raise OSError("network disabled in tests")

    def guarded_create_connection(*args, **kwargs):
        raise OSError("network disabled in tests")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "audit.sqlite"


@pytest.fixture(scope="session")
def lexicon():
    from jatayu.lexicon import Lexicon

    return Lexicon.load()


CAPTURE = __import__("datetime").datetime(2026, 10, 31, 10, 45).astimezone()


@pytest.fixture
def sample_utterance():
    from jatayu.models import Utterance

    return Utterance(incident_id="inc-test", capture_time=CAPTURE,
                     raw_transcript="gave 0.3 mg adrenaline IM two mins ago")


@pytest.fixture
def sample_entries(lexicon, sample_utterance):
    from jatayu.extract.rules import RulesExtractor

    return RulesExtractor(lexicon).extract(sample_utterance.raw_transcript, CAPTURE)


@pytest.fixture
def entry_missing_dose(lexicon):
    from jatayu.extract.rules import RulesExtractor

    [entry] = RulesExtractor(lexicon).extract("gave aspirin", CAPTURE)
    return entry
