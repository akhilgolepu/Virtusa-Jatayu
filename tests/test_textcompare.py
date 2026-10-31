from jatayu.textcompare import compare_tokens, normalised_wer


def test_spoken_and_written_forms_compare_equal(lexicon):
    assert normalised_wer("gave point three milligrams of adrenaline I.M.", "Gave 0.3 mg of adrenaline IM", lexicon) == 0.0
    assert compare_tokens("four mg ondansetron intravenous", lexicon) == ["4", "mg", "ondansetron", "iv"]


def test_wrong_drug_counts(lexicon):
    assert normalised_wer("glucagon 1 mg IM", "crocodone 1 mg IM", lexicon) > 0


def test_empty_hypothesis_is_total_error(lexicon):
    assert normalised_wer("aspirin 300 mg", "", lexicon) == 1.0
