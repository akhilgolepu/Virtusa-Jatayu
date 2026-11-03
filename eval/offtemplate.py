"""The hand-written off-template DEV set (eval/offtemplate_dev.yaml) as GoldUtterances, for eval.run
(--split offtemplate_dev) and tests/test_offtemplate.py. Dev-only."""
from __future__ import annotations

from pathlib import Path

import yaml

from datagen.schema import GoldEntry, GoldField, GoldTime, GoldUtterance

PATH = Path(__file__).with_name("offtemplate_dev.yaml")
CATEGORY = {"range": "med_messy", "weight_based": "med_messy", "another": "med_multi", "borrowed_time": "time_clock",
            "multi": "med_multi", "negation": "context_negation", "correction": "med_correction",
            "hinglish": "hinglish", "filler": "med_messy", "route": "med_basic"}


def _f(v) -> GoldField:
    return GoldField(value=v, surface=str(v), span=(0, 0))  # scoring compares values; spans are not used


def _time(t: str | None) -> GoldTime:
    if t is None:
        return GoldTime()
    if ":" in t:
        hh, mm = map(int, t.split(":"))
        return GoldTime(kind="clock", hh=hh, mm=mm, surface=t)
    return GoldTime(kind="relative", offset_s=int(t), surface=t)


def _entry(e: dict) -> GoldEntry:
    kind = e.get("kind", "medication")
    return GoldEntry(kind=kind, context=e.get("context", "given"),
                     drug=_f(e["drug"]) if "drug" in e else None,
                     procedure=_f(e["procedure"]) if "procedure" in e else None,
                     dose_value=_f(float(e["dose"])) if "dose" in e else None,
                     dose_unit=_f(e["unit"]) if "unit" in e else None,
                     route=_f(e["route"]) if "route" in e else None, time=_time(e.get("time")))


def cases(path: Path = PATH) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [{**c, "capture_time": doc["capture_time"]} for c in doc["cases"]]


def load(path: Path = PATH) -> list[GoldUtterance]:
    return [GoldUtterance(id=c["id"], family="offtemplate", category=CATEGORY[c["group"]], split="dev",
                          lang="hinglish" if c["group"] == "hinglish" else "en", text=c["text"],
                          capture_time=c["capture_time"], entries=[_entry(e) for e in c["entries"]],
                          tags=[c["group"]] + (["xfail"] if c.get("xfail") else []))
            for c in cases(path)]
