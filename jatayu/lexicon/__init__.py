"""Hand-curated EMS lexicon: drugs, procedures, units, routes (YAML in this package)."""
from __future__ import annotations

from functools import cached_property
from pathlib import Path

import yaml
from pydantic import BaseModel
from rapidfuzz import fuzz, process

_HERE = Path(__file__).resolve().parent


def _key(term: str) -> str:
    return " ".join(term.lower().split())


class DoseRange(BaseModel):
    """One cited adult dose row. min/max are in `unit`; per_kg rows use max as the adult cap."""
    route: str
    unit: str
    min: float | None = None
    max: float | None = None
    per_kg: float | None = None
    min_repeat_s: int | None = None
    indication: str
    source: str
    secondary: bool = False  # not a NASEMSO value (AHA via secondary source, or unverified)
    illustrative: bool = False  # no public guideline range exists; plausible demo bound (plan M2 rule)


class WeightRange(BaseModel):
    """Plausible adult weight (kg), cited; turns a per-kg dose into an absolute dose."""
    min: float
    max: float
    source: str


class DrugInfo(BaseModel):
    name: str
    aliases: list[str]
    atc: str
    routes: list[str]
    units: list[str]
    dose_ranges: list[DoseRange] = []


class ProcedureInfo(BaseModel):
    name: str
    aliases: list[str]
    snomed: str | None = None


class Lexicon:
    def __init__(self, drugs: dict[str, DrugInfo], procedures: dict[str, ProcedureInfo],
                 units: dict[str, list[str]], routes: dict[str, list[str]], weight_kg: WeightRange | None = None):
        self._drugs = drugs
        self.weight_kg = weight_kg
        self._procedures = procedures
        self._units = units
        self._routes = routes
        self._drug_terms = {_key(t): d.name for d in drugs.values() for t in [d.name, *d.aliases]}
        self._proc_terms = {_key(t): p.name for p in procedures.values() for t in [p.name, *p.aliases]}
        self._unit_terms = {_key(t): code for code, syns in units.items() for t in [code, *syns]}
        self._route_terms = {_key(t): code for code, syns in routes.items() for t in syns}

    @classmethod
    def load(cls, dir: Path | None = None) -> "Lexicon":
        d = dir or _HERE
        read = lambda name: yaml.safe_load((d / name).read_text(encoding="utf-8"))  # noqa: E731
        doc = read("dose_ranges.yaml") if (d / "dose_ranges.yaml").exists() else {}
        ranges = {k: list(v) for k, v in (doc.get("dose_ranges") or {}).items()}
        for k, v in (doc.get("illustrative_ranges") or {}).items():
            ranges.setdefault(k, []).extend(v)
        drugs = {n: DrugInfo(name=n, dose_ranges=ranges.get(n, []), **v) for n, v in read("drugs.yaml")["drugs"].items()}
        procs = {n: ProcedureInfo(name=n, **v) for n, v in read("procedures.yaml")["procedures"].items()}
        weight = WeightRange(**doc["plausible_adult_weight_kg"]) if doc.get("plausible_adult_weight_kg") else None
        return cls(drugs, procs, read("units.yaml")["units"], read("routes.yaml")["routes"], weight)

    def drug_names(self) -> list[str]:
        return list(self._drugs)

    def procedure_names(self) -> list[str]:
        return list(self._procedures)

    def route_codes(self) -> list[str]:
        return list(self._routes)

    def unit_codes(self) -> list[str]:
        return list(self._units)

    def unit_synonyms(self, code: str) -> list[str]:
        return list(self._units[code])

    def route_synonyms(self, code: str) -> list[str]:
        return list(self._routes[code])

    def drug(self, name: str) -> DrugInfo:
        return self._drugs[name]

    def dose_ranges(self, drug: str, route: str) -> list[DoseRange]:
        return [r for r in self._drugs[drug].dose_ranges if r.route == route]

    def min_repeat_s(self, drug: str, route: str) -> int | None:
        """The smallest repeat interval any cited row states for this drug and route (None if none is stated)."""
        stated = [r.min_repeat_s for r in self.dose_ranges(drug, route) if r.min_repeat_s is not None]
        return min(stated) if stated else None

    def procedure(self, name: str) -> ProcedureInfo:
        return self._procedures[name]

    def lookup_drug(self, term: str) -> str | None:
        return self._drug_terms.get(_key(term))

    def lookup_procedure(self, term: str) -> str | None:
        return self._proc_terms.get(_key(term))

    def canonical_unit(self, term: str) -> str | None:
        return self._unit_terms.get(_key(term))

    def canonical_route(self, term: str) -> str | None:
        return self._route_terms.get(_key(term))

    def fuzzy_drug(self, term: str, threshold: int) -> tuple[str, float] | None:
        hit = process.extractOne(_key(term), self._drug_terms.keys(), scorer=fuzz.ratio, score_cutoff=threshold)
        if hit is None:
            return None
        return self._drug_terms[hit[0]], hit[1] / 100.0

    @cached_property
    def _phrases(self) -> list[tuple[str, str, str]]:
        rows = [(t, "drug", c) for t, c in self._drug_terms.items()]
        rows += [(t, "procedure", c) for t, c in self._proc_terms.items()]
        rows += [(t, "unit", c) for t, c in self._unit_terms.items()]
        rows += [(t, "route", c) for t, c in self._route_terms.items()]
        return sorted(rows, key=lambda r: len(r[0]), reverse=True)

    def phrases(self) -> list[tuple[str, str, str]]:
        return self._phrases
