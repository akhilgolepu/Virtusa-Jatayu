"""Gold annotation format for synthetic and recorded utterances (consumed by eval in Plan 4)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

Category = Literal["med_basic", "med_messy", "med_multi", "med_correction", "med_incomplete", "procedure",
                   "hinglish", "context_negation", "context_measurement", "time_clock"]


class GoldField(BaseModel):
    value: Any
    surface: str
    span: tuple[int, int]


class GoldTime(BaseModel):
    kind: Literal["relative", "clock", "none"] = "none"
    offset_s: int | None = None
    hh: int | None = None
    mm: int | None = None
    surface: str | None = None
    span: tuple[int, int] | None = None


class GoldEntry(BaseModel):
    kind: Literal["medication", "procedure"]
    context: Literal["given", "not_given", "measurement"] = "given"
    drug: GoldField | None = None
    procedure: GoldField | None = None
    dose_value: GoldField | None = None
    dose_unit: GoldField | None = None
    route: GoldField | None = None
    detail: GoldField | None = None
    measured_value: GoldField | None = None  # context "measurement": the reading itself ("blood glucose 2.1")
    time: GoldTime = GoldTime()
    anomaly: Literal["10x", "unit_swap"] | None = None


class GoldUtterance(BaseModel):
    id: str
    family: str
    category: Category
    split: Literal["train", "dev", "test", "unsplit"] = "unsplit"
    lang: Literal["en", "hinglish"]
    text: str
    capture_time: str
    entries: list[GoldEntry]
    tags: list[str] = []
