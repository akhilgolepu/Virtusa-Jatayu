from datetime import datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from jatayu.models import Entry, Field, MedicationEntry


def test_field_confidence_bounds():
    with pytest.raises(ValidationError):
        Field[float](value=1.0, span=(0, 1), confidence=1.5, source="rules")


def test_span_must_be_ordered():
    with pytest.raises(ValidationError):
        Field[str](value="x", span=(5, 2), confidence=1, source="rules")


def test_entry_roundtrip_discriminated():
    e = MedicationEntry(
        drug=Field[str](value="epinephrine", span=(10, 20), confidence=1, source="rules"),
        dose_value=Field[float](value=0.3, span=(5, 8), confidence=1, source="rules"),
        dose_unit=Field.missing("rules"),
        route=Field.missing("rules"),
        time=Field[datetime](value=datetime(2026, 10, 31, 10, 42).astimezone(), span=None, confidence=1, source="rules"),
    )
    ta = TypeAdapter(list[Entry])
    data = ta.validate_json(ta.dump_json([e]))
    assert isinstance(data[0], MedicationEntry) and data[0].dose_value.value == 0.3


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        Field[datetime](value=datetime(2026, 1, 1), span=None, confidence=1, source="rules")
