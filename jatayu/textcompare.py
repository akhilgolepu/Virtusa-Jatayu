"""Normalised comparison of a reference and an ASR hypothesis: spoken/written number forms and unit/route
synonyms compare equal; drug words are left alone so a misheard drug still counts as an error."""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

import jiwer

from jatayu.lexicon import Lexicon
from jatayu.normalise.text import normalise


@lru_cache(maxsize=4)
def _unit_route_phrases(lexicon: Lexicon) -> dict[str, list[tuple[tuple[str, ...], str]]]:
    by_first: dict[str, list[tuple[tuple[str, ...], str]]] = defaultdict(list)
    for phrase, kind, canon in lexicon.phrases():
        if kind in ("unit", "route"):
            toks = tuple(t.text.lower() for t in normalise(phrase).tokens if t.kind != "punct")
            if toks:
                by_first[toks[0]].append((toks, canon.lower()))
    for cands in by_first.values():
        cands.sort(key=lambda c: len(c[0]), reverse=True)
    return by_first


def compare_tokens(text: str, lexicon: Lexicon) -> list[str]:
    words = [t.text.lower() for t in normalise(text).tokens if t.kind != "punct"]
    phrases = _unit_route_phrases(lexicon)
    out, i = [], 0
    while i < len(words):
        for toks, canon in phrases.get(words[i], ()):
            if tuple(words[i:i + len(toks)]) == toks:
                out.append(canon)
                i += len(toks)
                break
        else:
            out.append(words[i])
            i += 1
    return out


def normalised_wer(ref: str, hyp: str, lexicon: Lexicon) -> float:
    ref_t, hyp_t = compare_tokens(ref, lexicon), compare_tokens(hyp, lexicon)
    if not ref_t:
        return 0.0 if not hyp_t else 1.0
    if not hyp_t:
        return 1.0
    return float(jiwer.wer(" ".join(ref_t), " ".join(hyp_t)))
