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
