import io
import wave
from datetime import datetime

import pytest

from jatayu.models import Field, Flag, MedicationEntry, ProcedureEntry
from jatayu.readback import DRUG_LENGTH_SCALE, readback_parts, readback_text, synthesize_entry, synthesize_readback

T = datetime(2026, 10, 31, 10, 42).astimezone()


def _f(v):
    return Field(value=v, span=(0, 1), confidence=1.0, source="rules")


def test_medication_readback_with_flag():
    e = MedicationEntry(drug=_f("epinephrine"), dose_value=_f(0.3), dose_unit=_f("mg"), route=_f("IM"), time=_f(T),
                        flags=[Flag(code="dose_out_of_range", field="dose_value", severity="high",
                                    message="Dose outside the published adult range.")])
    assert readback_text(e) == ("Drug: Epinephrine. Zero point three milligrams, intramuscular, at 10:42. "
                                "Warning: Dose outside the published adult range. Confirm?")


def test_missing_fields_are_said_not_skipped():
    e = MedicationEntry(drug=_f("aspirin"), dose_value=Field.missing("rules"), dose_unit=Field.missing("rules"),
                        route=Field.missing("rules"), time=_f(T))
    assert readback_text(e) == "Drug: Aspirin. Dose not stated, route not stated, at 10:42. Confirm?"


def test_procedure_readback():
    p = ProcedureEntry(procedure=_f("endotracheal intubation"), time=_f(T), detail=_f("size 7.5"))
    assert readback_text(p) == "Endotracheal intubation, size 7.5, at 10:42. Confirm?"


@pytest.mark.models
def test_synthesize_readback_wav():
    with wave.open(io.BytesIO(synthesize_readback("Epinephrine, zero point three milligrams."))) as w:
        assert (w.getframerate(), w.getnchannels()) == (16000, 1) and w.getnframes() > 8000


def test_round10_drug_first_slow_heard_word_and_unit_in_full():
    """Presentation only (round 10, item 3): not claimed to catch a wrong drug."""
    heard = Field(value="salbutamol", span=(0, 10), confidence=1.0, source="rules", raw="Salbutamol")
    e = MedicationEntry(drug=heard, dose_value=_f(125.0), dose_unit=_f("mcg"), route=_f("IV"), time=_f(T))
    (drug, slow), (rest, normal) = readback_parts(e)
    assert drug == "Drug: Salbutamol." and slow == DRUG_LENGTH_SCALE > normal == 1.0
    assert rest.startswith("One hundred twenty-five micrograms") or "micrograms" in rest  # unit in full
    alias = Field(value="epinephrine", span=(0, 10), confidence=1.0, source="rules", raw="adrenaline")
    e2 = MedicationEntry(drug=alias, dose_value=_f(1.0), dose_unit=_f("mg"), route=_f("IV"), time=_f(T))
    assert readback_parts(e2)[0][0] == "Drug: Epinephrine. Heard as adrenaline."
    assert "1 mg" not in readback_text(e2) and "milligram" in readback_text(e2)


@pytest.mark.models
def test_synthesize_entry_says_the_drug_slower():
    e = MedicationEntry(drug=_f("epinephrine"), dose_value=_f(0.3), dose_unit=_f("mg"), route=_f("IM"), time=_f(T))
    slow = synthesize_readback("Drug: Epinephrine.", DRUG_LENGTH_SCALE)
    fast = synthesize_readback("Drug: Epinephrine.", 1.0)
    frames = lambda b: wave.open(io.BytesIO(b)).getnframes()  # noqa: E731
    assert frames(slow) > 1.3 * frames(fast)
    with wave.open(io.BytesIO(synthesize_entry(e))) as w:
        assert (w.getframerate(), w.getnchannels()) == (16000, 1) and w.getnframes() > frames(slow)
