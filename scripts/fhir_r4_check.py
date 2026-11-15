"""python -m scripts.fhir_r4_check --tag r8-fhir-r4-check --python <python with fhir.resources==6.5.0 (FHIR R4)>

Optional, offline: validates a FHIR-lite bundle exactly as the app emitted it (default: the round-9 example,
results/r9-fhir-pdf-example/example.json) with the FHIR R4 models of the `fhir.resources` package, run in a separate
Python so the app's environment is not touched. Reports, for the whole bundle and for each resource on its own, whether
it parses as R4 and the first errors if not. Nothing is added or patched before the check (round 8 tried a placeholder
subject; round 9 emits a real one). Our own check is still our FHIR-lite JSON Schema, run on every bundle the app builds.

What this checks: R4 structure and datatypes (required elements, cardinality, types, codes of required-binding status
fields, choice-type names, extension shape) as encoded in the fhir.resources pydantic models. What it does NOT check:
the HL7 validator's invariants beyond those models, terminology (ATC / SNOMED codes are not looked up), profiles
(no US Core or IPS), reference resolution (the patient is a logical reference, not a resource in the bundle)."""
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
    out["resources"].append({"index": i, "type": r["resourceType"], "status": r["status"], **check(r["resourceType"], r)})
print(json.dumps(out))
'''


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--bundle", type=Path, default=config.ROOT / "results/r9-fhir-pdf-example/example.json")
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    args.bundle = args.bundle.resolve()  # a relative --bundle used to crash after logging (round 10)
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
         f"`{args.bundle.relative_to(config.ROOT)}` (synthetic), checked exactly as the app emitted it: nothing added "
         "or patched. Our own check, on every bundle, is our FHIR-lite JSON Schema.", "",
         f"**Whole bundle as R4 Bundle: {'valid' if res['bundle']['valid'] else 'NOT valid'}.** "
         f"**Resources valid as R4 on their own: {valid} of {len(res['resources'])}.**", "",
         "Checked: R4 structure and datatypes as encoded in the fhir.resources models (required elements, cardinality, "
         "types, required-binding status codes, choice-type names, extension shape). Not checked: HL7 validator "
         "invariants beyond those models, terminology (ATC / SNOMED codes are not looked up), profiles (no US Core / "
         "IPS), reference resolution (the patient is a logical reference keyed by the incident, not a Patient resource).", "",
         "| # | Resource | Status | Valid R4 | First errors |", "|---|---|---|---|---|"]
    L += [f"| {r['index']} | {r['type']} | {r['status']} | {r['valid']} | {'; '.join(r['errors'][:3]) or '—'} |"
          for r in res["resources"]]
    L += ["", "Bundle errors: " + ("; ".join(res["bundle"]["errors"]) or "none")]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
