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


def _prov(entry: Entry, names: tuple[str, ...], utterance_id: str | None = None) -> list[dict]:
    record = {"entry_id": entry.id}
    if utterance_id:
        record["utterance_id"] = utterance_id
    for name in names:
        f: Field | None = getattr(entry, name)
        if f is not None:
            record[name] = {"span": list(f.span) if f.span else None, "confidence": f.confidence, "source": f.source,
                            "raw": f.raw}
    record["time_source"] = entry.time_source
    record["flags"] = [fl.model_dump() for fl in entry.flags]
    return [{"url": "urn:jatayu:provenance", "valueString": _canonical(record)}]


def _medication(e: MedicationEntry, lexicon: Lexicon, status: str = "in-progress",
                utterance_id: str | None = None) -> dict:
    res = {
        "resourceType": "MedicationAdministration",
        "status": status,
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
    res["extension"] = _prov(e, ("drug", "dose_value", "dose_unit", "route", "time"), utterance_id)
    return res


def _procedure(e: ProcedureEntry, lexicon: Lexicon, status: str = "in-progress",
               utterance_id: str | None = None) -> dict:
    code = {"text": e.procedure.value}
    snomed = lexicon.procedure(e.procedure.value).snomed
    if snomed:
        code["coding"] = [{"system": SNOMED, "code": snomed}]
    res = {"resourceType": "Procedure", "status": status, "code": code,
           "performedDateTime": e.time.value.isoformat()}
    if e.detail is not None and e.detail.value:
        res["note"] = [{"text": e.detail.value}]
    res["extension"] = _prov(e, ("procedure", "time", "detail"), utterance_id)
    return res


def _resource(e: Entry, lexicon: Lexicon, status: str = "in-progress", utterance_id: str | None = None) -> dict:
    build = _medication if isinstance(e, MedicationEntry) else _procedure
    return build(e, lexicon, status, utterance_id)


def to_bundle(utterance: Utterance, entries: list[Entry], lexicon: Lexicon) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": utterance.capture_time.isoformat(),
        "meta": {"tag": [{"code": "demo", "display": DISCLAIMER}]},
        "incident": utterance.incident_id,
        "utterance": utterance.id,
        "transcript": utterance.raw_transcript,  # spans in each resource's provenance index into this text
        "entry": [{"resource": _resource(e, lexicon)} for e in entries],
    }


def to_incident_bundle(incident: dict, items: list[tuple[Entry, str, str]], utterances: list[dict],
                       lexicon: Lexicon) -> dict:
    """items: (entry, status, utterance_id). Spans in each resource's provenance index into the transcript of
    the utterance it names; the top-level transcript is empty for an incident bundle."""
    fhir_status = {"confirmed": "completed", "rejected": "entered-in-error"}
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": incident["started_at"],
        "meta": {"tag": [{"code": "demo", "display": DISCLAIMER}], "device": incident.get("device", "unknown")},
        "incident": incident["id"],
        "utterance": incident["id"],
        "transcript": "",
        "utterances": [{"id": u["id"], "transcript": u["transcript"], "capture_time": u["capture_time"]}
                       for u in utterances],
        "entry": [{"resource": _resource(e, lexicon, fhir_status.get(status, "in-progress"), utt)}
                  for e, status, utt in items],
    }


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(resources.files("jatayu.schemas").joinpath("fhir_lite.schema.json").read_text("utf-8"))
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


def validate_bundle(bundle: dict) -> None:
    _validator().validate(bundle)
