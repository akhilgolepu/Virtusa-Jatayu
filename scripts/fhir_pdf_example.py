"""python -m scripts.fhir_pdf_example --tag r7-fhir-pdf-example

One synthetic incident through the real API (typed sentences, default extractor): the FHIR-lite bundle JSON
(schema-validated) and the PDF note rendered from that same bundle, saved side by side with a text extract of the PDF
and the checks: schema valid, every bundle entry appears in the PDF, the drug that was not given is `not-done`."""
from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from pathlib import Path

from eval.runlog import log_run
from jatayu import config

SENTENCES = ["gave 0.3 mg adrenaline IM two minutes ago", "aspirin 300 mg PO at 10 40", "patient allergic to morphine",
             "blood glucose 3.2 mmol", "started CPR", "ondansetron 4, no sorry, 2 mg IV",
             # round 9: a drug matched by sound, a drug not in the lexicon, a concentration, a procedure not done
             "gave lasicks 40 mg IV", "gave levetiracetam 500 mg IV", "atropine 0.6 mg per ml", "unable to get IV access"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from fastapi.testclient import TestClient
    from pypdf import PdfReader

    from jatayu.api import create_app
    from jatayu.output.fhir import clinical, provenance, transcripts, validate_bundle

    start = log_run(args.out, runner="scripts.fhir_pdf_example", split="none (synthetic example)", tag=args.tag)
    tmp = Path(tempfile.mkdtemp())
    c = TestClient(create_app(db_path=tmp / "j.sqlite", audio_dir=tmp / "a", recordings_dir=tmp / "r"))
    inc = c.post("/api/incidents", json={"label": "Synthetic example — not a real patient"}).json()["id"]
    ids = []
    for s in SENTENCES:
        ids += [e["id"] for e in c.post("/api/utterances", data={"incident_id": inc, "text": s}).json()["entries"]]
    bundle = c.get(f"/api/incidents/{inc}/bundle").json()
    by_drug = {r.get("medicationCodeableConcept", r.get("code", {})).get("text"): provenance(r)["entry_id"]
               for r in clinical(bundle)}
    to_confirm = [by_drug["aspirin"], by_drug["morphine"]]  # one given, one not given (acknowledging its high flag)
    ack = sorted({f["code"] for r in clinical(bundle) if provenance(r)["entry_id"] in to_confirm
                  for f in provenance(r)["flags"] if f["severity"] == "high"})
    c.post(f"/api/incidents/{inc}/confirm", json={"entry_ids": to_confirm, "acknowledged": ack})
    bundle = c.get(f"/api/incidents/{inc}/bundle").json()
    validate_bundle(bundle)
    pdf = c.get(f"/api/incidents/{inc}/note.pdf").content
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)

    rows, checks = [], {"schema_valid": True}
    for r in clinical(bundle):
        name = r.get("medicationCodeableConcept", r.get("code", {})).get("text")
        dose = r.get("dosage", {}).get("dose")
        dose_s = f"{dose['value']:g} {dose.get('unit', '?')}" if dose else ""
        heard = (provenance(r).get("drug") or {}).get("raw")
        rows.append({"item": name, "heard": heard, "fhir_status": r["status"], "review_status": provenance(r)["review_status"],
                     "dose": dose_s, "flags": sorted({f["code"] for f in provenance(r)["flags"] if f["severity"] == "high"}),
                     "in_pdf": name in text and (dose_s in text if dose_s else True)})
    checks["every_bundle_entry_in_pdf"] = all(r["in_pdf"] for r in rows)
    morphine = next(r for r in rows if r["item"] == "morphine")
    checks["morphine_not_given_status"] = morphine["fhir_status"]
    checks["morphine_confirmed_yet_not_done"] = morphine["review_status"] == "confirmed" and morphine["fhir_status"] == "not-done"
    checks["pdf_says_not_given"] = "NOT GIVEN" in text
    checks["glucose_reading_status"] = next(r["fhir_status"] for r in rows if r["item"] == "dextrose")
    checks["every_resource_has_subject"] = all("subject" in r for r in clinical(bundle))
    checks["transcripts_as_communications"] = len(transcripts(bundle)) == len(SENTENCES)
    checks["sound_alike_heard_word_in_pdf"] = "heard “lasicks”" in text
    checks["unknown_drug_kept"] = any(r["item"] == "levetiracetam" and "drug_not_in_lexicon" in r["flags"] for r in rows)
    checks["concentration_has_no_dose"] = any(r["item"] == "atropine" and not r["dose"] for r in rows)
    checks["procedure_not_done"] = any(r["item"] == "iv cannulation" and r["fhir_status"] == "not-done" for r in rows)
    checks["no_completed_not_given"] = not any(r["fhir_status"] == "completed" and r["item"] == "morphine" for r in rows)

    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "example.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    (out / "example.pdf").write_bytes(pdf)
    (out / "example_pdf.txt").write_text(text + "\n", encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "checks": checks, "rows": rows}, indent=2) + "\n")
    L = [f"# FHIR-lite JSON and the PDF made from it (`{args.tag}`, commit `{start['commit']}`)", "",
         "Synthetic incident, typed sentences: " + " · ".join(f"“{s}”" for s in SENTENCES) + ". Aspirin and the morphine "
         "allergy were confirmed (the allergy's high flag acknowledged); the rest stay drafts.", "",
         "Files: `example.json` (the bundle, schema-validated), `example.pdf` (rendered from that bundle), "
         "`example_pdf.txt` (text extracted from the PDF).", "",
         "| Entry | Heard | FHIR status | Review status | Dose | High flags | Found in the PDF |", "|---|---|---|---|---|---|---|"]
    L += [f"| {r['item']} | {r['heard'] or '—'} | {r['fhir_status']} | {r['review_status']} | {r['dose'] or '—'} | "
          f"{', '.join(r['flags']) or '—'} | {r['in_pdf']} |" for r in rows]
    L += ["", "| Check | Result |", "|---|---|"] + [f"| {k} | {v} |" for k, v in checks.items()]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=1))
    return 0 if all(v not in (False,) for v in checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
