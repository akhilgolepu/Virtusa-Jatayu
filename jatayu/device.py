"""A stable identifier for this install, shown on the PDF note and in every FHIR-lite bundle."""
from __future__ import annotations

import uuid
from pathlib import Path


def device_id(directory: Path) -> str:
    """Read (or create once) `<directory>/device_id`; the id never changes for this data directory."""
    path = Path(directory) / "device_id"
    if path.exists():
        return path.read_text().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    value = "jatayu-" + uuid.uuid4().hex[:12]
    path.write_text(value + "\n")
    return value
