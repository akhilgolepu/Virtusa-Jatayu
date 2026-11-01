"""Spoken confirmation of an entry: a fixed sentence template, read by the offline Piper voice."""
from __future__ import annotations

import io
import wave
from functools import lru_cache

from jatayu import config
from jatayu.audio import decode_to_16k
from jatayu.models import Entry, MedicationEntry
from jatayu.spoken import below_100, decimal_words, to_words

UNIT_WORDS = {"mg": "milligram", "mcg": "microgram", "g": "gram", "ml": "millilitre", "L/min": "litre per minute",
              "units": "unit", "puffs": "puff", "drops": "drop", "mmol": "millimole", "mEq": "milliequivalent"}
ROUTE_WORDS = {"IV": "intravenous", "IM": "intramuscular", "IO": "intraosseous", "SC": "subcutaneous",
               "PO": "by mouth", "SL": "sublingual", "IN": "intranasal", "NEB": "nebulised", "INH": "inhaled",
               "ET": "endotracheal", "PR": "rectal"}


def _unit(unit: str, value: float) -> str:
    word = UNIT_WORDS.get(unit, unit)
    if value == 1:
        return word
    return word.replace(" per ", "s per ") if " per " in word else word + "s"


def _clock(entry: Entry) -> str:
    t = entry.time.value
    hour = to_words(t.hour % 12 or 12)
    if t.minute == 0:
        return f"at {hour} o'clock"
    minute = f"oh {below_100(t.minute)}" if t.minute < 10 else below_100(t.minute, hyphen=True)
    return f"at {hour} {minute}"


def readback_text(entry: Entry) -> str:
    if isinstance(entry, MedicationEntry):
        parts = [entry.drug.value.capitalize() if entry.drug.value else "Unknown drug"]
        if entry.dose_value.value is None:
            parts.append("dose not stated")
        else:
            dose = decimal_words(entry.dose_value.value)
            parts.append(f"{dose} {_unit(entry.dose_unit.value, entry.dose_value.value)}"
                         if entry.dose_unit.value else f"{dose}, unit not stated")
        parts.append(ROUTE_WORDS.get(entry.route.value, entry.route.value) if entry.route.value else "route not stated")
    else:
        parts = [entry.procedure.value.capitalize()]
        if entry.detail is not None and entry.detail.value:
            parts.append(entry.detail.value)
    text = ", ".join(parts) + f", {_clock(entry)}."
    warnings = [f.message for f in entry.flags if f.severity == "high"]
    if warnings:
        text += " " + " ".join(f"Warning: {m}" for m in warnings)
    return text


@lru_cache(maxsize=1)
def _voice():
    from piper import PiperVoice

    return PiperVoice.load(config.READBACK_VOICE)


@lru_cache(maxsize=256)
def synthesize_readback(text: str) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        _voice().synthesize_wav(text, wf)
    return decode_to_16k(buf.getvalue())[1]
