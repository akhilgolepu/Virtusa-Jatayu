"""Mix ESC-50 ambulance-scene noise into TTS speech at fixed SNRs, with fold-separated noise banks."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

from jatayu import config
from jatayu.audio import SAMPLE_RATE, decode_to_16k

ESC50 = config.DATA_DIR / "raw" / "ESC-50-master"
NOISE_CATEGORIES = ("siren", "engine", "car_horn", "train", "helicopter", "rain", "wind", "crying_baby",
                    "coughing", "breathing")
FOLDS = {"train": {"1", "2", "3"}, "dev": {"4"}, "test": {"5"}}  # no noise clip is shared between splits
SNRS = (20, 10, 5)
_MIN_POWER = 1e-10


def noise_bank(split: str) -> list[Path]:
    with open(ESC50 / "meta" / "esc50.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return sorted(ESC50 / "audio" / r["filename"] for r in rows
                  if r["category"] in NOISE_CATEGORIES and r["fold"] in FOLDS[split])


@lru_cache(maxsize=512)
def _noise_samples(path: Path) -> np.ndarray:
    samples, _ = decode_to_16k(path.read_bytes())
    return samples


def mix_at_snr(speech: np.ndarray, noise: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    """speech + noise scaled so 10*log10(P_speech / P_noise) == snr_db over the speech length. The noise is
    looped/cropped from a random offset; the sum is peak-limited to 0.99 (uniform scaling keeps the SNR)."""
    speech = np.asarray(speech, dtype=np.float32)
    p_speech = float(np.mean(speech ** 2))
    if p_speech < _MIN_POWER:
        return speech.copy()
    reps = int(np.ceil((len(speech) + len(noise)) / len(noise)))
    looped = np.tile(np.asarray(noise, dtype=np.float32), reps)
    start = int(rng.integers(0, len(noise)))
    seg = looped[start:start + len(speech)]
    p_noise = float(np.mean(seg ** 2))
    if p_noise < _MIN_POWER:
        raise ValueError("noise segment is silent")
    scale = np.sqrt(p_speech / (p_noise * 10 ** (snr_db / 10)))
    mixed = speech + scale * seg
    peak = float(np.abs(mixed).max())
    if peak > 0.99:
        mixed *= 0.99 / peak
    return mixed.astype(np.float32)


def _read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768


def _write_wav(path: Path, samples: np.ndarray) -> None:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(buf.getvalue())
    tmp.replace(path)


def build_noisy(split: str, tts_rows: list[dict], tts_root: Path, out_root: Path, seed: int) -> list[dict]:
    """For every TTS clip and every SNR, mix one noise clip from this split's bank. Resumable."""
    bank = noise_bank(split)
    categories = {r["filename"]: r["category"] for r in csv.DictReader(open(ESC50 / "meta" / "esc50.csv"))}
    rows = []
    for row in tts_rows:
        speech = None
        clip_key = int.from_bytes(hashlib.sha256(row["path"].encode()).digest()[:8], "big")
        for snr in SNRS:
            rng = np.random.default_rng([seed, snr, clip_key])
            noise_path = bank[int(rng.integers(0, len(bank)))]
            for _ in range(5):  # a mostly-silent ESC-50 clip can yield a silent segment; draw another
                rel = Path(split) / str(snr) / f"{Path(row['path']).stem}__{categories[noise_path.name]}.wav"
                out = Path(out_root) / rel
                if out.exists():
                    break
                speech = _read_wav(Path(tts_root) / row["path"]) if speech is None else speech
                try:
                    mixed = mix_at_snr(speech, _noise_samples(noise_path), snr, rng)
                except ValueError:
                    noise_path = bank[int(rng.integers(0, len(bank)))]
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                _write_wav(out, mixed)
                break
            cat = categories[noise_path.name]
            rows.append({**row, "path": str(rel), "snr_db": snr, "noise_file": noise_path.name,
                         "noise_category": cat})
    (Path(out_root) / f"{split}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return rows
