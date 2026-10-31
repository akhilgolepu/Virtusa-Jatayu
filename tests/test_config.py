import os
import socket

import pytest

from jatayu import config


def test_offline_env_set_on_import():
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_disclaimer_exact():
    assert config.DISCLAIMER == "Decision-support demo, not a clinical device."


def test_paths_are_under_repo():
    assert config.ASR_MODEL_DIR == config.ROOT / "models/asr/faster-whisper-small.en"
    assert config.DB_PATH.parent == config.DATA_DIR


def test_no_network_fixture_blocks(no_network):
    with pytest.raises(OSError, match="network disabled"):
        socket.create_connection(("1.1.1.1", 80), timeout=1)
