"""Lexicon + regex extractor. Every value it emits points at the raw transcript words it came from."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from jatayu.lexicon import Lexicon
from jatayu.models import Entry, Field, Flag, MedicationEntry, ProcedureEntry
from jatayu.normalise.text import NormalisedText, normalise
from jatayu.normalise.timeparse import TimeMention, find_times

SEPARATORS = {"and", ",", "then", ";", "."}
CORRECTIONS = {"no", "sorry", "actually", "mean"}  # "mean" covers "I mean"
CONTEXT_WINDOW = 4  # tokens before a drug name searched for negation / measurement cues
NEGATION_CUES = {"not", "no", "didn't", "never", "without", "allergic", "allergy", "allergies",
                 "held", "withheld", "refused", "declined", "contraindicated"}
HOME_MED_CUES = {"takes", "taking", "daily", "regularly", "prescribed", "home"}
MEASUREMENT_CUES = {"blood", "bgl", "bsl", "sugar", "level", "levels", "reading", "sats", "sat", "saturation",
                    "saturations", "spo2"}
LOW_CONFIDENCE = 0.95
SHARED_TIME_CONFIDENCE = 0.7


@dataclass
class Candidate:
    """A span the rules layer found in the raw transcript; the hybrid LLM may only link these."""
    id: int
    kind: str  # drug | procedure | number | unit | route | time | detail
    text: str
    span: tuple[int, int]
    value: object
    confidence: float


@dataclass
class Mention:
    kind: str  # drug | procedure | unit | route
    canon: str
    i: int
    j: int
    confidence: float


class RulesExtractor:
    name = "rules"

    def __init__(self, lexicon: Lexicon, fuzzy_threshold: int = 88):
        self.lexicon = lexicon
        self.fuzzy_threshold = fuzzy_threshold
        # Phrases go through the same normaliser as transcripts, so "twelve lead" and "12 lead" match alike.
        self._by_first: dict[str, list[tuple[tuple[str, ...], str, str]]] = defaultdict(list)
        for phrase, kind, canon in lexicon.phrases():
            toks = tuple(t.text for t in normalise(phrase).tokens)
            if toks:
                self._by_first[toks[0]].append((toks, kind, canon))
        for cands in self._by_first.values():
            cands.sort(key=lambda c: len(c[0]), reverse=True)

    # ---- matching -------------------------------------------------------------------------
    def _mentions(self, nt: NormalisedText, blocked: set[int]) -> list[Mention]:
        toks, out, i = nt.tokens, [], 0
        while i < len(toks):
            if i in blocked:
                i += 1
                continue
            hit = None
            for phrase, kind, canon in self._by_first.get(toks[i].text, ()):
                j = i + len(phrase)
                if j <= len(toks) and tuple(t.text for t in toks[i:j]) == phrase and not blocked & set(range(i, j)):
                    hit = Mention(kind, canon, i, j, 1.0)
                    break
            if hit is None and toks[i].kind == "word" and sum(c.isalpha() for c in toks[i].text) >= 5:
                fz = self.lexicon.fuzzy_drug(toks[i].text, self.fuzzy_threshold)
                if fz:
                    hit = Mention("drug", fz[0], i, i + 1, fz[1])
            if hit:
                out.append(hit)
                i = hit.j
            else:
                i += 1
        return out

    # ---- segmentation ---------------------------------------------------------------------
    @staticmethod
    def _segments(nt: NormalisedText, anchors: list[Mention], mention_at: dict[int, Mention],
                  time_at: dict[int, TimeMention]) -> list[tuple[int, int]]:
        toks = nt.tokens
        bounds = [0]
        for a, b in zip(anchors, anchors[1:]):
            seps = [k for k in range(a.j, b.i) if toks[k].text in SEPARATORS]
            if seps:
                bounds.append(seps[-1])
                continue
            # No separator: the dose/unit/route/time chain right after anchor a belongs to a.
            k = a.j
            while k < b.i:
                if k in time_at:
                    k = time_at[k].tok_end
                elif k in mention_at and mention_at[k].kind in ("unit", "route"):
                    k = mention_at[k].j
                elif toks[k].kind == "number":
                    k += 1
                else:
                    break
            bounds.append(k)
        bounds.append(len(toks))
        return list(zip(bounds, bounds[1:]))

    # ---- candidates (for the hybrid extractor) --------------------------------------------
    def candidates(self, raw: str, capture_time: datetime) -> list[Candidate]:
        nt = normalise(raw)
        times = find_times(nt, capture_time)
        time_tokens = {k for t in times for k in range(t.tok_start, t.tok_end)}
        mentions = self._mentions(nt, time_tokens)
        consumed = time_tokens | {k for m in mentions for k in range(m.i, m.j)}
        found: list[tuple[tuple[int, int], str, object, float]] = []
        for m in mentions:
            found.append((nt.raw_span(m.i, m.j), m.kind, m.canon, m.confidence))
        for t in times:
            found.append((t.span, "time", t.value, 1.0))
        toks = nt.tokens
        detail_tokens = set()
        for k in range(len(toks) - 1):
            if toks[k].text == "size" and toks[k + 1].kind == "number" and k + 1 not in consumed:
                span = nt.raw_span(k, k + 2)
                found.append((span, "detail", raw[span[0]:span[1]], 1.0))
                detail_tokens.add(k + 1)
        for k, t in enumerate(toks):
            if t.kind == "number" and k not in consumed and k not in detail_tokens:
                found.append((nt.raw_span(k, k + 1), "number", t.value, 1.0))
        found.sort(key=lambda f: f[0])
        return [Candidate(i + 1, kind, raw[span[0]:span[1]], span, value, conf)
                for i, (span, kind, value, conf) in enumerate(found)]

    # ---- extraction -----------------------------------------------------------------------
    def extract(self, raw: str, capture_time: datetime) -> list[Entry]:
        nt = normalise(raw)
        times = find_times(nt, capture_time)
        time_tokens = {k for t in times for k in range(t.tok_start, t.tok_end)}
        mentions = self._mentions(nt, time_tokens)
        anchors = [m for m in mentions if m.kind in ("drug", "procedure")]
        if not anchors:
            return []
        mention_at = {m.i: m for m in mentions}
        consumed = time_tokens | {k for m in mentions for k in range(m.i, m.j)}
        time_at = {t.tok_start: t for t in times}

        entries: list[Entry] = []
        for anchor, (s, e) in zip(anchors, self._segments(nt, anchors, mention_at, time_at)):
            seg_mentions = [m for m in mentions if s <= m.i < e]
            time_field, flags = self._time(nt, times, s, e, capture_time)
            if anchor.kind == "drug":
                entries.append(self._medication(nt, anchor, seg_mentions, consumed, s, e, time_field, flags))
            else:
                entries.append(self._procedure(nt, anchor, s, e, time_field, flags))
        return entries

    def _f(self, nt: NormalisedText, value, i: int, j: int, confidence: float = 1.0) -> Field:
        span = nt.raw_span(i, j)
        return Field(value=value, span=span, confidence=confidence, source="rules", raw=nt.raw[span[0]:span[1]])

    def _time(self, nt, times, s, e, capture_time):
        inside = [t for t in times if s <= t.tok_start < e]
        if inside:
            t = inside[0]
            return Field[datetime](value=t.value, span=t.span, confidence=1.0, source="rules",
                                   raw=nt.raw[t.span[0]:t.span[1]]), []
        if len(times) == 1:
            t = times[0]
            return Field[datetime](value=t.value, span=t.span, confidence=SHARED_TIME_CONFIDENCE, source="rules",
                                   raw=nt.raw[t.span[0]:t.span[1]]), []
        return (Field[datetime](value=capture_time, span=None, confidence=1.0, source="rules"),
                [Flag(code="time_not_stated", field="time", severity="low",
                      message="No time stated; using capture time.")])

    def _medication(self, nt, anchor, seg_mentions, consumed, s, e, time_field, flags) -> MedicationEntry:
        toks = nt.tokens
        unit_at = {m.i: m for m in seg_mentions if m.kind == "unit"}
        nums = [k for k in range(s, e) if toks[k].kind == "number" and k not in consumed]
        # A correction ("4, no sorry, 2 mg") needs the marker *between* two numbers; "pain 8, no nausea" is not one.
        corrected = any(nums[0] < k < nums[-1] and toks[k].text in CORRECTIONS for k in range(s, e)) if nums else False
        with_unit = [k for k in nums if k + 1 in unit_at]
        ambiguous = False
        if corrected:
            pick = nums[-1]
        elif with_unit:
            pick = with_unit[0]
        elif nums:
            # No unit anywhere: take the number nearest the drug, and flag the value itself if there was a choice.
            pick = min(nums, key=lambda k: (min(abs(k - anchor.i), abs(k - (anchor.j - 1))), k < anchor.i))
            ambiguous = len(nums) > 1
        else:
            pick = None

        drug = self._f(nt, anchor.canon, anchor.i, anchor.j, anchor.confidence)
        if pick is None:
            dose_value, dose_unit = Field.missing("rules"), Field.missing("rules")
            flags.append(Flag(code="field_missing", field="dose_value", severity="high",
                              message=f"No dose stated for {anchor.canon}."))
        else:
            dose_value = self._f(nt, toks[pick].value, pick, pick + 1)
            if pick + 1 in unit_at:
                u = unit_at[pick + 1]
                dose_unit = self._f(nt, u.canon, u.i, u.j)
            else:
                dose_unit = Field.missing("rules")
                flags.append(Flag(code="field_missing", field="dose_unit", severity="high",
                                  message=f"Dose for {anchor.canon} has no unit."))

        routes = [m for m in seg_mentions if m.kind == "route"]
        if routes:
            route = self._f(nt, routes[0].canon, routes[0].i, routes[0].j)
        else:
            route = Field.missing("rules")
            flags.append(Flag(code="field_missing", field="route", severity="medium",
                              message=f"No route stated for {anchor.canon}."))
        if ambiguous:
            flags.append(Flag(code="ambiguous_dose", field="dose_value", severity="high",
                              message=f"Several numbers near {anchor.canon} and none has a unit; check the dose."))
        if anchor.confidence < LOW_CONFIDENCE:
            flags.append(Flag(code="low_confidence", field="drug", severity="medium",
                              message=f"Drug name matched approximately ({anchor.confidence:.2f})."))
        flags.extend(self._context_flags(nt, anchor, s, e))
        return MedicationEntry(drug=drug, dose_value=dose_value, dose_unit=dose_unit, route=route,
                               time=time_field, flags=flags)

    @staticmethod
    def _context_flags(nt, anchor, s, e) -> list[Flag]:
        """Words around a drug that suggest it was NOT administered now: negation, allergy, home medication,
        or a measurement ("blood glucose 3.2", "O2 sats 88"). Flag high; never silently drop or keep."""
        words = [t.text for t in nt.tokens]
        before = set(words[max(s, anchor.i - CONTEXT_WINDOW):anchor.i])
        after = set(words[anchor.j:min(e, anchor.j + 2)])
        segment = set(words[s:e])
        out = []
        if before & NEGATION_CUES or segment & HOME_MED_CUES:
            out.append(Flag(code="possible_not_given", field="drug", severity="high",
                            message=f"Context suggests {anchor.canon} may not have been given now "
                                    "(negation, allergy or regular medication)."))
        if (before | after) & MEASUREMENT_CUES:
            out.append(Flag(code="possible_measurement", field="drug", severity="high",
                            message=f"'{anchor.canon}' looks like a measurement, not a dose given."))
        return out

    def _procedure(self, nt, anchor, s, e, time_field, flags) -> ProcedureEntry:
        toks = nt.tokens
        detail = None
        for k in range(s, e - 1):
            if toks[k].text == "size" and toks[k + 1].kind == "number":
                detail = self._f(nt, nt.raw[slice(*nt.raw_span(k, k + 2))], k, k + 2)
                break
        return ProcedureEntry(procedure=self._f(nt, anchor.canon, anchor.i, anchor.j, anchor.confidence),
                              time=time_field, detail=detail, flags=flags)
