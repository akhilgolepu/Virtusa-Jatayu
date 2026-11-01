import json
import subprocess
import sys


def test_seeded_errors_writes_rates(tmp_path):
    root = tmp_path / "data"
    subprocess.run([sys.executable, "-m", "datagen.build", "--seed", "1234", "--per-pattern", "3", "--root", str(root)],
                   check=True, capture_output=True)
    from eval.seeded_errors import main
    assert main(["--n", "40", "--root", str(root), "--out", str(tmp_path / "res"), "--tag", "s"]) == 0
    m = json.loads((tmp_path / "res" / "s" / "metrics.json").read_text())
    assert m["n"] == 40 and set(m["by_corruption"]) == {"dose_x10", "dose_div10", "mg_mcg_swap", "wrong_route"}
    assert 0 <= m["catch_rate"]["rate"] <= 1 and "false_flag_rate" in m
    assert sum(v["denominator"] for v in m["by_corruption"].values()) == 40


def test_corruptions_change_the_record():
    from eval.seeded_errors import corrupt
    from jatayu.lexicon import Lexicon
    lex = Lexicon.load()
    base = {"drug": "epinephrine", "dose_value": 0.3, "dose_unit": "mg", "route": "IM"}
    assert corrupt(base, "dose_x10", lex)["dose_value"] == 3.0
    assert corrupt(base, "mg_mcg_swap", lex)["dose_unit"] == "mcg"
    assert corrupt(base, "wrong_route", lex)["route"] not in lex.drug("epinephrine").routes
