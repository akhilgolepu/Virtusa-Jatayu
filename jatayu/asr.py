"""faster-whisper transcriber with a drug-vocabulary prompt, VAD and a CPU fallback."""
from __future__ import annotations

import ctypes
import gc
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from jatayu import config
from jatayu.lexicon import Lexicon

log = logging.getLogger(__name__)
PROMPT_PREFIX = "Ambulance medication and procedure log."
PROMPT_TOKEN_LIMIT = 223  # Whisper keeps at most n_text_ctx // 2 - 1 prompt tokens (faster-whisper drops the oldest)


def _is_variant(alias: str, generic: str) -> bool:
    """A spelling variant of the generic name ("frusemide", "morphine sulphate") adds nothing to the prompt."""
    from rapidfuzz import fuzz

    a, g = alias.lower(), generic.lower()
    return a.startswith(g[:5]) or fuzz.ratio(a, g) >= 75


def vocabulary_terms(lexicon: Lexicon, aliases: bool) -> list[str]:
    """Generic names first, then distinct brand/alternative names round-robin (each drug's first alias before any
    drug's second), so a token budget drops the least important names."""
    terms = list(lexicon.drug_names())
    if aliases:
        per = [[a for a in lexicon.drug(d).aliases if not _is_variant(a, d)] for d in lexicon.drug_names()]
        for rank in range(max(map(len, per))):
            terms += [p[rank] for p in per if rank < len(p)]
    return terms


def fit_prompt(head: str, terms: list[str], count_tokens, limit: int = PROMPT_TOKEN_LIMIT) -> tuple[str, list[str]]:
    """head + "Drugs: a, b, ..." with as many terms as fit in `limit` tokens; returns (prompt, dropped terms)."""
    kept: list[str] = []
    for i, t in enumerate(terms):
        if count_tokens(f"{head} Drugs: {', '.join([*kept, t])}.") > limit:
            return f"{head} Drugs: {', '.join(kept)}.", terms[i:]
        kept.append(t)
    return f"{head} Drugs: {', '.join(kept)}.", []


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
    # [{"word", "start_char", "end_char", "p"}]: Whisper's per-word probability, with offsets into `text`
    words: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


class Transcriber:
    def __init__(self, model_dir: Path = config.ASR_MODEL_DIR, device: str = config.ASR_DEVICE,
                 compute_type: str = config.ASR_COMPUTE_TYPE, lexicon: Lexicon | None = None,
                 beam_size: int = 5, vad_filter: bool = True, use_prompt: bool = True,
                 prompt_aliases: bool = config.ASR_PROMPT_ALIASES, hotwords: bool = False,
                 word_confidence: bool = True):
        self.model_dir = Path(model_dir)
        self.beam_size, self.vad_filter, self.use_prompt = beam_size, vad_filter, use_prompt
        self.prompt_aliases, self.hotwords, self.word_confidence = prompt_aliases, hotwords, word_confidence
        self._prompt: tuple[str, list[str]] | None = None
        self.device = device
        self.compute_type = compute_type
        self.lexicon = lexicon or Lexicon.load()
        self._model = None

    def _count_tokens(self, text: str) -> int:
        import tokenizers

        if not hasattr(self, "_tok"):
            self._tok = tokenizers.Tokenizer.from_file(str(self.model_dir / "tokenizer.json"))
        return len(self._tok.encode(" " + text.strip(), add_special_tokens=False).ids)

    def prompt_and_dropped(self) -> tuple[str, list[str]]:
        """The vocabulary prompt within Whisper's 223-token prompt limit, and the names that did not fit."""
        if self._prompt is None:
            # Listing route codes stops Whisper hearing "I M" as "I am".
            head = f"{PROMPT_PREFIX} Routes: {', '.join(self.lexicon.route_codes())}."
            self._prompt = fit_prompt(head, vocabulary_terms(self.lexicon, self.prompt_aliases), self._count_tokens)
        return self._prompt

    @property
    def initial_prompt(self) -> str:
        return self.prompt_and_dropped()[0]

    @property
    def hotword_text(self) -> str | None:
        """Brand/alternative names as faster-whisper hotwords (a second prompt block, also capped at 223 tokens)."""
        if not self.hotwords:
            return None
        names = [t for t in vocabulary_terms(self.lexicon, True) if t not in self.lexicon.drug_names()]
        return fit_prompt("", names, self._count_tokens)[0].replace(" Drugs: ", "", 1).strip()

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
            samples, language="en", beam_size=self.beam_size, vad_filter=self.vad_filter,
            initial_prompt=self.initial_prompt if self.use_prompt else None, condition_on_previous_text=False,
            hotwords=self.hotword_text, word_timestamps=self.word_confidence,
        )
        segments = list(segments)
        text = " ".join(s.text.strip() for s in segments).strip()
        return AsrResult(text=text, language=info.language, duration_s=len(samples) / 16000,
                         latency_s=time.perf_counter() - t0, device=self.device, words=_word_offsets(text, segments))

    def unload(self) -> None:
        self._model = None
        gc.collect()


def _word_offsets(text: str, segments) -> list[dict]:
    """Locate each recognised word in the joined transcript so its probability can be tied to an extracted span."""
    out, cursor = [], 0
    for seg in segments:
        for w in getattr(seg, "words", None) or []:
            word = w.word.strip()
            at = text.find(word, cursor) if word else -1
            if at < 0:
                continue
            cursor = at + len(word)
            out.append({"word": word, "start_char": at, "end_char": cursor, "p": round(float(w.probability), 4)})
    return out
