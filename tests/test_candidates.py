from datetime import datetime

from jatayu.extract.rules import RulesExtractor

CAP = datetime(2026, 10, 31, 10, 45).astimezone()


def test_candidates_cover_every_mention_in_order(lexicon):
    raw = "gave 0.3 mg adrenaline IM at 10:42"
    cands = RulesExtractor(lexicon).candidates(raw, CAP)
    assert [c.kind for c in cands] == ["number", "unit", "drug", "route", "time"]
    assert [c.id for c in cands] == [1, 2, 3, 4, 5]
    for c in cands:
        assert raw[c.span[0]:c.span[1]] == c.text
    assert cands[0].value == 0.3 and cands[2].value == "epinephrine" and cands[4].value.hour == 10


def test_numbers_inside_phrases_and_times_are_not_candidates(lexicon):
    raw = "12 lead done at 10 42, then 4 mg ondansetron IV"
    kinds = [(c.kind, c.text) for c in RulesExtractor(lexicon).candidates(raw, CAP)]
    assert ("procedure", "12 lead") in kinds and ("number", "4") in kinds
    assert ("number", "12") not in kinds and ("number", "42") not in kinds


def test_detail_candidate(lexicon):
    cands = RulesExtractor(lexicon).candidates("tubed with a size 7.5 tube", CAP)
    assert ("detail", "size 7.5") in [(c.kind, c.text) for c in cands]
