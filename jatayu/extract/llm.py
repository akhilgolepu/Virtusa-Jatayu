"""LLM extractor: the model only QUOTES the transcript; code derives every value from the quoted words with the same
normaliser/lexicon as the rules extractor. A quote that is not in the transcript, or does not parse, is rejected."""
from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime

from jatayu.lexicon import Lexicon
from jatayu.llm import LlmRunner
from jatayu.models import Entry, Field, Flag, MedicationEntry, ProcedureEntry
from jatayu.normalise.text import normalise
from jatayu.normalise.timeparse import find_times

LLM_CONFIDENCE = 0.9
FIELDS = ("drug", "dose", "unit", "route", "time", "procedure", "detail")
ENTRY_FIELD = {"drug": "drug", "dose": "dose_value", "unit": "dose_unit", "route": "route", "time": "time",
               "procedure": "procedure", "detail": "detail"}

SYSTEM = (
    "You extract ambulance medication administrations and procedures from a responder's transcript.\n"
    "Return one entry per drug given or procedure done. For each field COPY THE EXACT WORDS from the transcript "
    "(same spelling, same order), or null if not said. Never write words that are not in the transcript.\n"
    "drug: the drug name as said. dose: only the number words/digits. unit: the unit words. route: the route words. "
    "time: the whole time phrase (e.g. 'two mins ago', 'at 10 42'). procedure: the procedure words. "
    "detail: e.g. 'size 7.5'.\n"
    "context: 'given' if it was administered; 'not_given' for allergies, refused, withheld, not given, or the "
    "patient's own regular medication; 'measurement' for readings such as blood glucose or oxygen saturation."
)
_Q = {"type": ["string", "null"]}
SCHEMA = {
    "type": "object",
    "properties": {"entries": {"type": "array", "items": {
        "type": "object",
        "properties": {"kind": {"enum": ["medication", "procedure"]},
                       "context": {"enum": ["given", "not_given", "measurement"]},
                       **{f: _Q for f in FIELDS}},
        "required": ["kind", "context", *FIELDS]}}},
    "required": ["entries"],
}


def locate(raw: str, quote: str, near: int | None = None) -> tuple[int, int] | None:
    """Whole-token, case-insensitive occurrence of `quote` in `raw`, nearest to `near` when it occurs twice."""
    quote = quote.strip()
    if not quote:
        return None
    hits = [m.span() for m in re.finditer(r"(?<![\w.])" + re.escape(quote) + r"(?!\w)", raw, re.IGNORECASE)]
    if not hits:
        return None
    return min(hits, key=lambda s: abs(s[0] - near)) if near is not None else hits[0]


def derive(name: str, text: str, lexicon: Lexicon, capture_time: datetime):
    """The value a quoted text stands for, or None. Same rules as the rules extractor."""
    if name == "drug":
        hit = lexicon.lookup_drug(text) or (lexicon.fuzzy_drug(text, 88) or (None,))[0]
        return hit
    if name == "dose":
        nums = [t.value for t in normalise(text).tokens if t.kind == "number"]
        return nums[0] if len(nums) == 1 else None
    if name == "unit":
        return lexicon.canonical_unit(text)
    if name == "route":
        return lexicon.canonical_route(text)
    if name == "procedure":
        return lexicon.lookup_procedure(text)
    if name == "time":
        times = find_times(normalise(text), capture_time)
        return times[0].value if len(times) == 1 else None
    if name == "detail":
        return text if re.search(r"\d", text) else None
    return None


def assemble(kind: str, context: str, fields: dict[str, Field | None], unsupported: list[str],
             capture_time: datetime, extra_flags: list[Flag] = ()) -> Entry | None:
    """Build an entry from supported fields; add the same structural flags the rules extractor uses."""
    flags = [Flag(code="llm_unsupported", field=ENTRY_FIELD[n], severity="high",
                  message=f"The model's {n} is not supported by the transcript and was discarded.") for n in unsupported]
    time = fields.get("time")
    if time is None:
        time = Field[datetime](value=capture_time, span=None, confidence=1.0, source="rules")
        flags.append(Flag(code="time_not_stated", field="time", severity="low", message="No time stated; using capture time."))
    if context == "not_given":
        flags.append(Flag(code="possible_not_given", field="drug", severity="high",
                          message="The transcript suggests this was not given now (negation, allergy or regular medication)."))
    elif context == "measurement":
        flags.append(Flag(code="possible_measurement", field="drug", severity="high",
                          message="This looks like a measurement, not a dose given."))
    flags.extend(f for f in extra_flags if f.code not in {g.code for g in flags})
    if kind == "procedure":
        if fields.get("procedure") is None:
            return None
        return ProcedureEntry(procedure=fields["procedure"], time=time, detail=fields.get("detail"), flags=flags)
    if fields.get("drug") is None:
        return None
    missing = lambda: Field.missing("llm")  # noqa: E731
    dose, unit, route = fields.get("dose") or missing(), fields.get("unit") or missing(), fields.get("route") or missing()
    if dose.value is None and "dose" not in unsupported:
        flags.append(Flag(code="field_missing", field="dose_value", severity="high", message="No dose stated."))
    elif dose.value is not None and unit.value is None and "unit" not in unsupported:
        flags.append(Flag(code="field_missing", field="dose_unit", severity="high", message="Dose has no unit."))
    if route.value is None and "route" not in unsupported:
        flags.append(Flag(code="field_missing", field="route", severity="medium", message="No route stated."))
    return MedicationEntry(drug=fields["drug"], dose_value=dose, dose_unit=unit, route=route, time=time, flags=flags)


class LlmExtractor:
    name = "llm"

    def __init__(self, lexicon: Lexicon, runner_factory: Callable[[], LlmRunner]):
        self.lexicon, self.runner_factory = lexicon, runner_factory

    def extract(self, raw: str, capture_time: datetime) -> list[Entry]:
        out = self.runner_factory().complete_json(SYSTEM, f"Transcript: {raw}", SCHEMA)
        entries = []
        for item in out.get("entries", []):
            kind, context = item.get("kind", "medication"), item.get("context", "given")
            anchor = item.get("drug") if kind == "medication" else item.get("procedure")
            anchor_span = locate(raw, anchor) if anchor else None
            near = anchor_span[0] if anchor_span else None
            fields: dict[str, Field | None] = {}
            unsupported: list[str] = []
            for name in FIELDS:
                quote = item.get(name)
                if not quote:
                    continue
                span = locate(raw, quote, near)
                value = derive(name, raw[span[0]:span[1]], self.lexicon, capture_time) if span else None
                if span is None or value is None:
                    unsupported.append(name)
                    continue
                fields[name] = Field(value=value, span=span, confidence=LLM_CONFIDENCE, source="llm")
            entry = assemble(kind, context, fields, unsupported, capture_time)
            if entry is not None:
                entries.append(entry)
        return entries
