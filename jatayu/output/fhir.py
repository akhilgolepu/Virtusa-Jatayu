"""FHIR-lite Bundle: MedicationAdministration and Procedure resources with span provenance, plus one Communication per
utterance carrying its transcript. Checked every time by our FHIR-lite JSON Schema (jatayu/schemas/fhir_lite.schema.json).
Round 9: the bundle is also shaped to pass the fhir.resources R4 models (scripts/fhir_r4_check.py) as it is emitted —
every resource names its subject (an unidentified patient, keyed by the incident), the incident id is
Bundle.identifier, the device is meta.source, and the transcripts are Communication resources, not extra fields."""
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
PATIENT_SYSTEM = "urn:jatayu:incident-patient"
UTTERANCE_SYSTEM = "urn:jatayu:utterance"
CLINICAL = ("MedicationAdministration", "Procedure")


def subject(incident_id: str) -> dict:
    """The patient every resource is about: not identified in the field, so a logical reference keyed by the incident."""
    return {"identifier": {"system": PATIENT_SYSTEM, "value": incident_id}, "display": "Unidentified patient"}
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
        "subject": {},  # filled by _resource
        # a drug not in the lexicon keeps its spoken name and has no code (it carries drug_not_in_lexicon)
        "medicationCodeableConcept": {"text": e.drug.value, **({"coding": [{"system": ATC, "code": lexicon.drug(e.drug.value).atc}]}
                                                               if lexicon.has_drug(e.drug.value) else {})},
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
    res = {"resourceType": "Procedure", "status": status, "subject": {}, "code": code,
           "performedDateTime": e.time.value.isoformat()}
    if e.detail is not None and e.detail.value:
        res["note"] = [{"text": e.detail.value}]
    res["extension"] = _prov(e, ("procedure", "time", "detail"), utterance_id, review_status)
    return res


def _resource(e: Entry, lexicon: Lexicon, incident_id: str, status: str = "in-progress",
              utterance_id: str | None = None, review_status: str = "draft") -> dict:
    build = _medication if isinstance(e, MedicationEntry) else _procedure
    status, reason = _status(e, status)
    res = build(e, lexicon, status, utterance_id, review_status)
    res["subject"] = subject(incident_id)
    if reason:  # R4: MedicationAdministration.statusReason is a list, Procedure.statusReason a single concept
        res["statusReason"] = [{"text": reason}] if isinstance(e, MedicationEntry) else {"text": reason}
    return res


def _communication(incident_id: str, utterance_id: str, transcript: str, capture_time: str) -> dict:
    """One utterance as said: provenance spans of the resources that name this utterance index into its text."""
    return {"resourceType": "Communication", "identifier": [{"system": UTTERANCE_SYSTEM, "value": utterance_id}],
            "status": "completed", "subject": subject(incident_id), "sent": capture_time,
            "payload": [{"contentString": transcript}]}


def _meta(device: str | None = None) -> dict:
    meta = {"tag": [{"code": "demo", "display": DISCLAIMER}]}
    if device:
        meta["source"] = f"urn:jatayu:device:{device}"
    return meta


def to_bundle(utterance: Utterance, entries: list[Entry], lexicon: Lexicon) -> dict:
    """One utterance: its clinical resources, then its transcript as a Communication."""
    inc = utterance.incident_id
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "identifier": {"system": "urn:jatayu:incident", "value": inc},
        "timestamp": utterance.capture_time.isoformat(),
        "meta": _meta(),
        "entry": [{"resource": _resource(e, lexicon, inc, utterance_id=utterance.id)} for e in entries]
        + [{"resource": _communication(inc, utterance.id, utterance.raw_transcript, utterance.capture_time.isoformat())}],
    }


def to_incident_bundle(incident: dict, items: list[tuple[Entry, str, str]], utterances: list[dict],
                       lexicon: Lexicon) -> dict:
    """items: (entry, status, utterance_id). Clinical resources first, then one Communication per utterance; spans in
    each resource's provenance index into the transcript of the utterance it names."""
    fhir_status = {"confirmed": "completed", "rejected": "entered-in-error"}
    inc = incident["id"]
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "identifier": {"system": "urn:jatayu:incident", "value": inc},
        "timestamp": incident["started_at"],
        "meta": _meta(incident.get("device", "unknown")),
        "entry": [{"resource": _resource(e, lexicon, inc, fhir_status.get(status, "in-progress"), utt, status)}
                  for e, status, utt in items]
        + [{"resource": _communication(inc, u["id"], u["transcript"], u["capture_time"])} for u in utterances],
    }


def clinical(bundle: dict) -> list[dict]:
    """The MedicationAdministration and Procedure resources of a bundle, in order."""
    return [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] in CLINICAL]


def transcripts(bundle: dict) -> list[dict]:
    """[{id, transcript, capture_time}] from the bundle's Communication resources."""
    return [{"id": r["identifier"][0]["value"], "transcript": r["payload"][0]["contentString"], "capture_time": r["sent"]}
            for r in (e["resource"] for e in bundle["entry"]) if r["resourceType"] == "Communication"]


def status_reason(resource: dict) -> str | None:
    r = resource.get("statusReason")
    return (r[0] if isinstance(r, list) else r)["text"] if r else None


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(resources.files("jatayu.schemas").joinpath("fhir_lite.schema.json").read_text("utf-8"))
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


def validate_bundle(bundle: dict) -> None:
    _validator().validate(bundle)


def provenance(resource: dict) -> dict:
    """The provenance record a resource carries (spans, sources, flags, review status)."""
    return json.loads(resource["extension"][0]["valueString"])
