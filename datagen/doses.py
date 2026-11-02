"""Gold doses come from the lexicon's dose ranges and nowhere else (one source of truth with the validator).

For each drug + route the generator uses the cited rows; a route with no cited row falls back to its ILLUSTRATIVE row
(labelled, e.g. oxygen L/min). Each row gives an absolute window:
  band "min-max"               -> [min, max]
  "per kg, up to N"            -> per_kg x [45, 130] kg, capped at N (the plausible adult weight in the lexicon)
  "per kg" with no cap         -> per_kg x [45, 130] kg
  "up to N" with no per-kg dose -> (0, N]; the generator samples it from [N/10, N]
Values are "speakable" round numbers inside the window plus the row's stated min/max.

`in_cited_range` is the check the dataset test applies to every gold dose. It uses the windows above and none of the
validator's own heuristics (the N/5 decimal-slip floor, the mg/mcg band rule).
"""
from __future__ import annotations

from functools import lru_cache

from jatayu.lexicon import DoseRange, Lexicon

NICE = (1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5, 8)
OPEN_SAMPLE_FLOOR = 0.1  # "up to N" (no per-kg dose) is sampled from [N/10, N]; the cited range itself is (0, N]
TO_MG = {"mcg": 0.001, "mg": 1.0, "g": 1000.0}
COUNT_UNITS = {"puffs", "drops", "units"}  # whole numbers only (nobody gives 7.5 puffs)
EPS = 1e-9


def _convert(value: float, unit: str, target: str) -> float | None:
    if unit == target:
        return value
    if unit in TO_MG and target in TO_MG:
        return value * TO_MG[unit] / TO_MG[target]
    return None


def window(r: DoseRange, lex: Lexicon) -> tuple[float, float, set[float]] | None:
    """(low, high, stated values) of the absolute doses a row allows; low is exclusive 0 for "up to N"."""
    w = lex.weight_kg
    if r.min is not None and r.max is not None:
        return r.min, r.max, {r.min, r.max}
    if r.per_kg is not None:
        if w is None:
            return None
        lo, hi = r.per_kg * w.min, r.per_kg * w.max
        if r.max is not None:
            lo, hi = min(lo, r.max), min(hi, r.max)
            return lo, hi, {r.max} if hi == r.max else set()
        return lo, hi, set()
    if r.max is not None:
        return 0.0, r.max, {r.max}
    return None


def rows_for(lex: Lexicon, drug: str, route: str | None) -> tuple[list[DoseRange], str]:
    """The rows that define a gold dose's range: cited rows for the route, else its illustrative rows. With no route
    spoken, every route of the drug counts (as in the validator)."""
    info = lex.drug(drug)
    routes = [route] if route else sorted({r.route for r in info.dose_ranges})
    rows: list[DoseRange] = []
    classes = set()
    for rt in routes:
        mine = [r for r in info.dose_ranges if r.route == rt]
        cited = [r for r in mine if not r.illustrative]
        rows += cited or mine
        if mine:
            classes.add("cited" if cited else "illustrative")
    cls = "cited" if classes == {"cited"} else "illustrative" if classes == {"illustrative"} else \
        "mixed" if classes else "none"
    return rows, cls


def in_cited_range(lex: Lexicon, drug: str, route: str | None, unit: str, value: float) -> bool:
    for r in rows_for(lex, drug, route)[0]:
        v = _convert(value, unit, r.unit)
        win = window(r, lex)
        if v is None or win is None:
            continue
        lo, hi, _ = win
        if (v > EPS if lo == 0.0 else v >= lo - EPS) and v <= hi + EPS:
            return True
    return False


def _grid(lo: float, hi: float) -> set[float]:
    return {round(m * 10.0 ** k, 6) for k in range(-3, 5) for m in NICE if lo - EPS <= m * 10.0 ** k <= hi + EPS}


@lru_cache(maxsize=None)
def _specs(lex_id: int, drug: str, lex: Lexicon) -> tuple[dict, ...]:
    info = lex.drug(drug)
    units = set(lex.unit_codes())
    out = []
    for route in sorted({r.route for r in info.dose_ranges}):
        if route not in info.routes:
            continue
        rows, cls = rows_for(lex, drug, route)
        by_unit: dict[str, set[float]] = {}
        for r in rows:
            win = window(r, lex)
            if win is None or r.unit not in info.units or r.unit not in units:
                continue
            lo, hi, stated = win
            if lo == 0.0:
                lo = hi * OPEN_SAMPLE_FLOOR
            vals = _grid(lo, hi) | {v for v in stated if lo - EPS <= v <= hi + EPS}
            if r.unit in COUNT_UNITS:
                vals = {v for v in vals if float(v).is_integer()}
            by_unit.setdefault(r.unit, set()).update(vals)
        out += [{"route": route, "unit": u, "values": sorted(vs), "range_class": cls}
                for u, vs in sorted(by_unit.items()) if vs]
    return tuple(out)


def dose_specs(lex: Lexicon, drug: str) -> list[dict]:
    """[{route, unit, values, range_class}] the generator may draw a gold dose from."""
    return list(_specs(id(lex), drug, lex))
