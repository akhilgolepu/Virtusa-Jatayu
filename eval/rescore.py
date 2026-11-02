"""python -m eval.rescore results/<tag> [...]

Offline re-score of finished pipeline runs from their own errors.jsonl (no GPU, no re-run, no run-log entry: nothing
is re-evaluated). Writes results/<tag>/rescored_dangerous.json with the strict (headline) and lenient dangerous-error
counts; the run's original metrics.json is left untouched."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.metrics import NON_CATCHING, NON_CATCHING_LENIENT, is_dangerous


def rescore(folder: Path) -> dict:
    m = json.loads((folder / "metrics.json").read_text())["metrics"]
    rows = [json.loads(l) for l in (folder / "errors.jsonl").read_text().splitlines() if l]
    given = [r for r in rows if r.get("kind") == "wrong" and r.get("context") == "given"
             and "drug" in (r.get("expected") or {})]
    den = m["dangerous_error"]["denominator"]
    strict = sum(is_dangerous(r["wrong_fields"], set(r["flags"]), NON_CATCHING) for r in given)
    lenient = sum(is_dangerous(r["wrong_fields"], set(r["flags"]), NON_CATCHING_LENIENT) for r in given)
    out = {"source": "errors.jsonl (offline re-score, no re-run)",
           "as_recorded": m["dangerous_error"],
           "strict": {"count": strict, "denominator": den, "rate": round(strict / den, 4) if den else 0.0,
                      "non_catching": sorted(NON_CATCHING)},
           "lenient": {"count": lenient, "denominator": den, "rate": round(lenient / den, 4) if den else 0.0,
                       "non_catching": sorted(NON_CATCHING_LENIENT)}}
    (folder / "rescored_dangerous.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def main(argv: list[str] | None = None) -> int:
    for arg in argv if argv is not None else sys.argv[1:]:
        o = rescore(Path(arg))
        print(f"{arg}: recorded {o['as_recorded']['count']} · strict {o['strict']['count']} · lenient "
              f"{o['lenient']['count']} / {o['strict']['denominator']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
