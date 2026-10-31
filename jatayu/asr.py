"""faster-whisper transcriber with a drug-vocabulary prompt, VAD and a CPU fallback."""
from __future__ import annotations

import ctypes
import gc
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from jatayu import config
from jatayu.lexicon import Lexicon

log = logging.getLogger(__name__)
PROMPT_PREFIX = "Ambulance medication and procedure log."


def _preload_cuda_libs() -> None:
    """CTranslate2 wheels need CUDA 12 cuBLAS and cuDNN 9; load them from the pip-installed NVIDIA
    packages so the GPU works without LD_LIBRARY_PATH (see scripts/env.sh for the shell equivalent)."""
    try:
        import nvidia
    except ImportError:
        return
    roots = [Path(p) for p in nvidia.__path__]
    patterns = ["cu13/lib/libcublasLt.so.13", "cu13/lib/libcublas.so.13",
                "cublas/lib/libcublasLt.so.12", "cublas/lib/libcublas.so.12",
                "cudnn/lib/libcudnn.so.9", "cudnn/lib/libcudnn_*.so.9"]
    for root in roots:
        for pattern in patterns:
            for lib in sorted(root.glob(pattern)):
                try:
                    ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
                except OSError as exc:
                    log.debug("could not preload %s: %s", lib, exc)


@dataclass
class AsrResult:
    text: str
    language: str
    duration_s: float
    latency_s: float
    device: str

    def as_dict(self) -> dict:
        return asdict(self)


class Transcriber:
    def __init__(self, model_dir: Path = config.ASR_MODEL_DIR, device: str = config.ASR_DEVICE,
                 compute_type: str = config.ASR_COMPUTE_TYPE, lexicon: Lexicon | None = None):
        self.model_dir = Path(model_dir)
        self.device = device
        self.compute_type = compute_type
        self.lexicon = lexicon or Lexicon.load()
        self._model = None

    @property
    def initial_prompt(self) -> str:
        # Listing route codes stops Whisper hearing "I M" as "I am".
        routes = ", ".join(self.lexicon.route_codes())
        return f"{PROMPT_PREFIX} Routes: {routes}. Drugs: {', '.join(self.lexicon.drug_names())}."

    def _load(self):
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel

        if self.device == "cuda":
            _preload_cuda_libs()
            try:
                self._model = WhisperModel(str(self.model_dir), device="cuda", compute_type=self.compute_type)
                # CUDA library problems surface on first use, so prove the model runs before keeping it.
                list(self._model.transcribe(np.zeros(1600, dtype=np.float32), language="en")[0])
                return self._model
            except Exception as exc:
                log.warning("ASR on CUDA failed (%s); falling back to CPU int8", exc)
                self._model = None
                self.device, self.compute_type = "cpu", "int8"
        self._model = WhisperModel(str(self.model_dir), device=self.device, compute_type=self.compute_type)
        return self._model

    def transcribe(self, samples: np.ndarray) -> AsrResult:
        model = self._load()
        t0 = time.perf_counter()
        segments, info = model.transcribe(
            samples, language="en", beam_size=5, vad_filter=True,
            initial_prompt=self.initial_prompt, condition_on_previous_text=False,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return AsrResult(text=text, language=info.language, duration_s=len(samples) / 16000,
                         latency_s=time.perf_counter() - t0, device=self.device)

    def unload(self) -> None:
        self._model = None
        gc.collect()
