import json

from f2r.cli import main


def test_add_and_verify(tmp_path, capsys):
    db = tmp_path / "f.sqlite"
    assert main(["--db", str(db), "add", "gave 0.3 mg adrenaline IM two mins ago", "--extractor", "rules"]) == 0
    out = json.loads(capsys.readouterr().out)
    e = out["entries"][0]
    assert (e["drug"]["value"], e["dose_value"]["value"], e["time_source"]) == ("epinephrine", 0.3, "spoken")
    assert main(["--db", str(db), "verify"]) == 0
    assert '"ok": true' in capsys.readouterr().out


def test_verify_fails_after_tamper(tmp_path, capsys):
    import sqlite3
    db = tmp_path / "f.sqlite"
    main(["--db", str(db), "add", "aspirin 300 mg PO", "--extractor", "rules"])
    con = sqlite3.connect(db)
    con.execute("DROP TRIGGER audit_no_update")
    con.execute("UPDATE audit_log SET payload_json = replace(payload_json, '300', '3000')")
    con.commit()
    capsys.readouterr()
    assert main(["--db", str(db), "verify"]) == 1
    assert '"first_bad_seq": 1' in capsys.readouterr().out


def test_add_reuses_one_cli_incident(tmp_path, capsys):
    db = tmp_path / "f.sqlite"
    main(["--db", str(db), "add", "aspirin 300 mg PO", "--extractor", "rules"])
    a = json.loads(capsys.readouterr().out)["utterance"]["incident_id"]
    main(["--db", str(db), "add", "4 mg ondansetron IV", "--extractor", "rules"])
    assert json.loads(capsys.readouterr().out)["utterance"]["incident_id"] == a
