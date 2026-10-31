"""Day-0 smoke test: can CTranslate2 / faster-whisper run on this GPU?

Prints diagnostics and ends with `RESULT device=<cuda|cpu> compute_type=<...>`.
Usage: python scripts/smoke_gpu.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
MODEL = Path(__file__).resolve().parent.parent / "models/asr/faster-whisper-small.en"

CUDA_LIB_HINT = (
    "CUDA libraries missing for CTranslate2. Fix:\n"
    "  pip install nvidia-cublas-cu12 'nvidia-cudnn-cu12==9.*'\n"
    "  export LD_LIBRARY_PATH=$(python -c \"import nvidia.cublas.lib, nvidia.cudnn.lib, os; "
    "print(os.path.dirname(nvidia.cublas.lib.__file__)+':'+os.path.dirname(nvidia.cudnn.lib.__file__))\"):$LD_LIBRARY_PATH\n"
    "  (or: source scripts/env.sh)"
)


def try_whisper(device: str, compute_type: str) -> bool:
    import numpy as np
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(str(MODEL), device=device, compute_type=compute_type)
        segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language="en")
        list(segments)
        return True
    except Exception as exc:  # report and let caller fall back
        print(f"  whisper on {device}/{compute_type} failed: {type(exc).__name__}: {exc}")
        if "libcublas" in str(exc) or "libcudnn" in str(exc):
            print(CUDA_LIB_HINT)
        return False


def main() -> int:
    try:
        import torch
        print(f"torch {torch.__version__} cuda_available={torch.cuda.is_available()}",
              torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
    except ImportError:
        print("torch not installed")

    import ctranslate2
    n = ctranslate2.get_cuda_device_count()
    print(f"ctranslate2 {ctranslate2.__version__} cuda_devices={n}")
    if n:
        print("  cuda compute types:", sorted(ctranslate2.get_supported_compute_types("cuda")))

    if not MODEL.exists():
        print(f"model missing: {MODEL} (run scripts/download_assets.sh)")
        return 1

    for device, ctype in (("cuda", "int8_float16"), ("cuda", "float16"), ("cpu", "int8")):
        if device == "cuda" and not n:
            continue
        print(f"trying {device}/{ctype} ...")
        if try_whisper(device, ctype):
            print(f"RESULT device={device} compute_type={ctype}")
            return 0
    print("RESULT device=none compute_type=none")
    return 1


if __name__ == "__main__":
    sys.exit(main())
