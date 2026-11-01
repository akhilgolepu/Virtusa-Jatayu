import io
import wave
from datetime import datetime

import pytest

from jatayu.models import Field, Flag, MedicationEntry, ProcedureEntry
from jatayu.readback import readback_text, synthesize_readback

T = datetime(2026, 10, 31, 10, 42).astimezone()


def _f(v):
    return Field(value=v, span=(0, 1), confidence=1.0, source="rules")


def test_medication_readback_with_flag():
    e = MedicationEntry(drug=_f("epinephrine"), dose_value=_f(0.3), dose_unit=_f("mg"), route=_f("IM"), time=_f(T),
                        flags=[Flag(code="dose_out_of_range", field="dose_value", severity="high",
                                    message="Dose outside the published adult range.")])
    assert readback_text(e) == ("Epinephrine, zero point three milligrams, intramuscular, at ten forty-two. "
                                "Warning: Dose outside the published adult range.")


def test_missing_fields_are_said_not_skipped():
    e = MedicationEntry(drug=_f("aspirin"), dose_value=Field.missing("rules"), dose_unit=Field.missing("rules"),
                        route=Field.missing("rules"), time=_f(T))
    assert readback_text(e) == "Aspirin, dose not stated, route not stated, at ten forty-two."


def test_procedure_readback():
    p = ProcedureEntry(procedure=_f("endotracheal intubation"), time=_f(T), detail=_f("size 7.5"))
    assert readback_text(p) == "Endotracheal intubation, size 7.5, at ten forty-two."


@pytest.mark.models
def test_synthesize_readback_wav():
    with wave.open(io.BytesIO(synthesize_readback("Epinephrine, zero point three milligrams."))) as w:
        assert (w.getframerate(), w.getnchannels()) == (16000, 1) and w.getnframes() > 8000
