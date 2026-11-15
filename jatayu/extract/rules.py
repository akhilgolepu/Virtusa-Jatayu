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
# A procedure said with these before it was not done ("no IV access", "unable to get IO", "failed intubation").
PROCEDURE_NEGATION_CUES = NEGATION_CUES | {"unable", "failed", "couldn't", "cannot", "can't"}
# Lab and monitor words added in evaluator round 3 (dev context errors were all "serum magnesium 0.7"): a reading's
# qualifier, never something said about a dose given.
MEASUREMENT_CUES = {"blood", "bgl", "bsl", "sugar", "level", "levels", "reading", "sats", "sat", "saturation",
                    "saturations", "spo2", "serum", "plasma", "ionised", "ionized", "measured", "checked"}
LOW_CONFIDENCE = 0.95
FUZZY_CONFIDENCE_CAP = 0.94  # a fuzzy or phonetic drug match is always below LOW_CONFIDENCE, so always flagged
PHONETIC_THRESHOLD = 84  # rapidfuzz ratio between phonetic keys (chosen on dev transcripts, round 4)
SHARED_TIME_CONFIDENCE = 0.7
RANGE_JOINERS = {"to", "-", "or"}  # "2 to 4 mg", "2-4 mg", "2 or 4 mg": a range, not a dose given
REPEAT_CUES = {"another", "again", "repeat", "repeated"}  # "then another 2 mg": a second dose of the same drug


MASS_UNITS = {"mg", "mcg", "g", "units", "mmol", "mEq"}
VOLUME_UNITS = {"ml"}
# Words that are never a drug name when a number follows them: vital signs, quantities, verbs, time words, Hinglish.
NOT_DRUG_WORDS = {"pulse", "pressure", "rate", "heart", "resp", "respiratory", "temp", "temperature", "weight", "weighs",
                  "kilos", "kilo", "kgs", "years", "year", "aged", "score", "glasgow", "dose", "doses", "dosage", "total",
                  "bolus", "drip", "infusion", "over", "under", "about", "around", "approx", "approximately", "roughly",
                  "nearly", "almost", "maybe", "number", "room", "saturating", "systolic", "diastolic", "respirations",
                  "gave", "given", "give", "giving", "administered", "administer", "pushed", "push", "started", "start",
                  "repeat", "repeated", "another", "second", "third", "first", "then", "with", "from", "into", "litres",
                  "liters", "litre", "liter", "minutes", "minute", "hours", "hour", "seconds", "patient", "mareez",
                  "maine", "diya", "lagaya", "chadhaya", "phir", "abhi", "pehle", "baad", "wala", "wali", "gauge", "size",
                  "lead", "attempt", "attempts", "times", "only", "just", "also", "still", "again", "more", "less"}
# Common English words (4+ letters) that are never a drug name, whatever follows them.
ENGLISH_WORDS = set("""about above across actually after again against almost along already also although always among
another anyone anything around away back because been before behind being below beside besides best better between
both bring brought came cannot come could does doing done down during each either else enough even ever every first
from front gets give given going gone good have having here hers herself himself into itself just keep kept know last
later least left less like little look made make many maybe might more most much must near need never next none
nothing once only onto other others ought over past perhaps please quite rather really right same second seem seemed
shall should since some something still such sure take taken than that their them then there these they thing think
this those though three through thus till together told took toward towards under until upon very want wanted well
went were what whatever when where whether which while whole whom whose will with within without would yeah your
yours okay basically sort kind somewhat""".split())
ADMIN_VERBS = {"gave", "given", "give", "administered", "pushed", "push", "started", "start", "put", "injected"}
# Round 9. A drug matched only by sound (fuzzy or phonetic) with a similarity below this needs explicit acknowledgement
# on the confirm screen ("did you mean X?"), the heard word shown next to the recorded drug. The similarity is the
# heard word's SPELLING against the drug's nearest name or alias, so only a near-identical spelling ("furosmide") passes
# without it. Stated, not tuned: 0.95 is the existing LOW_CONFIDENCE line (eval/drug_identity.py has the dev numbers).
SOUND_ACK_BELOW = 0.95
# Round 9 junk guard for the unknown-drug rule. A word this similar (rapidfuzz ratio, letters only) to a route or unit
# term is a misheard route or unit, not a drug ("evipush" ~ "iv push", "intramascula"); misheard drugs on dev score <= 59.
ROUTE_LIKE = 75


def _common_words() -> frozenset[str]:
    """Ordinary English words: the whole-word tokens of the recogniser's own vocabulary minus lexicon words
    (jatayu/lexicon/common_words.txt, built by scripts/build_common_words.py)."""
    from importlib import resources

    text = resources.files("jatayu.lexicon").joinpath("common_words.txt").read_text("utf-8")
    return frozenset(w for w in text.split() if not w.startswith("#") and w.isalpha())


COMMON_ENGLISH = _common_words()
# Ordinary words the recogniser produces that must never be re-read as a drug name by sound.
COMMON_WORDS = {"minute", "minutes", "ago", "given", "gave", "patient", "right", "now", "just", "then", "and", "the",
                "after", "before", "pushed", "push", "started", "start", "time", "times", "about", "around", "into",
                "point", "sorry", "actually", "second", "seconds", "hour", "hours", "again", "another", "repeat",
                "because", "still", "pain", "score", "nausea", "chest", "blood", "level", "reading", "allergic"}


def sound_alike_flag(heard: str | None, recorded: str, score: float) -> Flag:
    """High: the drug was matched only by sound. The heard word stays in the drug field's raw text and is shown next to
    the recorded drug; confirming needs this flag ticked ("did you mean ...?")."""
    return Flag(code="sound_alike_drug", field="drug", severity="high",
                message=f"Heard '{heard}' — did you mean {recorded}? Matched by sound only (similarity {score:.2f}). "
                        "Confirm only if it is this drug; otherwise reject and re-dictate.")


def phonetic_key(word: str) -> str:
    """A crude English/Indian-English sound key: c/k/q, s/z, f/ph/v, i/y and doubled letters collapse; vowels after the
    first letter drop. Enough to match "ketool" to "ketorol" or "adenol card" to "adenocard", never used unflagged."""
    import re

    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    for a, b in (("ph", "f"), ("ck", "k"), ("q", "k"), ("x", "ks"), ("z", "s"), ("v", "f"), ("w", "f"),
                 ("dg", "j"), ("gh", "g"), ("y", "i")):
        w = w.replace(a, b)
    w = re.sub(r"c(?=[eiy])", "s", w).replace("c", "k")
    head, tail = w[0], re.sub(r"[aeiouh]", "", w[1:])
    return re.sub(r"(.)\1+", r"\1", head + tail)


def _cue_words(words: list[str]) -> set[str]:
    """Words as context cues: hyphenated tokens also count by their parts ("on-home" -> home), and a word of 4+ letters
    that SOUNDS like a cue of 5+ letters counts as that cue ("serm", "ceram" -> serum: ASR spellings on dev speech)."""
    out = set()
    for w in words:
        parts = [w, *w.split("-")] if "-" in w else [w]
        out.update(parts)
        for part in parts:
            if sum(c.isalpha() for c in part) >= 4:
                out.update(_CUE_BY_SOUND.get(phonetic_key(part), ()))
    return out


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
    known: bool = True  # False: a drug-like word that is not in the lexicon (canon = the word as spoken)
    score: float | None = None  # matched by sound (fuzzy / phonetic): the uncapped similarity; None = exact lexicon word


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
        # Words of every lexicon phrase (routes, units, procedures, drugs): never re-read as a misheard drug name.
        self._known_words = {t for toks in (tuple(t.text for t in normalise(ph).tokens) for ph, _, _ in lexicon.phrases())
                             for t in toks} | COMMON_WORDS
        self._phonetic_index = [(phonetic_key(t), canon) for t, kind, canon in lexicon.phrases() if kind == "drug"
                                and len(phonetic_key(t)) >= 4]
        self._drug_spellings: dict[str, set[str]] = defaultdict(set)
        for t, kind, canon in lexicon.phrases():
            if kind == "drug":
                self._drug_spellings[canon].add("".join(c for c in t.lower() if c.isalpha()))
        self._route_unit_terms = sorted({t.replace(" ", "") for t, kind, _ in lexicon.phrases()
                                         if kind in ("route", "unit") and sum(c.isalpha() for c in t) >= 4})

    # ---- matching -------------------------------------------------------------------------
    def _mentions(self, nt: NormalisedText, blocked: set[int]) -> list[Mention]:
        toks, out, i = nt.tokens, [], 0
        while i < len(toks):
            if i in blocked:
                i += 1
                continue
            hit = None
            raw_tok = nt.raw[toks[i].raw_start:toks[i].raw_end]
            if raw_tok == "IN" and not nt.raw.isupper():  # written "IN" = intranasal; the word "in" is not a route
                hit = Mention("route", "IN", i, i + 1, 1.0)
            for phrase, kind, canon in () if hit else self._by_first.get(toks[i].text, ()):
                j = i + len(phrase)
                if j <= len(toks) and tuple(t.text for t in toks[i:j]) == phrase and not blocked & set(range(i, j)):
                    hit = Mention(kind, canon, i, j, 1.0)
                    break
            if hit is None and toks[i].kind == "word" and sum(c.isalpha() for c in toks[i].text) >= 5:
                fz = self.lexicon.fuzzy_drug(toks[i].text, self.fuzzy_threshold)
                if fz:
                    hit = Mention("drug", fz[0], i, i + 1, min(fz[1], FUZZY_CONFIDENCE_CAP),
                                  score=self._spelling(toks[i].text, fz[0]))
            if hit is None and toks[i].kind == "word" and toks[i].text not in self._known_words:
                hit = self._phonetic(toks, i, blocked)
            if hit is None and self._unknown_drug(nt, i, blocked, after_dose=bool(out) and out[-1].kind == "unit"
                                                  and out[-1].j == i):
                hit = Mention("drug", toks[i].text, i, i + 1, 1.0, known=False)
            if hit:
                out.append(hit)
                i = hit.j
            else:
                i += 1
        return out

    def _unknown_drug(self, nt, i: int, blocked: set[int], after_dose: bool = False) -> bool:
        """A drug-like word the lexicon does not know, directly followed by a dose, a unit or a route ("gave tramadol
        50 mg IV"): it becomes an entry with the word as spoken and a drug_not_in_lexicon flag — never dropped."""
        toks = nt.tokens
        w = toks[i].text
        if (i in blocked or toks[i].kind != "word" or not w.isalpha() or len(w) < 4 or w in self._known_words
                or w in NOT_DRUG_WORDS or w in ENGLISH_WORDS or w in NEGATION_CUES | HOME_MED_CUES | MEASUREMENT_CUES
                or w in CORRECTIONS or i + 1 >= len(toks) or i + 1 in blocked):
            return False
        if self._route_like(w):  # round 9: a misheard route or unit ("evipush", "intramascula") is not a drug
            return False
        nxt = toks[i + 1]

        def follows_at(k: int) -> set[str]:
            return {kind for ph, kind, _ in self._by_first.get(toks[k].text, ())
                    if tuple(t.text for t in toks[k:k + len(ph)]) == ph} if k < len(toks) else set()

        if w in COMMON_ENGLISH:  # round 9: an ordinary word only with the full dose pattern after it ("spring 300 mg")
            return nxt.kind == "number" and i + 2 not in blocked and "unit" in follows_at(i + 2)
        if nxt.kind == "number":
            return True
        follows = follows_at(i + 1)
        # a route alone after a word is often a body site ("tibial IO"): only after an administration verb or a dose
        # ("gave X IV", "1 g X IV")
        return "unit" in follows or ("route" in follows and (after_dose or (i > 0 and toks[i - 1].text in ADMIN_VERBS)))

    def _route_like(self, word: str) -> bool:
        from rapidfuzz import fuzz, process

        return process.extractOne(word, self._route_unit_terms, scorer=fuzz.ratio, score_cutoff=ROUTE_LIKE) is not None

    def _phonetic(self, toks, i: int, blocked: set[int]) -> Mention | None:
        """A drug name the recogniser split or misspelt ("adenol card" -> adenocard, "ketool" -> ketorol): 1-3
        adjacent unknown words joined and compared by phonetic key. Confidence is capped, so it is always flagged."""
        from rapidfuzz import fuzz

        best = None
        for n in (1, 2, 3):
            j = i + n
            if j > len(toks) or any(k in blocked or toks[k].kind != "word" or toks[k].text in self._known_words
                                    for k in range(i, j)):
                break
            joined = "".join(t.text for t in toks[i:j])
            key = phonetic_key(joined)
            if sum(c.isalpha() for c in joined) < 5 or len(key) < 4:
                continue
            for k, canon in self._phonetic_index:
                score = fuzz.ratio(key, k)
                if score >= PHONETIC_THRESHOLD and (best is None or score > best[0]):
                    best = (score, canon, j)
        if best is None:
            return None
        joined = "".join(t.text for t in toks[i:best[2]])
        return Mention("drug", best[1], i, best[2], min(best[0] / 100.0, FUZZY_CONFIDENCE_CAP),
                       score=self._spelling(joined, best[1]))

    def _spelling(self, heard: str, canon: str) -> float:
        """How alike the heard letters are to the recorded drug's nearest name or alias as WRITTEN (0-1). A phonetic
        match can score 1.0 on sound while the words differ ("kettler" ~ ketalar); this is the number shown and
        compared with SOUND_ACK_BELOW."""
        from rapidfuzz import fuzz

        h = "".join(c for c in heard.lower() if c.isalpha())
        return max((fuzz.ratio(h, t) for t in self._drug_spellings.get(canon, ())), default=0.0) / 100.0

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
            parts = [(s, e)]
            cue = self._repeat_cue(nt, anchor, s, e, consumed) if anchor.kind == "drug" else None
            if cue is not None:
                parts = [(s, cue), (cue, e)]
            for n, (ps, pe) in enumerate(parts):
                seg_mentions = [m for m in mentions if ps <= m.i < pe]
                time_field, flags = self._time(nt, times, ps, pe, capture_time)
                if anchor.kind != "drug":
                    entries.append(self._procedure(nt, anchor, ps, pe, time_field, flags))
                    continue
                entry = self._medication(nt, anchor, seg_mentions, consumed, ps, pe, time_field, flags)
                if n == 1:
                    first = entries[-1]
                    entry.flags += [f for f in first.flags if f.code in ("possible_not_given", "possible_measurement")]
                    entry.flags.append(Flag(code="repeat_dose_inferred", field="drug", severity="medium",
                                            message=f"A second {anchor.canon} dose was read from "
                                                    f"'{nt.tokens[cue].text}'; check it was given."))
                entries.append(entry)
        return entries

    @staticmethod
    def _repeat_cue(nt, anchor, s, e, consumed) -> int | None:
        """'morphine 4 mg IV then another 2 mg': the cue index, if a dose was already said before it and another
        number follows it. The second dose becomes its own entry (flagged) instead of being dropped."""
        toks = nt.tokens
        for c in range(anchor.j, e):
            if toks[c].text in REPEAT_CUES:
                before = any(toks[k].kind == "number" and k not in consumed for k in range(s, c))
                after = any(toks[k].kind == "number" and k not in consumed for k in range(c + 1, min(e, c + 4)))
                if before and after:
                    return c
        return None

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
                                   raw=nt.raw[t.span[0]:t.span[1]]), \
                [Flag(code="time_borrowed", field="time", severity="medium",
                      message=f"Time '{nt.raw[t.span[0]:t.span[1]]}' was said in another part of the sentence; "
                              "check it applies here.")]
        return (Field[datetime](value=capture_time, span=None, confidence=1.0, source="rules"),
                [Flag(code="time_not_stated", field="time", severity="low",
                      message="No time stated; using capture time.")])

    def _medication(self, nt, anchor, seg_mentions, consumed, s, e, time_field, flags) -> MedicationEntry:
        toks = nt.tokens
        unit_at = {m.i: m for m in seg_mentions if m.kind == "unit"}
        nums = [k for k in range(s, e) if toks[k].kind == "number" and k not in consumed]
        # A correction ("4, no sorry, 2 mg") needs the marker *between* two numbers; "pain 8, no nausea" is not one.
        corrected = any(nums[0] < k < nums[-1] and toks[k].text in CORRECTIONS for k in range(s, e)) if nums else False
        if corrected:
            marker = max(k for k in range(s, e) if nums[0] < k < nums[-1] and toks[k].text in CORRECTIONS)
            after = min(k for k in nums if k > marker)
            before = max(k for k in nums if k < marker)
            flags.append(Flag(code="self_correction", field="dose_value", severity="low",
                              message=f"The speaker corrected the dose ({toks[before].text} -> {toks[after].text}); "
                                      "the later value is used."))
        concentration = self._concentration(nt, s, e, unit_at)
        if concentration is not None:
            nums = []  # numbers in a concentration ("1 in 10000", "0.6 mg per ml") are not a dose
        with_unit = [k for k in nums if k + 1 in unit_at]
        ambiguous = False
        stated_range = next(((a, b) for a, b in zip(nums, nums[1:]) if 0 < b - a <= 3 and all(
            toks[k].text in RANGE_JOINERS or (toks[k].text == "and" and a > 0 and toks[a - 1].text == "between")
            for k in range(a + 1, b))), None)
        if corrected:
            # the number right after the last correction marker ("800, sorry, 1000 mg ... 10 men ago" -> 1000), not
            # the last number of the clause (a misheard time can follow)
            marker = max(k for k in range(s, e) if nums[0] < k < nums[-1] and toks[k].text in CORRECTIONS)
            pick = min(k for k in nums if k > marker)
        elif with_unit:
            pick = with_unit[0]
        elif nums:
            # No unit anywhere: take the number nearest the drug, and flag the value itself if there was a choice.
            pick = min(nums, key=lambda k: (min(abs(k - anchor.i), abs(k - (anchor.j - 1))), k < anchor.i))
            ambiguous = len(nums) > 1
        else:
            pick = None

        drug = self._f(nt, anchor.canon, anchor.i, anchor.j, anchor.confidence)
        if not anchor.known:
            flags.append(Flag(code="drug_not_in_lexicon", field="drug", severity="high",
                              message=f"'{drug.raw}' is not in the drug list: nothing about it could be checked. Confirm the "
                                      "name, the dose and the route."))
        if concentration is not None:
            dose_value, dose_unit = Field.missing("rules"), Field.missing("rules")
            flags.append(Flag(code="concentration_not_dose", field="dose_value", severity="high",
                              message=f"'{concentration}' is a concentration, not a dose: enter the dose given."))
        elif pick is None:
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
        if stated_range:
            lo, hi = (toks[k].text for k in stated_range)
            flags.append(Flag(code="dose_range_stated", field="dose_value", severity="high",
                              message=f"A range ({lo} to {hi}) was said for {anchor.canon}, not one dose; enter the "
                                      "dose actually given."))
        if ambiguous:
            flags.append(Flag(code="ambiguous_dose", field="dose_value", severity="high",
                              message=f"Several numbers near {anchor.canon} and none has a unit; check the dose."))
        if anchor.known and anchor.score is not None and anchor.score < SOUND_ACK_BELOW:
            flags.append(sound_alike_flag(drug.raw, anchor.canon, anchor.score))
        elif anchor.known and anchor.confidence < LOW_CONFIDENCE:
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
        before = _cue_words(words[max(s, anchor.i - CONTEXT_WINDOW):anchor.i])
        after = _cue_words(words[anchor.j:min(e, anchor.j + 2)])
        segment = _cue_words(words[s:e])
        out = []
        if before & NEGATION_CUES or segment & HOME_MED_CUES:
            out.append(Flag(code="possible_not_given", field="drug", severity="high",
                            message=f"Context suggests {anchor.canon} may not have been given now "
                                    "(negation, allergy or regular medication)."))
        if (before | after) & MEASUREMENT_CUES:
            out.append(Flag(code="possible_measurement", field="drug", severity="high",
                            message=f"'{anchor.canon}' looks like a measurement, not a dose given."))
        return out

    @staticmethod
    def _concentration(nt, s: int, e: int, unit_at: dict) -> str | None:
        """The raw text of a concentration said in this clause, if any: a ratio ("1 in 10000", "1:1000") or an amount
        per volume ("0.6 mg per ml", "50 mg/ml"). Recorded as a concentration, never as the dose."""
        toks = nt.tokens
        for k in range(s, e - 2):
            a, mid, b = toks[k], toks[k + 1], toks[k + 2]
            if a.kind == "number" and mid.text in ("in", ":") and b.kind == "number" and b.value >= 100 and a.value <= 10:
                return nt.raw[slice(*nt.raw_span(k, k + 3))]
            if k in unit_at and unit_at[k].canon in MASS_UNITS:
                j = unit_at[k].j
                if j + 1 < e and toks[j].text in ("per", "/") and j + 1 in unit_at and unit_at[j + 1].canon in VOLUME_UNITS:
                    start = k - 1 if k > s and toks[k - 1].kind == "number" else k
                    return nt.raw[slice(*nt.raw_span(start, unit_at[j + 1].j))]
        return None

    def _procedure(self, nt, anchor, s, e, time_field, flags) -> ProcedureEntry:
        toks = nt.tokens
        detail = None
        for k in range(s, e - 1):
            if toks[k].text == "size" and toks[k + 1].kind == "number":
                detail = self._f(nt, nt.raw[slice(*nt.raw_span(k, k + 2))], k, k + 2)
                break
        words = [t.text for t in toks]
        if set(words[max(s, anchor.i - CONTEXT_WINDOW):anchor.i]) & PROCEDURE_NEGATION_CUES:
            flags.append(Flag(code="possible_not_given", field="procedure", severity="high",
                              message=f"Context suggests {anchor.canon} was not done (negation, or an attempt that failed)."))
        return ProcedureEntry(procedure=self._f(nt, anchor.canon, anchor.i, anchor.j, anchor.confidence),
                              time=time_field, detail=detail, flags=flags)


_CUE_BY_SOUND: dict[str, set[str]] = {}
for _cue in NEGATION_CUES | HOME_MED_CUES | MEASUREMENT_CUES:
    if len(_cue) >= 5 and _cue.isalpha() and len(phonetic_key(_cue)) >= 3:  # "without" -> "ft" would match "with"
        _CUE_BY_SOUND.setdefault(phonetic_key(_cue), set()).add(_cue)
