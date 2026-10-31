"""normalise(raw) -> tokens with offsets into the raw transcript; spoken numbers collapsed."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from jatayu.normalise.numbers import FRACTIONS, STARTERS, parse_spoken_number

# Devanagari range keeps vowel signs (combining marks \w misses) inside words; inner '.' keeps "i.m" whole.
TOKEN_RE = re.compile(r"\d+(?:\.\d+)?|[\wऀ-ॿ]+(?:[-'.][\wऀ-ॿ]+)*|[^\w\s]")

Span = tuple[int, int]


@dataclass
class Token:
    text: str
    raw_start: int
    raw_end: int
    kind: Literal["word", "number", "punct"]
    value: float | None = None


@dataclass
class NormalisedText:
    raw: str
    tokens: list[Token] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(t.text for t in self.tokens)

    def raw_span(self, i: int, j: int) -> Span:
        return (self.tokens[i].raw_start, self.tokens[j - 1].raw_end)


def _fmt(v: float) -> str:
    return f"{v:g}"


def _lex(raw: str) -> list[Token]:
    out = []
    for m in TOKEN_RE.finditer(raw):
        s = m.group()
        if s[0].isdigit():
            out.append(Token(s, m.start(), m.end(), "number", float(s)))
        elif s[0].isalnum() or "ऀ" <= s[0] <= "ॿ" or s[0] == "_":
            out.append(Token(s.lower(), m.start(), m.end(), "word"))
        else:
            out.append(Token(s, m.start(), m.end(), "punct"))
    return out


def normalise(raw: str) -> NormalisedText:
    toks = _lex(raw)
    out: list[Token] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.kind == "word" and t.text in STARTERS:
            run = []
            for u in toks[i:]:
                if u.kind != "word":
                    break
                run.append(u.text)
            hit = parse_spoken_number(run)
            if hit:
                value, n = hit
                out.append(Token(_fmt(value), t.raw_start, toks[i + n - 1].raw_end, "number", value))
                i += n
                continue
        if t.kind == "number":
            # "1 and a half"
            tail = [u.text for u in toks[i + 1:i + 4]]
            if len(tail) == 3 and tail[:2] == ["and", "a"] and tail[2] in FRACTIONS:
                value = t.value + FRACTIONS[tail[2]]
                out.append(Token(_fmt(value), t.raw_start, toks[i + 3].raw_end, "number", value))
                i += 4
                continue
            t = Token(_fmt(t.value), t.raw_start, t.raw_end, "number", t.value)
        out.append(t)
        i += 1
    return NormalisedText(raw, out)
