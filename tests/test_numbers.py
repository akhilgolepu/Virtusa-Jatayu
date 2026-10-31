import pytest

from jatayu.normalise.numbers import parse_spoken_number


@pytest.mark.parametrize("words,expected", [
    (["point", "three"], (0.3, 2)), (["zero", "point", "five"], (0.5, 3)), (["four"], (4.0, 1)),
    (["one", "and", "a", "half"], (1.5, 4)), (["half"], (0.5, 1)), (["twenty", "five"], (25.0, 2)),
    (["one", "hundred", "fifty"], (150.0, 3)), (["point", "oh", "five"], (0.05, 3)), (["a"], None), (["mg"], None),
])
def test_parse_spoken_number(words, expected):
    assert parse_spoken_number(words) == expected
