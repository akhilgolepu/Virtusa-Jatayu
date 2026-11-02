"""Scoring-side ASR text: reference and hypothesis go through the SAME normalisation before WER.

The templates write numbers both ways ("nine eighteen", "9:18") and units in many spellings ("mgs", "milligrammes");
Whisper writes digits and its own unit spelling. Without this, "seven point five mgs" vs "7.5 MGS" counts as three
word errors although the words heard are identical. Numbers go through the pipeline's own normaliser, unit and route
words map to their lexicon code, punctuation is dropped.
"""
from __future__ import annotations

import jiwer

from jatayu.lexicon import Lexicon
from jatayu.normalise import normalise


def asr_norm(text: str, lex: Lexicon) -> str:
    out = []
    for t in normalise(text).tokens:
        if t.kind == "punct":
            continue
        w = t.text
        if t.kind == "word":
            w = w.replace(".", "")  # "i.v" -> "iv"
            code = lex.canonical_unit(w) or lex.canonical_route(w)
            w = code.lower() if code else w
        out.append(w)
    return " ".join(out)


def word_errors(ref: str, hyp: str) -> tuple[int, int]:
    """(edit operations, reference words) for already-normalised strings."""
    n = len(ref.split())
    if not n:
        return len(hyp.split()), 0
    o = jiwer.process_words(ref, hyp or "_")
    return o.substitutions + o.deletions + o.insertions, n


def drugs_heard(text: str, lex: Lexicon) -> set[str]:
    """Canonical drugs whose name or alias appears verbatim (1-3 words) in the normalised text."""
    words = asr_norm(text, lex).split()
    found = set()
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            d = lex.lookup_drug(" ".join(words[i:i + n]))
            if d:
                found.add(d)
    return found
