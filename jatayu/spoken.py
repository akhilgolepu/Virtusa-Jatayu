"""Numbers as English words (shared by read-back and the synthetic data generator)."""
from __future__ import annotations

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
        "sixteen seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def below_100(n: int, hyphen: bool = False) -> str:
    if n < 20:
        return ONES[n]
    tens, ones = divmod(n, 10)
    return TENS[tens] + (("-" if hyphen else " ") + ONES[ones] if ones else "")


def to_words(n: int, hundred_and: bool = False) -> str:
    """0-99999 in English words; hundred_and=True gives the British/Indian "three hundred and twenty five"."""
    if not 0 <= n <= 99999:
        raise ValueError(f"out of range: {n}")
    if n < 100:
        return below_100(n)
    parts = []
    thousands, rest = divmod(n, 1000)
    if thousands:
        parts.append(f"{below_100(thousands)} thousand")
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        parts.append(f"{ONES[hundreds]} hundred")
    if rest:
        parts.append(("and " if hundred_and else "") + below_100(rest))
    return " ".join(parts)


def decimal_words(value: float) -> str:
    """0.3 -> "zero point three", 22.75 -> "twenty two point seven five", 4.0 -> "four"."""
    text = f"{float(value):g}"
    if "." not in text:
        return to_words(int(text))
    whole, frac = text.split(".")
    return f"{to_words(int(whole))} point {' '.join(ONES[int(d)] for d in frac)}"
