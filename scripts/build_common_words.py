"""python -m scripts.build_common_words   (round 9, item 2; run once, output committed)

Writes jatayu/lexicon/common_words.txt: the ordinary English words of the recogniser's own vocabulary — every
whole-word token (a token that starts a word and is all letters) of faster-whisper small.en's BPE tokenizer, lower-cased,
minus every word of a lexicon phrase (drug, procedure, route, unit). These are the frequent words of Whisper's training
text, the words it falls back to when it mishears. The rules NER reads such a word as an unknown drug only when a dose
and a unit follow it ("spring 300 mg"), never on a bare number or a route ("fine mg", "rise intramuscular")."""
from __future__ import annotations

import json
import sys

from jatayu import config
from jatayu.lexicon import Lexicon
from jatayu.normalise.text import normalise

OUT = config.ROOT / "jatayu" / "lexicon" / "common_words.txt"


def main() -> int:
    vocab = json.loads((config.ASR_MODEL_DIR / "tokenizer.json").read_text(encoding="utf-8"))["model"]["vocab"]
    words = {k[1:].lower() for k in vocab if k.startswith("Ġ") and k[1:].isascii() and k[1:].isalpha()}
    lexicon_words = {t.text for ph, _, _ in Lexicon.load().phrases() for t in normalise(ph).tokens}
    keep = sorted(words - lexicon_words)
    OUT.write_text(f"# {len(keep)} words: whole-word tokens of {config.ASR_MODEL_DIR.name}/tokenizer.json minus lexicon "
                   "words; built by scripts/build_common_words.py\n" + "\n".join(keep) + "\n", encoding="utf-8")
    print(len(words), "whole-word tokens;", len(words & lexicon_words), "lexicon words removed;", len(keep), "written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
