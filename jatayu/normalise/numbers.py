"""Spoken English numbers -> floats ("point three" -> 0.3, "one and a half" -> 1.5)."""
from __future__ import annotations

ONES = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
DIGITS = {**{w: str(i) for w, i in ONES.items() if i < 10}, "oh": "0"}
FRACTIONS = {"half": 0.5, "quarter": 0.25}

# words that can begin a spoken number (used by the normaliser to decide where to try)
STARTERS = set(ONES) | set(TENS) | {"point", "half", "a"}


def _cardinal(words: list[str]) -> tuple[int | None, int]:
    """Parse an integer like 'one hundred and fifty' or 'twenty five'. Returns (value|None, consumed)."""
    total, current, n, last = 0, 0, 0, None
    k = 0
    while k < len(words):
        w = words[k]
        # British/Indian "three hundred AND twenty five": 'and' joins only when a ones/tens word follows.
        if w == "and" and last in ("hundred", "thousand") and k + 1 < len(words) \
                and (words[k + 1] in ONES or words[k + 1] in TENS):
            k += 1
            continue
        if w in ONES and last in (None, "hundred", "thousand") or (w in ONES and ONES[w] < 10 and last == "tens"):
            current += ONES[w]; last = "ones"
        elif w in TENS and last in (None, "hundred", "thousand"):
            current += TENS[w]; last = "tens"
        elif w == "hundred" and last in ("ones", "tens") and current < 100:
            current *= 100; last = "hundred"
        elif w == "thousand" and last in ("ones", "tens", "hundred"):
            total += current * 1000; current = 0; last = "thousand"
        else:
            break
        k += 1
        n = k
    return (total + current, n) if n else (None, 0)


def parse_spoken_number(words: list[str]) -> tuple[float, int] | None:
    words = [w.lower() for w in words]
    if not words:
        return None
    if words[0] in FRACTIONS:
        return FRACTIONS[words[0]], 1
    if words[0] == "a":
        if len(words) > 1 and words[1] in FRACTIONS:
            return FRACTIONS[words[1]], 2
        return None

    integer, n = _cardinal(words)
    value = float(integer) if integer is not None else None

    if n < len(words) and words[n] == "point":
        digits = []
        for w in words[n + 1:]:
            if w not in DIGITS:
                break
            digits.append(DIGITS[w])
        if digits:
            value = float(f"{integer or 0}.{''.join(digits)}")
            n += 1 + len(digits)

    if value is not None and words[n:n + 2] == ["and", "a"] and n + 2 < len(words) and words[n + 2] in FRACTIONS:
        value += FRACTIONS[words[n + 2]]
        n += 3

    return (value, n) if value is not None else None
