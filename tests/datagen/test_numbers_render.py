import pytest

from datagen.numbers import surfaces, to_words
from jatayu.normalise.text import normalise

VALUES = [0.05, 0.1, 0.3, 0.5, 1, 1.5, 2, 2.5, 4, 10, 25, 50, 100, 150, 300, 325, 500, 1000, 2000]


@pytest.mark.parametrize("value", VALUES)
def test_surfaces_round_trip(value):
    forms = surfaces(value)
    assert len(forms) >= 2
    for s in forms:
        nums = [t.value for t in normalise(s).tokens if t.kind == "number"]
        assert nums == [value], (s, nums)


def test_words_and_hundred_and():
    assert to_words(325) == "three hundred twenty five"
    assert "three hundred and twenty five" in surfaces(325)
    assert "1,000" in surfaces(1000)
    assert ".5" in surfaces(0.5) and "half" in surfaces(0.5)
    assert "two and a half" in surfaces(2.5)
