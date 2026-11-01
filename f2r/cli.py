"""f2r — Field-to-Record CLI.

  python -m f2r.cli add "gave 0.3 mg adrenaline IM"      # sentence -> checked record (JSON), appended to the chain
  python -m f2r.cli verify                               # exit 1 if the chain is broken
  python -m f2r.cli eval --split dev --tag m3-dev        # writes results/<tag>/metrics.json, report.md, errors.jsonl
  python -m f2r.cli setup-check                          # Gate G0 checks -> results/g0/setup_check.json

Decision-support demo, not a clinical device.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from jatayu import config

CLI_INCIDENT_LABEL = "f2r-cli"


def _pipeline(db: Path, extractor: str):
    from jatayu.audit import AuditLog
    from jatayu.extract.hybrid import HybridExtractor
    from jatayu.extract.llm import LlmExtractor
    from jatayu.extract.rules import RulesExtractor
    from jatayu.lexicon import Lexicon
    from jatayu.llm import LlmRunner
    from jatayu.pipeline import Pipeline
    from jatayu.validate import validate_all

    lex = Lexicon.load()
    rules = RulesExtractor(lex)
    runner = LlmRunner(config.LLM_MODEL_PATH)
    chosen = {"rules": rules, "llm": LlmExtractor(lex, lambda: runner),
              "hybrid": HybridExtractor(lex, lambda: runner, rules)}[extractor]
    return Pipeline(lex, chosen, AuditLog(db), validator=lambda e, h: validate_all(e, lex, h))


def cmd_add(args) -> int:
    from jatayu.incident import IncidentStore, incident_state

    store = IncidentStore(args.db)
    incident = args.incident or next((i["id"] for i in store.list() if i["label"] == CLI_INCIDENT_LABEL), None) \
        or store.create(CLI_INCIDENT_LABEL)["id"]
    pipe = _pipeline(args.db, args.extractor)
    history = incident_state(pipe.audit, incident).current_entries()
    result = pipe.run(incident, text=args.text, history=history)
    print(result.model_dump_json(indent=2, exclude={"bundle"}))
    return 0


def cmd_verify(args) -> int:
    from jatayu.audit import AuditLog

    v = AuditLog(args.db).verify()
    print(json.dumps(asdict(v)))
    return 0 if v.ok else 1


def cmd_eval(args) -> int:
    from eval.run import main as run_eval

    return run_eval(args.rest)


def cmd_setup_check(args) -> int:
    from scripts.setup_check import main as setup

    return setup(args.rest)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="f2r", description="Field-to-Record CLI (decision-support demo, not a clinical device)")
    ap.add_argument("--db", type=Path, default=config.DB_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="extract + validate a typed sentence and append it to the chain")
    a.add_argument("text")
    a.add_argument("--incident")
    a.add_argument("--extractor", choices=["rules", "llm", "hybrid"], default=config.DEFAULT_EXTRACTOR)
    a.set_defaults(fn=cmd_add)
    sub.add_parser("verify", help="verify the hash chain").set_defaults(fn=cmd_verify)
    e = sub.add_parser("eval", help="run the evaluation harness (see python -m eval.run --help)", add_help=False)
    e.add_argument("rest", nargs=argparse.REMAINDER)
    e.set_defaults(fn=cmd_eval)
    s = sub.add_parser("setup-check", help="Gate G0 checks", add_help=False)
    s.add_argument("rest", nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_setup_check)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
