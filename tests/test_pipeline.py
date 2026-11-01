from pathlib import Path

import pytest

from jatayu.asr import Transcriber
from jatayu.audit import AuditLog, canonical_json, sha256_hex
from jatayu.extract.rules import RulesExtractor
from jatayu.pipeline import Pipeline, draft_payload


def test_text_run_logs_verified_row(lexicon, tmp_db, tmp_path):
    p = Pipeline(lexicon, RulesExtractor(lexicon), AuditLog(tmp_db), audio_dir=tmp_path)
    r = p.run("inc1", text="pushed 4 mg ondansetron IV")
    assert r.entries[0].drug.value == "ondansetron"
    row = AuditLog(tmp_db).rows("inc1")[-1]
    assert row.seq == r.audit_seq
    assert row.json_sha256 == sha256_hex(canonical_json(draft_payload(r.utterance, r.entries, r.bundle)))
    assert AuditLog(tmp_db).verify().ok


def test_empty_text_still_logged(lexicon, tmp_db, tmp_path):
    r = Pipeline(lexicon, RulesExtractor(lexicon), AuditLog(tmp_db), audio_dir=tmp_path).run("inc1", text="")
    assert r.entries == [] and "no speech detected" in r.warnings and r.audit_seq == 1


def test_requires_exactly_one_input(lexicon, tmp_db):
    p = Pipeline(lexicon, RulesExtractor(lexicon), AuditLog(tmp_db))
    with pytest.raises(ValueError):
        p.run("inc1")
    with pytest.raises(ValueError):
        p.run("inc1", text="x", audio=b"y")


@pytest.mark.models
def test_audio_end_to_end_offline(lexicon, tmp_db, tmp_path, no_network):
    p = Pipeline(lexicon, RulesExtractor(lexicon), AuditLog(tmp_db), Transcriber(lexicon=lexicon), audio_dir=tmp_path)
    r = p.run("inc1", audio=Path("tests/fixtures/adrenaline.wav").read_bytes())
    [e] = r.entries
    assert e.drug.value == "epinephrine" and e.dose_value.value == 0.3 and e.route.value == "IM"
    assert (tmp_path / f"{r.utterance.audio_sha256}.wav").exists()
    assert AuditLog(tmp_db).verify().ok
