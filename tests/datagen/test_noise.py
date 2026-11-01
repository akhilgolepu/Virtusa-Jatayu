import csv

import numpy as np
import pytest

from datagen.noise import ESC50, NOISE_CATEGORIES, mix_at_snr, noise_bank

needs_esc50 = pytest.mark.skipif(not (ESC50 / "meta" / "esc50.csv").exists(), reason="ESC-50 not downloaded")


def _snr(clean, mixed):
    noise = mixed - clean
    return 10 * np.log10(np.mean(clean ** 2) / np.mean(noise ** 2))


@pytest.mark.parametrize("snr", [20, 10, 5])
def test_mix_hits_target_snr(snr):
    rng = np.random.default_rng(0)
    t = np.arange(16000 * 2) / 16000
    speech = (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    noise = (0.05 * rng.standard_normal(16000)).astype(np.float32)  # shorter than speech -> must loop
    mixed = mix_at_snr(speech, noise, snr, np.random.default_rng(1))
    assert mixed.shape == speech.shape and np.abs(mixed).max() <= 0.99
    assert abs(_snr(speech, mixed) - snr) < 0.2


def test_deterministic_mix():
    speech = np.linspace(-0.1, 0.1, 8000, dtype=np.float32)
    noise = np.random.default_rng(3).standard_normal(20000).astype(np.float32) * 0.1
    a = mix_at_snr(speech, noise, 10, np.random.default_rng(5))
    b = mix_at_snr(speech, noise, 10, np.random.default_rng(5))
    assert np.array_equal(a, b)


@needs_esc50
def test_noise_bank_folds():
    folds = {r["filename"]: r["fold"] for r in csv.DictReader(open(ESC50 / "meta" / "esc50.csv"))}
    cats = {r["filename"]: r["category"] for r in csv.DictReader(open(ESC50 / "meta" / "esc50.csv"))}
    test_bank = noise_bank("test")
    assert test_bank and all(folds[p.name] == "5" for p in test_bank)
    assert all(folds[p.name] in "123" for p in noise_bank("train"))
    assert {cats[p.name] for p in test_bank} == set(NOISE_CATEGORIES)


@needs_esc50
def test_final_test_noise_comes_from_the_held_out_fold():
    folds = {r["filename"]: r["fold"] for r in csv.DictReader(open(ESC50 / "meta" / "esc50.csv"))}
    assert noise_bank("final_test") and all(folds[p.name] == "5" for p in noise_bank("final_test"))
