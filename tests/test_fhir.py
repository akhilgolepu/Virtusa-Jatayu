import json

import jsonschema
import pytest

from jatayu.output.fhir import to_bundle, validate_bundle


def test_bundle_valid_and_carries_disclaimer(lexicon, sample_utterance, sample_entries):
    b = to_bundle(sample_utterance, sample_entries, lexicon)
    validate_bundle(b)
    assert b["meta"]["tag"][0]["display"] == "Decision-support demo, not a clinical device."
    med = b["entry"][0]["resource"]
    assert med["resourceType"] == "MedicationAdministration"
    assert med["medicationCodeableConcept"]["coding"][0]["code"] == lexicon.drug("epinephrine").atc
    assert med["dosage"]["dose"] == {"value": 0.3, "unit": "mg"}


def test_missing_fields_omitted_not_null(lexicon, sample_utterance, entry_missing_dose):
    med = to_bundle(sample_utterance, [entry_missing_dose], lexicon)["entry"][0]["resource"]
    assert "dose" not in med.get("dosage", {})
    assert "null" not in json.dumps({k: v for k, v in med.items() if k != "extension"})


def test_provenance_spans_present(lexicon, sample_utterance, sample_entries):
    ext = to_bundle(sample_utterance, sample_entries, lexicon)["entry"][0]["resource"]["extension"][0]
    prov = json.loads(ext["valueString"])
    assert prov["drug"]["span"] == list(sample_entries[0].drug.span)


def test_procedure_resource(lexicon, sample_utterance):
    from datetime import datetime
    from jatayu.extract.rules import RulesExtractor
    entries = RulesExtractor(lexicon).extract("started CPR at 10:30", datetime(2026, 10, 31, 10, 45).astimezone())
    b = to_bundle(sample_utterance, entries, lexicon)
    validate_bundle(b)
    proc = b["entry"][0]["resource"]
    assert proc["resourceType"] == "Procedure" and proc["code"]["text"] == "cpr"
    assert proc["performedDateTime"].startswith("2026-10-31T10:30")


def test_schema_rejects_garbage():
    with pytest.raises(jsonschema.ValidationError):
        validate_bundle({"resourceType": "Bundle"})
