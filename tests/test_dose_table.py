def test_every_range_is_consistent_and_cited(lexicon):
    n = 0
    for drug in lexicon.drug_names():
        info = lexicon.drug(drug)
        for r in info.dose_ranges:
            n += 1
            assert r.route in info.routes and r.unit in info.units, (drug, r)
            assert r.source.strip(), (drug, r)
            if r.min is not None and r.max is not None:
                assert r.min <= r.max, (drug, r)
            assert r.min is not None or r.max is not None or r.per_kg is not None, (drug, r)
    assert n >= 150


def test_epinephrine_im_range(lexicon):
    rows = lexicon.dose_ranges("epinephrine", "IM")
    assert rows and any(r.min is not None and r.min <= 0.3 <= r.max for r in rows if r.unit == "mg")
    assert all(r.max is not None and r.max < 5 for r in rows if r.unit == "mg")


def test_min_repeat_is_the_smallest_stated_interval(lexicon):
    assert lexicon.min_repeat_s("epinephrine", "IM") == 300
    assert lexicon.min_repeat_s("atropine", "IV") == 180
    assert lexicon.min_repeat_s("furosemide", "IV") is None
    assert lexicon.min_repeat_s("salbutamol", "NEB") == 0


def test_secondary_rows_are_marked(lexicon):
    assert any(r.secondary for r in lexicon.dose_ranges("tranexamic acid", "IV"))
    assert not any(r.secondary for r in lexicon.dose_ranges("aspirin", "PO"))
