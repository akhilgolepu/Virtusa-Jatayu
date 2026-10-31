from jatayu.normalise.text import normalise


def test_normalise_maps_back_to_raw():
    raw = "Gave point three of Adrenaline IM, two mins ago"
    nt = normalise(raw)
    num = next(t for t in nt.tokens if t.kind == "number")
    assert num.value == 0.3 and raw[num.raw_start:num.raw_end] == "point three"
    assert "0.3" in nt.text and "adrenaline" in nt.text


def test_digit_decimal_token():
    nt = normalise("pushed 4 mg ondansetron IV")
    assert [t.value for t in nt.tokens if t.kind == "number"] == [4.0]


def test_non_ascii_offsets_stay_correct():
    raw = "adrenaline 0.3 mg IM दे दिया"
    nt = normalise(raw)
    for t in nt.tokens:
        assert raw[t.raw_start:t.raw_end].lower() == t.text or t.kind == "number"
    assert nt.raw_span(0, 1) == (0, 10)
    assert [t.text for t in nt.tokens][-2:] == ["दे", "दिया"]


def test_a_before_unit_not_number():
    nt = normalise("gave a gram of TXA")
    assert all(t.kind != "number" for t in nt.tokens)


import pytest  # noqa: E402


@pytest.mark.parametrize("raw,values", [
    ("adrenaline .5 mg IM", [0.5]),
    ("adrenaline point 5 mg IM", [0.5]),
    ("one point 5 mg", [1.5]),
    ("fentanyl one hundred and fifty micrograms", [150.0]),
    ("aspirin three hundred and twenty five milligrams", [325.0]),
    ("normal saline 1,000 ml IV", [1000.0]),
    ("two thousand and fifty units", [2050.0]),
])
def test_number_forms_medics_say(raw, values):
    assert [t.value for t in normalise(raw).tokens if t.kind == "number"] == values


def test_asr_glued_decimal_splits_from_word():
    # Whisper writes "glucagon .5 mg" as "glucagon.5 mg"; the drug and the 0.5 must both survive.
    nt = normalise("glucagon.5 MD, intramuscular")
    assert [t.text for t in nt.tokens][:2] == ["glucagon", "0.5"]
    assert [t.text for t in normalise("given i.m.").tokens][:2] == ["given", "i.m"]
