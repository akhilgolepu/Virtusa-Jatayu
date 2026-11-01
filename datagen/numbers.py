"""Render dose values the way responders say (and ASR writes) them: "0.3", ".3", "point three", "1,000"..."""
from __future__ import annotations

from jatayu.spoken import ONES, to_words  # noqa: F401  (to_words re-exported for datagen callers)


def _digit_words(digits: str) -> str:
    return " ".join(ONES[int(d)] for d in digits)


def surfaces(value: float) -> list[str]:
    """Every surface form of `value` that the generator may emit; each normalises back to `value`."""
    value = float(value)
    out: list[str] = []
    if value.is_integer():
        n = int(value)
        out += [str(n), to_words(n)]
        if n >= 100 and n % 100:
            out.append(to_words(n, hundred_and=True))
        if n >= 1000:
            out.append(f"{n:,}")
        return list(dict.fromkeys(out))

    text = f"{value:g}"
    whole, frac = text.split(".")
    w = int(whole)
    out.append(text)
    if w == 0:
        out += [f".{frac}", f"point {_digit_words(frac)}", f"zero point {_digit_words(frac)}"]
    else:
        out.append(f"{to_words(w)} point {_digit_words(frac)}")
    if frac == "5":
        out.append("half" if w == 0 else f"{to_words(w)} and a half")
    return list(dict.fromkeys(out))
