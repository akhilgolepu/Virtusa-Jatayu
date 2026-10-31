"""Core data model. Every extracted value carries a span into the raw transcript."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar, Union

from pydantic import BaseModel, Discriminator, field_validator, model_validator
from pydantic import Field as PydField

T = TypeVar("T")
Span = tuple[int, int]
Source = Literal["rules", "llm", "ner", "user"]


class Field(BaseModel, Generic[T]):
    value: T | None
    span: Span | None
    confidence: float = PydField(ge=0.0, le=1.0)
    source: Source

    @field_validator("span")
    @classmethod
    def _ordered(cls, v: Span | None) -> Span | None:
        if v is not None and not (0 <= v[0] <= v[1]):
            raise ValueError(f"span must satisfy 0 <= start <= end, got {v}")
        return v

    @model_validator(mode="after")
    def _aware_datetime(self) -> "Field[T]":
        if isinstance(self.value, datetime) and self.value.tzinfo is None:
            raise ValueError("datetime values must be timezone-aware")
        return self

    @classmethod
    def missing(cls, source: Source) -> "Field":
        return cls(value=None, span=None, confidence=0.0, source=source)


class Flag(BaseModel):
    code: str
    field: str | None = None
    severity: Literal["high", "medium", "low"]
    message: str


class MedicationEntry(BaseModel):
    kind: Literal["medication"] = "medication"
    drug: Field[str]
    dose_value: Field[float]
    dose_unit: Field[str]
    route: Field[str]
    time: Field[datetime]
    flags: list[Flag] = []


class ProcedureEntry(BaseModel):
    kind: Literal["procedure"] = "procedure"
    procedure: Field[str]
    time: Field[datetime]
    detail: Field[str] | None = None
    flags: list[Flag] = []


Entry = Annotated[Union[MedicationEntry, ProcedureEntry], Discriminator("kind")]


class Utterance(BaseModel):
    id: str = PydField(default_factory=lambda: uuid.uuid4().hex)
    incident_id: str
    capture_time: datetime
    raw_transcript: str
    audio_sha256: str | None = None
    audio_path: str | None = None
