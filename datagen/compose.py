"""Build an utterance left to right, recording each gold field's span as its surface is appended."""
from __future__ import annotations

import re

from datagen.schema import GoldEntry, GoldField, GoldTime, GoldUtterance


class Composer:
    def __init__(self):
        self._buf = ""
        self._entries: list[GoldEntry] = []
        self.tags: list[str] = []

    @property
    def text(self) -> str:
        return self._buf

    def add(self, text: str) -> None:
        """Append literal text. Whitespace is normalised on the way in so recorded spans never move."""
        text = re.sub(r" {2,}", " ", text)
        if not self._buf or self._buf.endswith(" "):
            text = text.lstrip(" ")
        if text[:1] in ",.;:":
            # Trailing buffer spaces are never inside a recorded span, so dropping them before
            # punctuation ("IV ," -> "IV,") cannot move any span.
            self._buf = self._buf.rstrip(" ")
        self._buf += text

    def _append_surface(self, surface: str) -> tuple[int, int]:
        if self._buf and not self._buf.endswith((" ", "(", '"')):
            self._buf += " "
        start = len(self._buf)
        self._buf += surface
        return (start, len(self._buf))

    def new_entry(self, kind: str, context: str = "given") -> None:
        self._entries.append(GoldEntry(kind=kind, context=context))

    @property
    def entry(self) -> GoldEntry:
        if not self._entries:
            raise RuntimeError("call new_entry() before adding fields")
        return self._entries[-1]

    def field(self, name: str, surface: str, value) -> None:
        setattr(self.entry, name, GoldField(value=value, surface=surface, span=self._append_surface(surface)))

    def time(self, kind: str, surface: str | None = None, offset_s: int | None = None,
             hh: int | None = None, mm: int | None = None) -> None:
        span = self._append_surface(surface) if surface else None
        self.entry.time = GoldTime(kind=kind, offset_s=offset_s, hh=hh, mm=mm, surface=surface, span=span)

    def build(self, *, id: str, family: str, category: str, lang: str, capture_time: str) -> GoldUtterance:
        return GoldUtterance(id=id, family=family, category=category, lang=lang, text=self._buf.rstrip(),
                             capture_time=capture_time, entries=self._entries, tags=sorted(set(self.tags)))
