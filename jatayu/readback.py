"""Spoken confirmation of an entry: a fixed sentence template, read by the offline Piper voice.

Round 10: drug identity comes first and is the most audible part. The drug name is a phrase of its own, spoken SLOWLY
(DRUG_LENGTH_SCALE) and followed by a pause; if the words heard differ from the drug recorded, "heard as ..." follows.
Units are always spoken in full ("milligrams", never "m g"). This is a presentation change: it is not claimed to catch
a wrong drug (no measurement; the human test comes later)."""
from __future__ import annotations

import io
import wave
from functools import lru_cache

from jatayu import config
from jatayu.audio import decode_to_16k
from jatayu.models import Entry, MedicationEntry
from jatayu.spoken import decimal_words

DRUG_LENGTH_SCALE = 1.6  # Piper length_scale for the drug phrase (1.0 = the voice's normal speed; larger = slower)
PAUSE_S = 0.35
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
    """24-hour digits ("at 14:32"); the voice reads them as "fourteen thirty-two"."""
    return f"at {entry.time.value:%H:%M}"


def _letters(s: str | None) -> str:
    return "".join(c for c in (s or "").lower() if c.isalpha())


def drug_phrase(entry: MedicationEntry) -> str:
    """The first thing said: the drug, alone ("Drug: Ondansetron."), then what was heard if it differs."""
    name = entry.drug.value.capitalize() if entry.drug.value else "Unknown drug"
    text = f"Drug: {name}."
    if entry.drug.raw and _letters(entry.drug.raw) != _letters(entry.drug.value):
        text += f" Heard as {entry.drug.raw}."
    return text


def readback_parts(entry: Entry) -> list[tuple[str, float]]:
    """(text, length_scale) phrases in speaking order: for a medication the drug phrase first and slow."""
    if not isinstance(entry, MedicationEntry):
        return [(readback_text(entry), 1.0)]
    return [(drug_phrase(entry), DRUG_LENGTH_SCALE), (_rest(entry), 1.0)]


def _rest(entry: MedicationEntry) -> str:
    parts = []
    if entry.dose_value.value is None:
        parts.append("dose not stated")
    else:
        dose = decimal_words(entry.dose_value.value)
        parts.append(f"{dose} {_unit(entry.dose_unit.value, entry.dose_value.value)}"
                     if entry.dose_unit.value else f"{dose}, unit not stated")
    parts.append(ROUTE_WORDS.get(entry.route.value, entry.route.value) if entry.route.value else "route not stated")
    text = ", ".join(parts) + f", {_clock(entry)}."
    return text[0].upper() + text[1:] + _warnings(entry)


def _warnings(entry: Entry) -> str:
    warnings = [f.message for f in entry.flags if f.severity == "high"]
    text = (" " + " ".join(f"Warning: {m}" for m in warnings)) if warnings else ""
    return text + " Confirm?"


def readback_text(entry: Entry) -> str:
    if isinstance(entry, MedicationEntry):
        return " ".join(t for t, _ in readback_parts(entry))
    parts = [entry.procedure.value.capitalize()]
    if entry.detail is not None and entry.detail.value:
        parts.append(entry.detail.value)
    return ", ".join(parts) + f", {_clock(entry)}." + _warnings(entry)


@lru_cache(maxsize=1)
def _voice():
    from piper import PiperVoice

    return PiperVoice.load(config.READBACK_VOICE)


@lru_cache(maxsize=256)
def synthesize_readback(text: str, length_scale: float = 1.0) -> bytes:
    from piper.config import SynthesisConfig

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        _voice().synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=length_scale))
    return decode_to_16k(buf.getvalue())[1]


def synthesize_entry(entry: Entry) -> bytes:
    """The read-back of one entry: its phrases at their own speeds, joined with a short pause (16 kHz mono WAV)."""
    frames, rate, width = [], 16000, 2
    for i, (text, scale) in enumerate(readback_parts(entry)):
        with wave.open(io.BytesIO(synthesize_readback(text, scale))) as w:
            rate, width = w.getframerate(), w.getsampwidth()
            if i:
                frames.append(b"\x00" * int(PAUSE_S * rate) * width * w.getnchannels())
            frames.append(w.readframes(w.getnframes()))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(width)
        out.setframerate(rate)
        out.writeframes(b"".join(frames))
    return buf.getvalue()
