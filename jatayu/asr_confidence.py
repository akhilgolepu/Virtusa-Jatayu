"""low_asr_confidence: a drug, dose or unit read from words Whisper itself was unsure of is flagged, never trusted
silently. Word probabilities come from AsrResult.words (offsets into the transcript the extractor read)."""
from __future__ import annotations

from jatayu import config
from jatayu.models import Entry, Flag

CHECKED = ("drug", "dose_value", "dose_unit")


def lowest(words: list[dict], span: tuple[int, int] | None) -> dict | None:
    """The least probable recognised word overlapping a transcript span."""
    if span is None:
        return None
    hits = [w for w in words if w["start_char"] < span[1] and w["end_char"] > span[0]]
    return min(hits, key=lambda w: w["p"]) if hits else None


def flag_low_confidence(entries: list[Entry], words: list[dict],
                        threshold: float = config.ASR_WORD_PROB_THRESHOLD) -> list[Entry]:
    if not words:
        return entries
    out = []
    for e in entries:
        flags = list(e.flags)
        for name in CHECKED:
            f = getattr(e, name, None)
            w = lowest(words, f.span) if f is not None and f.source != "user" else None
            if w is not None and w["p"] < threshold:
                flags.append(Flag(code="low_asr_confidence", field=name, severity="medium",
                                  message=f"The speech recogniser was unsure of '{w['word']}' (p = {w['p']:.2f}); "
                                          "check it against the audio."))
        out.append(e.model_copy(update={"flags": flags}) if len(flags) != len(e.flags) else e)
    return out
