"""python -m scripts.fhir_r4_check --tag r8-fhir-r4-check --python <python with fhir.resources==6.5.0 (FHIR R4)>

Optional, offline: validates our FHIR-lite example bundle (results/r7-fhir-pdf-example/example.json) with the
official FHIR R4 models of the `fhir.resources` package, run in a separate Python so the app's environment is not
touched. Reports, per resource and for the whole bundle, whether it is valid R4 and the first errors if not. Our own
check remains our FHIR-lite JSON Schema; this only measures how far FHIR-lite is from strict R4."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from eval.runlog import log_run
from jatayu import config

CHECK = r'''
import json, sys
from pydantic import ValidationError
from fhir.resources import construct_fhir_element
bundle = json.load(open(sys.argv[1]))
out = {"bundle": None, "resources": []}
def check(kind, obj):
    try:
        construct_fhir_element(kind, obj)
        return {"valid": True, "errors": []}
    except ValidationError as e:
        return {"valid": False, "errors": [f"{'.'.join(str(p) for p in er['loc'])}: {er['msg']}" for er in e.errors()][:8]}
out["bundle"] = check("Bundle", bundle)
for i, e in enumerate(bundle["entry"]):
    r = e["resource"]
    with_subject = check(r["resourceType"], {**r, "subject": {"display": "unidentified patient (placeholder)"}})
    out["resources"].append({"index": i, "type": r["resourceType"], "status": r["status"], **check(r["resourceType"], r),
                             "valid_with_placeholder_subject": with_subject["valid"],
                             "errors_with_placeholder_subject": with_subject["errors"]})
print(json.dumps(out))
'''


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--bundle", type=Path, default=config.ROOT / "results/r7-fhir-pdf-example/example.json")
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    start = log_run(args.out, runner="scripts.fhir_r4_check", split="none (synthetic example)", tag=args.tag)
    ver = subprocess.run([args.python, "-c", "import fhir.resources as f, pydantic; print(f.__version__, pydantic.VERSION)"],
                         capture_output=True, text=True).stdout.strip()
    res = json.loads(subprocess.run([args.python, "-c", CHECK, str(args.bundle)], capture_output=True, text=True,
                                    check=True).stdout)
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "fhir_resources_pydantic": ver,
                                                  "bundle_file": str(args.bundle.relative_to(config.ROOT)), **res}, indent=2) + "\n")
    valid = sum(r["valid"] for r in res["resources"])
    L = [f"# Strict FHIR R4 check of the FHIR-lite example (`{args.tag}`, commit `{start['commit']}`)", "",
         f"`fhir.resources` / pydantic: {ver} (R4 models), in a separate virtual environment. Bundle: "
         f"`{args.bundle.relative_to(config.ROOT)}` (synthetic). Our own check is our FHIR-lite JSON Schema; this "
         "only shows how far FHIR-lite is from strict R4.", "",
         f"**Whole bundle as R4 Bundle: {'valid' if res['bundle']['valid'] else 'NOT valid'}.** "
         f"**Resources valid as R4 on their own: {valid} of {len(res['resources'])}.**", "",
         "| # | Resource | Status | Valid R4 | First errors | Valid with a placeholder `subject` added |",
         "|---|---|---|---|---|---|"]
    L += [f"| {r['index']} | {r['type']} | {r['status']} | {r['valid']} | {'; '.join(r['errors'][:3]) or '—'} | "
          f"{r['valid_with_placeholder_subject']} {'; '.join(r['errors_with_placeholder_subject'][:2])} |"
          for r in res["resources"]]
    L += ["", "Bundle errors: " + ("; ".join(res["bundle"]["errors"]) or "none")]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
