"""Find time mentions ("two mins ago", "at 10:42", "just now") and anchor them to the capture time."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from jatayu.normalise.text import NormalisedText, Span, Token

_UNITS = {
    **dict.fromkeys(["second", "seconds", "sec", "secs"], "seconds"),
    **dict.fromkeys(["minute", "minutes", "min", "mins"], "minutes"),
    **dict.fromkeys(["hour", "hours", "hr", "hrs"], "hours"),
}
_MERIDIEM = {"am": 0, "a.m": 0, "pm": 12, "p.m": 12}
_FUTURE_SLACK = timedelta(minutes=5)


@dataclass
class TimeMention:
    value: datetime
    tok_start: int
    tok_end: int
    span: Span


def _int(t: Token | None, lo: int, hi: int) -> int | None:
    if t is None or t.kind != "number" or t.value is None or not float(t.value).is_integer():
        return None
    v = int(t.value)
    return v if lo <= v <= hi else None


def _clock(capture: datetime, hour: int, minute: int, meridiem_known: bool) -> datetime:
    """Most recent past occurrence of hour:minute. Without am/pm, "2 30" may be 02:30 or 14:30."""
    hours = [hour] if meridiem_known or hour > 12 else [hour % 12, hour % 12 + 12]
    best = None
    for h in hours:
        at = capture.replace(hour=h, minute=minute, second=0, microsecond=0)
        if at > capture + _FUTURE_SLACK:
            at -= timedelta(days=1)
        if best is None or at > best:
            best = at
    return best


def _match(nt: NormalisedText, i: int, capture: datetime) -> tuple[datetime, int] | None:
    toks = nt.tokens
    tok = lambda k: toks[k] if k < len(toks) else None  # noqa: E731
    word = lambda k: toks[k].text if k < len(toks) and toks[k].kind != "number" else None  # noqa: E731

    # <n> minutes ago / a minute ago / an hour ago
    if word(i + 1) in _UNITS and word(i + 2) == "ago":
        if toks[i].kind == "number":
            return capture - timedelta(**{_UNITS[word(i + 1)]: toks[i].value}), i + 3
        if word(i) in ("a", "an"):
            return capture - timedelta(**{_UNITS[word(i + 1)]: 1}), i + 3

    if word(i) in ("just", "right") and word(i + 1) == "now":
        return capture, i + 2

    if word(i) == "at" and (hour := _int(tok(i + 1), 0, 23)) is not None:
        j = i + 2
        minute = 0
        if word(j) == ":" and (m := _int(tok(j + 1), 0, 59)) is not None:
            minute, j = m, j + 2
        elif (m := _int(tok(j), 0, 59)) is not None:
            raw_min = nt.raw[toks[j].raw_start:toks[j].raw_end]
            if len(raw_min) == 2 or not raw_min.isdigit():  # "at 10 42" or "at ten forty two"
                minute, j = m, j + 1
        meridiem_known = word(j) in _MERIDIEM
        if meridiem_known:
            if hour > 12:
                return None
            hour = hour % 12 + _MERIDIEM[word(j)]
            j += 1
        elif j == i + 2:  # bare "at 10" with neither minutes nor am/pm is not a clock time
            return None
        return _clock(capture, hour, minute, meridiem_known), j
    return None


def find_times(nt: NormalisedText, capture_time: datetime) -> list[TimeMention]:
    out, i = [], 0
    while i < len(nt.tokens):
        hit = _match(nt, i, capture_time)
        if hit:
            value, end = hit
            out.append(TimeMention(value, i, end, nt.raw_span(i, end)))
            i = end
        else:
            i += 1
    return out
