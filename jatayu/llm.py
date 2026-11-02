"""Local LLM (llama.cpp, Qwen3-4B Q4) with JSON-schema-constrained output. Never used to produce values directly:
extractors derive every value from transcript text the LLM points at."""
from __future__ import annotations

import ctypes
import gc
import logging
import threading
from pathlib import Path

log = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


def _preload_cuda13() -> None:
    """llama-cpp-python is built against CUDA 13; reuse the runtime + cuBLAS that torch's nvidia-cu13 wheels ship."""
    try:
        import nvidia
    except ImportError:
        return
    for root in map(Path, nvidia.__path__):
        for lib in sorted(root.glob("cu13/lib/libcu*.so.13")):
            try:
                ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
            except OSError as exc:
                log.debug("could not preload %s: %s", lib, exc)


class LlmRunner:
    def __init__(self, model_path: Path, n_ctx: int = 4096, n_gpu_layers: int = -1):
        self.model_path = Path(model_path)
        self.n_ctx, self.n_gpu_layers = n_ctx, n_gpu_layers
        self._llm = None
        self._lock = threading.Lock()

    def _load(self):
        if self._llm is None:
            if not self.model_path.exists():
                raise LlmError(f"model not found: {self.model_path}")
            _preload_cuda13()
            try:
                import llama_cpp

                # Qwen uses ChatML; without an explicit format the GGUF template guess garbles quoting.
                self._llm = llama_cpp.Llama(str(self.model_path), n_ctx=self.n_ctx, n_gpu_layers=self.n_gpu_layers,
                                            chat_format="chatml", verbose=False)
            except Exception as exc:
                raise LlmError(f"could not load LLM: {exc}") from exc
        return self._llm

    def complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 512) -> dict:
        import json

        with self._lock:
            llm = self._load()
            try:
                out = llm.create_chat_completion(
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    response_format={"type": "json_object", "schema": schema}, temperature=0.0,
                    max_tokens=max_tokens)
                choice = out["choices"][0]
                if choice.get("finish_reason") == "length":
                    raise LlmError(f"output truncated at max_tokens={max_tokens} (not valid JSON)")
                return json.loads(choice["message"]["content"])
            except LlmError:
                raise
            except Exception as exc:
                raise LlmError(f"LLM call failed: {exc}") from exc

    def close(self) -> None:
        with self._lock:
            self._llm = None
            gc.collect()
