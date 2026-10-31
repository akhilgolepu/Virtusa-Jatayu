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

DISCLAIMER = "Decision-support demo, not a clinical device."
