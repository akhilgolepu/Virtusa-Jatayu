"""Render dose values the way responders say (and ASR writes) them: "0.3", ".3", "point three", "1,000"..."""
from __future__ import annotations

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
        "sixteen seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _below_100(n: int) -> str:
    if n < 20:
        return ONES[n]
    tens, ones = divmod(n, 10)
    return TENS[tens] + (f" {ONES[ones]}" if ones else "")


def to_words(n: int, hundred_and: bool = False) -> str:
    """0-9999 in English words; hundred_and=True gives the British/Indian "three hundred and twenty five"."""
    if not 0 <= n <= 9999:
        raise ValueError(f"out of range: {n}")
    if n < 100:
        return _below_100(n)
    parts = []
    thousands, rest = divmod(n, 1000)
    if thousands:
        parts.append(f"{ONES[thousands]} thousand")
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        parts.append(f"{ONES[hundreds]} hundred")
    if rest:
        parts.append(("and " if hundred_and else "") + _below_100(rest))
    return " ".join(parts)


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
