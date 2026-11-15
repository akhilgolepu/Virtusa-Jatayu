"""Paths, offline switches and defaults. Import this before any model library."""
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "jatayu.sqlite"

ASR_MODEL_DIR = MODELS_DIR / "asr/faster-whisper-small.en"
# Chosen by scripts/smoke_gpu.py on the demo laptop (RTX 5060): RESULT device=cuda compute_type=int8_float16
ASR_DEVICE = os.environ.get("JATAYU_ASR_DEVICE", "cuda")
ASR_COMPUTE_TYPE = os.environ.get("JATAYU_ASR_COMPUTE", "int8_float16")
ASR_PROMPT_ALIASES = os.environ.get("JATAYU_ASR_PROMPT_ALIASES", "0") == "1"  # set from the round-4 dev comparison
# Words Whisper heard with probability below this get a low_asr_confidence flag (threshold chosen on dev, round 4)
ASR_WORD_PROB_THRESHOLD = float(os.environ.get("JATAYU_ASR_WORD_P", "0.2"))

DISCLAIMER = "Decision-support demo, not a clinical device."

READBACK_VOICE = MODELS_DIR / "tts/en/en_US/lessac/medium/en_US-lessac-medium.onnx"

DEFAULT_EXTRACTOR = os.environ.get("JATAYU_EXTRACTOR", "rules")  # rules (default, round 5) | hybrid
# LLM-only extraction is EXPERIMENTAL (round 9): it is off the demo path, has none of the round-8/9 safety fixes, and
# is offered by the app only when JATAYU_EXPERIMENTAL=1. The evaluation harness can still score it on dev.
DEMO_EXTRACTORS = ("rules", "hybrid")
EXPERIMENTAL_EXTRACTORS = ("llm",)
EXPERIMENTAL = os.environ.get("JATAYU_EXPERIMENTAL", "0") == "1"
if DEFAULT_EXTRACTOR not in DEMO_EXTRACTORS + (EXPERIMENTAL_EXTRACTORS if EXPERIMENTAL else ()):
    raise ValueError(f"JATAYU_EXTRACTOR={DEFAULT_EXTRACTOR!r}: the demo extractors are {DEMO_EXTRACTORS}; LLM-only is "
                     "experimental (set JATAYU_EXPERIMENTAL=1 to allow it outside the demo)")

LLM_MODEL_PATH = MODELS_DIR / "llm/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
LLM_BACKUP_PATH = MODELS_DIR / "llm/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
# Measured 2026-11-01 on the demo RTX 5060 (8 GB, Windows desktop already holds ~3.8 GB): Qwen3-4B +3.35 GB,
# Whisper small.en +0.2 GB -> both fit with ~0.8 GB free; swapping costs 1.2-2.6 s per utterance. Keep both.
KEEP_MODELS = os.environ.get("JATAYU_KEEP_MODELS", "1") == "1"
