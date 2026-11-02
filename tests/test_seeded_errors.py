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


def test_not_range_checked_is_not_a_seeded_catch():
    from eval.seeded_errors import CATCH
    assert "no_reference_range" not in CATCH


def _root(tmp_path):
    root = tmp_path / "data"
    subprocess.run([sys.executable, "-m", "datagen.build", "--seed", "1234", "--per-pattern", "3", "--root", str(root)],
                   check=True, capture_output=True)
    return root


def test_harder_variant_and_range_class_split(tmp_path):
    from eval.seeded_errors import main
    root = _root(tmp_path)
    assert main(["--n", "40", "--variant", "harder", "--root", str(root), "--out", str(tmp_path / "res"), "--tag", "h"]) == 0
    m = json.loads((tmp_path / "res" / "h" / "metrics.json").read_text())
    assert set(m["by_corruption"]) == {"dose_x2", "dose_x5", "digit_slip", "mg_to_g"}
    assert set(m["by_range_class"]) <= {"cited", "illustrative", "none"}
    assert sum(v["denominator"] for v in m["by_range_class"].values()) == 40
    assert m["split"] == "dev" and m["variant"] == "harder"


def test_false_flags_are_tabulated_and_runs_logged(tmp_path):
    from eval.seeded_errors import main
    root = _root(tmp_path)
    main(["--n", "40", "--root", str(root), "--out", str(tmp_path / "res"), "--tag", "f"])
    out = tmp_path / "res" / "f"
    m = json.loads((out / "metrics.json").read_text())
    rows = [json.loads(l) for l in (out / "false_flags.jsonl").read_text().splitlines() if l]
    assert len(rows) == m["false_flag_rate"]["count"] and all(r["rules"] for r in rows)
    report = (out / "report.md").read_text()
    assert "False-flag rate" in report and "Catch rate" in report
    log = [json.loads(l) for l in (tmp_path / "res" / "run_log.jsonl").read_text().splitlines()]
    assert log[-1]["runner"] == "eval.seeded_errors" and log[-1]["split"] == "dev"


def test_digit_slip_changes_one_digit():
    from eval.seeded_errors import corrupt
    from jatayu.lexicon import Lexicon
    import random
    out = corrupt({"drug": "epinephrine", "dose_value": 0.3, "dose_unit": "mg", "route": "IM"}, "digit_slip",
                  Lexicon.load(), random.Random(1))
    assert out["dose_value"] != 0.3 and len(f"{out['dose_value']:g}") == len("0.3")


def test_wilson_interval():
    from eval.stats import wilson
    lo, hi = wilson(189, 200)
    assert 0.90 < lo < 0.92 and 0.96 < hi < 0.98
    assert wilson(0, 0) == (0.0, 0.0)


def test_test_split_runs_write_aggregates_only(tmp_path):
    from eval.seeded_errors import main
    root = _root(tmp_path)
    main(["--split", "test", "--n", "40", "--root", str(root), "--out", str(tmp_path / "res"), "--tag", "t"])
    out = tmp_path / "res" / "t"
    assert not (out / "errors.jsonl").exists() and not (out / "false_flags.jsonl").exists()
    m = json.loads((out / "metrics.json").read_text())
    assert "ci95" in m["catch_rate"] and "ci95" in m["false_flag_rate"]
    assert sum(r["count"] for r in m["miss_breakdown"]) == 40 - m["catch_rate"]["count"]
    assert all(set(r) == {"corruption", "range_class", "outcome", "count"} for r in m["miss_breakdown"])
    report = (out / "report.md").read_text()
    assert "Residual misses, new-flag definition (aggregate)" in report and "| was " not in report


def test_rerender_strips_records_from_a_test_folder(tmp_path):
    from eval.seeded_errors import main, rerender
    root = _root(tmp_path)
    main(["--split", "dev", "--n", "40", "--root", str(root), "--out", str(tmp_path / "res"), "--tag", "d"])
    out = tmp_path / "res" / "d"
    m = json.loads((out / "metrics.json").read_text()); m["split"] = "test"
    (out / "metrics.json").write_text(json.dumps(m))
    rerender(out)
    m2 = json.loads((out / "metrics.json").read_text())
    assert "miss_breakdown" in m2 and "ci95" in m2["catch_rate"] and not (out / "errors.jsonl").exists()


def test_new_flag_definition_needs_a_flag_the_base_did_not_have():
    from eval.seeded_errors import caught
    assert caught(set(), {"dose_out_of_range"}) == (True, True)  # clean base: both definitions agree
    assert caught({"dose_out_of_range"}, {"dose_out_of_range"}) == (True, False)  # same flag as before corruption
    assert caught({"dose_below_range"}, {"dose_out_of_range"}) == (True, True)  # a different, new flag
    assert caught(set(), {"weight_based_dose", "no_reference_range"}) == (False, False)  # informational only


def test_report_shows_both_definitions_and_base_already_flagged(tmp_path):
    from eval.seeded_errors import main
    root = _root(tmp_path)
    assert main(["--n", "40", "--root", str(root), "--out", str(tmp_path / "res"), "--tag", "d"]) == 0
    m = json.loads((tmp_path / "res" / "d" / "metrics.json").read_text())
    assert m["catch_rate_new_flag"]["count"] <= m["catch_rate"]["count"]
    assert m["base_already_flagged"]["count"] == m["false_flag_rate"]["count"]
    assert set(m["by_corruption_new_flag"]) == set(m["by_corruption"])
    report = (tmp_path / "res" / "d" / "report.md").read_text()
    assert "new-flag definition" in report and "existing definition" in report and "already flagged" in report
