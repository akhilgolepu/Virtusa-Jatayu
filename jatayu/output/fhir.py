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
# An entry the utterance says was NOT given (negation, allergy, refusal, home medication) or that is a reading is
# never written as an administration, whatever its review status: FHIR status "not-done" plus the reason. Acknowledging
# the flag at confirm time records that the medic saw it; to record a real administration they reject and re-dictate.
NOT_DONE = {"possible_not_given": "Not given: the utterance states a negation, allergy, refusal or regular medication.",
            "possible_measurement": "A reading, not an administration."}


def _status(e: Entry, status: str) -> tuple[str, str | None]:
    if status != "entered-in-error":
        for f in e.flags:
            if f.code in NOT_DONE:
                return "not-done", NOT_DONE[f.code]
    return status, None


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _prov(entry: Entry, names: tuple[str, ...], utterance_id: str | None = None,
          review_status: str = "draft") -> list[dict]:
    record = {"entry_id": entry.id, "review_status": review_status}  # draft | edited | confirmed | rejected
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
                utterance_id: str | None = None, review_status: str = "draft") -> dict:
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
    res["extension"] = _prov(e, ("drug", "dose_value", "dose_unit", "route", "time"), utterance_id, review_status)
    return res


def _procedure(e: ProcedureEntry, lexicon: Lexicon, status: str = "in-progress",
               utterance_id: str | None = None, review_status: str = "draft") -> dict:
    code = {"text": e.procedure.value}
    snomed = lexicon.procedure(e.procedure.value).snomed
    if snomed:
        code["coding"] = [{"system": SNOMED, "code": snomed}]
    res = {"resourceType": "Procedure", "status": status, "code": code,
           "performedDateTime": e.time.value.isoformat()}
    if e.detail is not None and e.detail.value:
        res["note"] = [{"text": e.detail.value}]
    res["extension"] = _prov(e, ("procedure", "time", "detail"), utterance_id, review_status)
    return res


def _resource(e: Entry, lexicon: Lexicon, status: str = "in-progress", utterance_id: str | None = None,
              review_status: str = "draft") -> dict:
    build = _medication if isinstance(e, MedicationEntry) else _procedure
    status, reason = _status(e, status)
    res = build(e, lexicon, status, utterance_id, review_status)
    if reason:
        res["statusReason"] = [{"text": reason}]
    return res


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
        "entry": [{"resource": _resource(e, lexicon, fhir_status.get(status, "in-progress"), utt, status)}
                  for e, status, utt in items],
    }


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(resources.files("jatayu.schemas").joinpath("fhir_lite.schema.json").read_text("utf-8"))
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


def validate_bundle(bundle: dict) -> None:
    _validator().validate(bundle)


def provenance(resource: dict) -> dict:
    """The provenance record a resource carries (spans, sources, flags, review status)."""
    return json.loads(resource["extension"][0]["valueString"])
