"""Round 9 launcher: the pre-flight fails loudly and nothing is started when any check fails."""
import subprocess

from scripts import start_demo


def _all_pass(monkeypatch, **fail):
    for name in ("check_gpu", "check_models", "check_config", "check_offline_env", "check_asr", "check_voice",
                 "check_audit"):
        monkeypatch.setattr(start_demo, name, lambda n=name: {"pass": n not in fail, "detail": fail.get(n, "ok")})
    monkeypatch.setattr(start_demo, "check_port", lambda port: {"pass": True, "detail": "free"})


def test_a_failing_check_stops_the_demo(monkeypatch, capsys):
    _all_pass(monkeypatch, check_asr="whisper not on the GPU")
    started = []
    real = subprocess.Popen
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: started.append(a) if "uvicorn" in str(a) else real(*a, **k))
    assert start_demo.main(["--no-browser"]) == 1
    out = capsys.readouterr().out
    assert "FAIL  ASR" in out and "PRE-FLIGHT FAILED: asr" in out and "NOT started" in out
    assert started == []  # no server, no browser


def test_check_only_passes_without_starting(monkeypatch, capsys, tmp_path):
    _all_pass(monkeypatch)
    real = subprocess.Popen

    def popen(*a, **k):
        assert "uvicorn" not in str(a), "server started"
        return real(*a, **k)

    monkeypatch.setattr(subprocess, "Popen", popen)
    assert start_demo.main(["--check-only", "--out", str(tmp_path / "p.json")]) == 0
    assert '"all_pass": true' in (tmp_path / "p.json").read_text()


def test_config_check_refuses_llm_only_and_offline_check_needs_env(monkeypatch):
    from jatayu import config
    monkeypatch.setattr(config, "EXPERIMENTAL", True)
    assert not start_demo.check_config()["pass"]
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    assert not start_demo.check_offline_env()["pass"]


def test_network_is_blocked_inside_the_checks():
    import socket

    import pytest
    with start_demo.no_network():
        with pytest.raises(OSError, match="blocked"):
            socket.create_connection(("1.1.1.1", 443), timeout=2)
