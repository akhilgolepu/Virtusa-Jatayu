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


class DrugInfo(BaseModel):
    name: str
    aliases: list[str]
    atc: str
    routes: list[str]
    units: list[str]
    dose_ranges: list = []
    min_repeat_s: int | None = None
    source: str | None = None


class ProcedureInfo(BaseModel):
    name: str
    aliases: list[str]
    snomed: str | None = None


class Lexicon:
    def __init__(self, drugs: dict[str, DrugInfo], procedures: dict[str, ProcedureInfo],
                 units: dict[str, list[str]], routes: dict[str, list[str]]):
        self._drugs = drugs
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
        drugs = {n: DrugInfo(name=n, **v) for n, v in read("drugs.yaml")["drugs"].items()}
        procs = {n: ProcedureInfo(name=n, **v) for n, v in read("procedures.yaml")["procedures"].items()}
        return cls(drugs, procs, read("units.yaml")["units"], read("routes.yaml")["routes"])

    def drug_names(self) -> list[str]:
        return list(self._drugs)

    def procedure_names(self) -> list[str]:
        return list(self._procedures)

    def route_codes(self) -> list[str]:
        return list(self._routes)

    def unit_codes(self) -> list[str]:
        return list(self._units)

    def drug(self, name: str) -> DrugInfo:
        return self._drugs[name]

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
