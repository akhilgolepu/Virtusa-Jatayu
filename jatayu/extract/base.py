from datetime import datetime
from typing import Protocol

from jatayu.models import Entry


class Extractor(Protocol):
    name: str

    def extract(self, raw: str, capture_time: datetime) -> list[Entry]: ...
