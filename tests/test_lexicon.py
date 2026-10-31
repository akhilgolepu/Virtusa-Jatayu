def test_alias_and_brand_lookup(lexicon):
    assert lexicon.lookup_drug("Adrenaline") == "epinephrine"
    assert lexicon.lookup_drug("emeset") == "ondansetron"
    assert lexicon.lookup_drug("D50") == "dextrose"
    assert lexicon.lookup_drug("banana") is None


def test_fuzzy_catches_asr_misspelling(lexicon):
    name, score = lexicon.fuzzy_drug("ondansatron", threshold=85)
    assert name == "ondansetron" and 0.85 <= score <= 1


def test_units_and_routes(lexicon):
    assert lexicon.canonical_unit("micrograms") == "mcg"
    assert lexicon.canonical_unit("cc") == "ml"
    assert lexicon.canonical_route("intramuscular") == "IM"
    assert lexicon.canonical_route("under the tongue") == "SL"
    assert lexicon.canonical_route("pushed") is None


def test_lexicon_sizes_and_integrity(lexicon):
    assert 25 <= len(lexicon.drug_names()) <= 40
    assert 10 <= len(lexicon.procedure_names()) <= 15
    for d in lexicon.drug_names():
        info = lexicon.drug(d)
        assert info.routes and info.units and info.atc
        assert set(info.routes) <= set(lexicon.route_codes())
        assert set(info.units) <= set(lexicon.unit_codes())


def test_no_alias_maps_to_two_things(lexicon):
    seen = {}
    for phrase, kind, canon in lexicon.phrases():
        assert seen.setdefault(phrase, (kind, canon)) == (kind, canon), phrase


def test_phrases_longest_first(lexicon):
    lens = [len(p[0]) for p in lexicon.phrases()]
    assert lens == sorted(lens, reverse=True)


def test_synonym_accessors(lexicon):
    assert "micrograms" in lexicon.unit_synonyms("mcg")
    assert "by mouth" in lexicon.route_synonyms("PO")
