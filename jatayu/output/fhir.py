"""FHIR-lite Bundle: MedicationAdministration- and Procedure-style resources with span provenance."""
from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

import jsonschema

from jatayu.config import DISCLAIMER
from jatayu.lexicon import Lexicon
from jatayu.models import Entry, Field, MedicationEntry, ProcedureEntry, Utterance

ATC = "http://www.whocc.no/atc"
SNOMED = "http://snomed.info/sct"


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _prov(entry: Entry, names: tuple[str, ...]) -> list[dict]:
    record = {}
    for name in names:
        f: Field | None = getattr(entry, name)
        if f is not None:
            record[name] = {"span": list(f.span) if f.span else None, "confidence": f.confidence, "source": f.source}
    record["flags"] = [fl.model_dump() for fl in entry.flags]
    return [{"url": "urn:jatayu:provenance", "valueString": _canonical(record)}]


def _medication(e: MedicationEntry, lexicon: Lexicon) -> dict:
    res = {
        "resourceType": "MedicationAdministration",
        "status": "in-progress",
        "medicationCodeableConcept": {"text": e.drug.value,
                                      "coding": [{"system": ATC, "code": lexicon.drug(e.drug.value).atc}]},
        "effectiveDateTime": e.time.value.isoformat(),
    }
    dosage = {}
    if e.route.value is not None:
        dosage["route"] = {"text": e.route.value}
    if e.dose_value.value is not None:
        dosage["dose"] = {"value": e.dose_value.value}
        if e.dose_unit.value is not None:
            dosage["dose"]["unit"] = e.dose_unit.value
    if dosage:
        res["dosage"] = dosage
    res["extension"] = _prov(e, ("drug", "dose_value", "dose_unit", "route", "time"))
    return res


def _procedure(e: ProcedureEntry, lexicon: Lexicon) -> dict:
    code = {"text": e.procedure.value}
    snomed = lexicon.procedure(e.procedure.value).snomed
    if snomed:
        code["coding"] = [{"system": SNOMED, "code": snomed}]
    res = {"resourceType": "Procedure", "status": "in-progress", "code": code,
           "performedDateTime": e.time.value.isoformat()}
    if e.detail is not None and e.detail.value:
        res["note"] = [{"text": e.detail.value}]
    res["extension"] = _prov(e, ("procedure", "time", "detail"))
    return res


def to_bundle(utterance: Utterance, entries: list[Entry], lexicon: Lexicon) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": utterance.capture_time.isoformat(),
        "meta": {"tag": [{"code": "demo", "display": DISCLAIMER}]},
        "incident": utterance.incident_id,
        "utterance": utterance.id,
        "entry": [{"resource": _medication(e, lexicon) if isinstance(e, MedicationEntry) else _procedure(e, lexicon)}
                  for e in entries],
    }


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(resources.files("jatayu.schemas").joinpath("fhir_lite.schema.json").read_text("utf-8"))
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


def validate_bundle(bundle: dict) -> None:
    _validator().validate(bundle)
