"""Metric definitions (Field-to-Record plan, metrics table; spec §9/§13). Pure functions over gold and predictions.

- Entity P/R/F1: micro over drug, dose_value, dose_unit, route, time, procedure; a field counts only if its
  normalised value equals gold (dose within 1e-6, time within 60 s of the anchored gold time).
- Record exact match: every gold field of the record equals the matched prediction's.
- Dangerous error: a matched given-medication record whose drug, dose, unit or route is wrong AND carries no
  catching flag (any flag except time_not_stated), over all given gold records, reported as count/denominator.
  A gold record with no prediction is a miss (recall), not a dangerous error.
- Context error (spec §9): a not_given/measurement gold record emitted without possible_not_given/possible_measurement.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from datagen.schema import GoldEntry, GoldUtterance
from jatayu.models import Entry, MedicationEntry

FIELDS = ("drug", "dose_value", "dose_unit", "route", "time", "procedure")
DANGER_FIELDS = ("drug", "dose_value", "dose_unit", "route")
NON_CATCHING = {"time_not_stated"}
CONTEXT_FLAGS = {"not_given": "possible_not_given", "measurement": "possible_measurement"}
TIME_TOLERANCE_S = 60


def gold_time(g: GoldEntry, capture: datetime) -> datetime | None:
    t = g.time
    if t.kind == "relative":
        return capture + timedelta(seconds=t.offset_s or 0)
    if t.kind == "clock":
        at = capture.replace(hour=t.hh, minute=t.mm, second=0, microsecond=0)
        return at - timedelta(days=1) if at > capture + timedelta(minutes=5) else at
    return None


def gold_values(g: GoldEntry, capture: datetime) -> dict:
    v = {f: (getattr(g, f).value if getattr(g, f) is not None else None) for f in FIELDS if f != "time"}
    v["time"] = gold_time(g, capture)
    return v


def pred_values(p: Entry) -> dict:
    v = {f: None for f in FIELDS}
    if isinstance(p, MedicationEntry):
        v.update(drug=p.drug.value, dose_value=p.dose_value.value, dose_unit=p.dose_unit.value, route=p.route.value)
    else:
        v["procedure"] = p.procedure.value
    v["time"] = p.time.value if p.time_source != "device_clock" else None  # capture-time fallback = "not stated"
    return v


def same(field: str, a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if field == "dose_value":
        return abs(float(a) - float(b)) < 1e-6
    if field == "time":
        return abs((a - b).total_seconds()) <= TIME_TOLERANCE_S
    return a == b


def _overlap(gv: dict, pv: dict) -> int:
    anchor = ("drug", "procedure")
    if not any(gv[a] is not None and gv[a] == pv[a] for a in anchor):
        return -1  # never pair records about different drugs/procedures
    return sum(same(f, gv[f], pv[f]) for f in FIELDS if gv[f] is not None)


class Scorer:
    def __init__(self):
        self.counts = defaultdict(lambda: {"tp": 0, "gold": 0, "pred": 0})
        self.records = 0
        self.exact = 0
        self.danger = 0
        self.danger_den = 0
        self.context_err = 0
        self.context_den = 0
        self.anomaly_caught = 0
        self.anomaly_den = 0
        self.quote_ok = 0
        self.quote_den = 0
        self._errors: list[dict] = []

    def add(self, utt: GoldUtterance, preds: list[Entry], meta: dict | None = None) -> None:
        capture = datetime.fromisoformat(utt.capture_time)
        golds = [(g, gold_values(g, capture)) for g in utt.entries]
        pvals = [(p, pred_values(p)) for p in preds]
        for p, pv in pvals:
            for name in ("drug", "dose_value", "dose_unit", "route", "procedure", "detail"):
                f = getattr(p, name, None)
                if f is not None and f.value is not None and f.source != "user":
                    self.quote_den += 1
                    self.quote_ok += f.span is not None and bool(f.raw)
        free = list(range(len(pvals)))
        for g, gv in golds:
            best, score = None, -1
            for i in free:
                s = _overlap(gv, pvals[i][1])
                if s > score:
                    best, score = i, s
            match = pvals[best] if best is not None and score >= 0 else None
            if match is not None:
                free.remove(best)
            self._score_record(utt, g, gv, match, meta)
        for i in free:  # unmatched predictions are false positives
            for f in FIELDS:
                if pvals[i][1][f] is not None:
                    self.counts[f]["pred"] += 1
            self._errors.append({"id": utt.id, "input": utt.text, "kind": "extra_prediction", "dangerous": False,
                                 "output": _show(pvals[i][1]), "expected": None, **(meta or {})})

    def _score_record(self, utt, g: GoldEntry, gv: dict, match, meta) -> None:
        pv = dict(match[1]) if match else {f: None for f in FIELDS}
        if g.context == "measurement":
            # spec §13: a reading put in the dose field is judged only by its flag, not as a dose/unit/route error
            for f in ("dose_value", "dose_unit", "route"):
                pv[f] = None
        p = match[0] if match else None
        flags = {fl.code for fl in p.flags} if p else set()
        wrong = []
        for f in FIELDS:
            if gv[f] is not None:
                self.counts[f]["gold"] += 1
            if pv[f] is not None:
                self.counts[f]["pred"] += 1
            if gv[f] is not None and same(f, gv[f], pv[f]):
                self.counts[f]["tp"] += 1
            elif gv[f] is not None or pv[f] is not None:
                wrong.append(f)
        self.records += 1
        self.exact += not wrong
        dangerous = False
        if g.context != "given":
            self.context_den += 1
            missed = p is not None and CONTEXT_FLAGS[g.context] not in flags
            self.context_err += missed
        else:
            self.danger_den += 1
            if p is not None and g.kind == "medication":
                bad = [f for f in DANGER_FIELDS if not same(f, gv[f], pv[f])]
                dangerous = bool(bad) and not (flags - NON_CATCHING)
                self.danger += dangerous
            if g.anomaly:
                self.anomaly_den += 1
                self.anomaly_caught += bool(flags - NON_CATCHING)
        if wrong or p is None:
            self._errors.append({"id": utt.id, "input": utt.text, "category": utt.category, "lang": utt.lang,
                                 "kind": "miss" if p is None else "wrong", "wrong_fields": wrong,
                                 "dangerous": dangerous, "flags": sorted(flags), "context": g.context,
                                 "output": _show(pv) if p else None, "expected": _show(gv), **(meta or {})})

    def metrics(self) -> dict:
        per = {}
        tp = gold = pred = 0
        for f in FIELDS:
            c = self.counts[f]
            tp, gold, pred = tp + c["tp"], gold + c["gold"], pred + c["pred"]
            per[f] = {**c, **_prf(c["tp"], c["gold"], c["pred"])}
        return {
            "entity": {"micro": {"tp": tp, "gold": gold, "pred": pred, **_prf(tp, gold, pred)}, "per_field": per},
            "record_exact_match": _rate(self.exact, self.records),
            "dangerous_error": _rate(self.danger, self.danger_den),
            "context_error": _rate(self.context_err, self.context_den),
            "anomaly_flagged": _rate(self.anomaly_caught, self.anomaly_den),
            "source_quote_coverage": _rate(self.quote_ok, self.quote_den),
        }

    def errors(self) -> list[dict]:
        """Worst first: dangerous, then misses and wrong records, then extra predictions."""
        rank = lambda e: (not e["dangerous"], e["kind"] == "extra_prediction", -len(e.get("wrong_fields", [])))  # noqa: E731
        return sorted(self._errors, key=rank)


def _prf(tp: int, gold: int, pred: int) -> dict:
    p = tp / pred if pred else 0.0
    r = tp / gold if gold else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0}


def _rate(n: int, d: int) -> dict:
    return {"count": n, "denominator": d, "rate": round(n / d, 4) if d else 0.0}


def _show(v: dict) -> dict:
    return {k: (x.isoformat() if isinstance(x, datetime) else x) for k, x in v.items() if x is not None}
