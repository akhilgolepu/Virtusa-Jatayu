from datetime import datetime, timedelta

from jatayu.normalise.text import normalise
from jatayu.normalise.timeparse import find_times

CAP = datetime(2026, 10, 31, 10, 45, 0).astimezone()


def test_minutes_ago():
    raw = "gave 0.3 of adrenaline IM, two mins ago"
    [m] = find_times(normalise(raw), CAP)
    assert m.value == CAP - timedelta(minutes=2) and raw[slice(*m.span)] == "two mins ago"


def test_clock_time_not_dose():
    raw = "at 10 42 gave 2 mg morphine IV"
    nt = normalise(raw)
    [m] = find_times(nt, CAP)
    assert (m.value.hour, m.value.minute) == (10, 42)
    assert raw[slice(*m.span)] == "at 10 42"


def test_clock_with_colon_and_future_rolls_back_a_day():
    [m] = find_times(normalise("at 23:50 started CPR"), CAP)
    assert m.value.date() == (CAP - timedelta(days=1)).date()


def test_no_time():
    assert find_times(normalise("gave aspirin"), CAP) == []


def test_just_now_and_an_hour_ago():
    a, b = find_times(normalise("aspirin just now, morphine an hour ago"), CAP)
    assert a.value == CAP and b.value == CAP - timedelta(hours=1)


def test_clock_without_meridiem_picks_most_recent():
    cap = datetime(2026, 10, 31, 14, 45).astimezone()
    [m] = find_times(normalise("at 2 30 gave adrenaline 1 mg IV"), cap)
    assert (m.value.hour, m.value.minute, m.value.date()) == (14, 30, cap.date())
    [m] = find_times(normalise("at 10 42 gave morphine"), CAP)
    assert (m.value.hour, m.value.minute) == (10, 42)


def test_whisper_dotted_clock_after_at():
    [m] = find_times(normalise("ativan 1 mg at 10.12."), CAP)
    assert (m.value.hour, m.value.minute) == (10, 12)
    assert find_times(normalise("adrenaline 0.3 mg"), CAP) == []
    assert find_times(normalise("at 10.75 something"), CAP) == []
