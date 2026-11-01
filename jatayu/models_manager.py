"""Keeps heavy models on the GPU. Default (spec §4): one at a time; keep_all keeps every loaded model resident."""
from __future__ import annotations

import threading
from collections.abc import Callable


class ModelManager:
    def __init__(self, loaders: dict[str, Callable[[], object]], unloaders: dict[str, Callable[[object], None]],
                 keep_all: bool):
        self._loaders, self._unloaders, self.keep_all = loaders, unloaders, keep_all
        self._models: dict[str, object] = {}
        self._lock = threading.Lock()  # two first requests must not both load a model (8 GB VRAM)

    @property
    def loaded(self) -> list[str]:
        return list(self._models)

    def get(self, name: str) -> object:
        with self._lock:
            if name in self._models:
                return self._models[name]
            if not self.keep_all:
                for other in [n for n in self._models if n != name]:
                    self._unloaders[other](self._models.pop(other))
            self._models[name] = self._loaders[name]()
            return self._models[name]
