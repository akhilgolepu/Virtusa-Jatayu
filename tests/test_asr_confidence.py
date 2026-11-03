from datetime import datetime

from jatayu.asr import fit_prompt, vocabulary_terms
from jatayu.asr_confidence import flag_low_confidence
from jatayu.extract.rules import RulesExtractor


def test_low_probability_dose_word_is_flagged(lexicon):
    text = "gave 5 mg morphine IV"
    [e] = RulesExtractor(lexicon).extract(text, datetime.now().astimezone())
    words = [{"word": w, "start_char": text.index(w), "end_char": text.index(w) + len(w), "p": p}
             for w, p in (("gave", 0.99), ("5", 0.31), ("mg", 0.97), ("morphine", 0.95), ("IV", 0.9))]
    [f] = flag_low_confidence([e], words, threshold=0.5)
    hits = [x for x in f.flags if x.code == "low_asr_confidence"]
    assert [x.field for x in hits] == ["dose_value"] and "0.31" in hits[0].message
    assert flag_low_confidence([e], words, threshold=0.2)[0].flags == e.flags  # nothing below 0.2
    assert flag_low_confidence([e], [], threshold=0.9)[0] is e  # typed text: no word probabilities, no flag


def test_low_asr_confidence_catches_a_dangerous_error():
    from eval.metrics import is_dangerous
    assert not is_dangerous(["dose_value"], ["low_asr_confidence"])


def test_prompt_fits_the_whisper_budget(lexicon):
    count = lambda s: len(s.split())  # noqa: E731
    prompt, dropped = fit_prompt("Head.", vocabulary_terms(lexicon, True), count, limit=60)
    assert count(prompt) <= 60 and dropped and prompt.startswith("Head. Drugs: epinephrine")
    assert vocabulary_terms(lexicon, False) == lexicon.drug_names()
