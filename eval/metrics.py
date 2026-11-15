"""Metric definitions (Field-to-Record plan, metrics table; spec §9/§13). Pure functions over gold and predictions.

- Entity P/R/F1: micro over drug, dose_value, dose_unit, route, time, procedure; a field counts only if its
  normalised value equals gold (dose within 1e-6, time within 60 s of the anchored gold time).
- Record exact match: every gold field of the record equals the matched prediction's.
- Dangerous error, HEADLINE since round 10 (`dangerous_error_r10`): a wrong drug, dose, unit, route or
  administration status recorded without a flag the medic must tick (severity high: the confirm screen refuses until
  it is acknowledged). Over every given and not_given gold record. Three ways to be counted:
    * a matched record (same drug) with a wrong dose, unit or route RECORDED (a value present and different from
      gold; a field left empty shows "not stated" on the confirm screen and is counted apart, as an omission) and
      no high flag;
    * a WRONG DRUG: a gold medication with no same-drug prediction, paired in order with an unmatched predicted
      medication of the same utterance (the drug recorded instead), which has no high flag;
    * a not_given record recorded without possible_not_given and with no other high flag.
  Note: any high flag counts, also one about another field (the evaluator's definition).
- Not stated, per field (round 11; shown apart from the dangerous-error count), over the given and not_given gold
  medication records that have that field in gold:
    * drug: no entry recorded for the record at all (neither the same drug nor a drug recorded instead);
    * dose / unit / route: the entry recorded for it (same drug, or the drug recorded instead) leaves the field empty;
    * time: that entry's time was not stated (the device clock was used).
  An empty field shows "not stated" on the confirm screen: an omission, not a wrong value.
- Dangerous error, matched-drug only (pre-round-10; secondary row): a matched given-medication record whose drug, dose,
  unit or route is wrong AND carries no
  catching flag, over all given gold records, reported as count/denominator. Headline = strict: time_not_stated,
  time_borrowed, no_reference_range, self_correction, weight_based_dose and low_asr_confidence do not catch.
  Lenient (secondary row) also counts weight_based_dose and low_asr_confidence as catches.
  A gold record with no prediction is a miss (recall), not a dangerous error.
- Context error (spec §9): a not_given/measurement gold record emitted without possible_not_given/possible_measurement.
- Administration-status error: a not_given gold record (allergy, refused, withheld, home medication, "did not give")
  emitted without possible_not_given, i.e. the record claims a drug was given when the utterance says it was not.
  Reported next to the dangerous-error rate, over all not_given gold records.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from datagen.schema import GoldEntry, GoldUtterance
from jatayu.models import Entry, MedicationEntry

FIELDS = ("drug", "dose_value", "dose_unit", "route", "time", "procedure")
DANGER_FIELDS = ("drug", "dose_value", "dose_unit", "route")
# Flags that do NOT catch an error: "time not stated" is about time, "no_reference_range" says the dose was NOT
# range-checked at all, and "weight_based_dose" is informational (low; "check against weight") — strict, the headline.
# The lenient definition (secondary row) counts weight_based_dose as a catch.
# time_borrowed (round 3) is about time too, so it never catches a dose/unit/route error either; self_correction
# (round 4) only says the speaker corrected themselves. low_asr_confidence (round 5 ruling) is informational: it does
# not catch in the headline (strict) rate; the lenient row counts it, like weight_based_dose.
NON_CATCHING_LENIENT = {"time_not_stated", "time_borrowed", "no_reference_range", "self_correction"}
NON_CATCHING = NON_CATCHING_LENIENT | {"weight_based_dose", "low_asr_confidence"}
CONTEXT_FLAGS = {"not_given": "possible_not_given", "measurement": "possible_measurement"}
ACK = "high"  # round 10: only a flag the confirm screen makes the medic tick catches an error
# Severity of every flag code, for offline re-scoring of errors.jsonl rows that stored codes only. field_missing is
# high for dose_value / dose_unit and medium for route: decided from the record's output (see high_codes).
FLAG_SEVERITY = {"ambiguous_dose": "high", "concentration_not_dose": "high", "dose_below_range": "medium",
                 "dose_out_of_range": "high", "dose_range_stated": "high", "drug_not_in_lexicon": "high",
                 "duplicate_dose": "medium", "llm_omitted": "medium", "llm_unsupported": "high",
                 "low_asr_confidence": "low", "low_confidence": "medium", "no_reference_range": "medium",
                 "possible_measurement": "high", "possible_mg_mcg_confusion": "high", "possible_not_given": "high",
                 "repeat_dose_inferred": "medium", "repeat_too_soon": "high", "route_not_allowed": "high",
                 "self_correction": "low", "sound_alike_drug": "high", "time_borrowed": "medium",
                 "time_not_stated": "low", "unit_not_allowed": "high", "weight_based_dose": "low"}


def high_codes(codes, output: dict | None) -> set[str]:
    """High-severity codes among stored codes. field_missing is high when the output has no dose, or a dose and no
    unit (the extractor's rule); otherwise it was the medium route flag."""
    out = {c for c in codes if FLAG_SEVERITY.get(c) == ACK}
    o = output or {}
    if "field_missing" in codes and (o.get("dose_value") is None or o.get("dose_unit") is None):
        out.add("field_missing")
    return out
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


def is_dangerous(wrong, flags, non_catching: set[str] = NON_CATCHING) -> bool:
    """A wrong drug/dose/unit/route with no catching flag."""
    return any(f in DANGER_FIELDS for f in wrong) and not (set(flags) - non_catching)


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
        self.danger_lenient = 0
        self.context_err = 0
        self.context_den = 0
        self.admin_err = 0
        self.admin_den = 0
        self.anomaly_caught = 0
        self.anomaly_den = 0
        self.quote_ok = 0
        self.quote_den = 0
        self.r10 = 0
        self.r10_den = 0
        self.r10_kinds = defaultdict(int)  # uncaught, by kind
        self.r10_events = defaultdict(int)  # every such error, caught or not
        self.not_stated = defaultdict(lambda: [0, 0])  # field -> [not stated, gold records with the field]
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
        matches = []
        for g, gv in golds:
            best, score = None, -1
            for i in free:
                s = _overlap(gv, pvals[i][1])
                if s > score:
                    best, score = i, s
            match = pvals[best] if best is not None and score >= 0 else None
            if match is not None:
                free.remove(best)
            matches.append(match)
        # Round 10: a gold medication with no same-drug prediction, and a predicted medication matched to nothing in the
        # same utterance, are paired in order: the drug recorded INSTEAD (a wrong drug), not a miss plus a stray entry.
        lost = [k for k, (g, _) in enumerate(golds) if matches[k] is None and g.kind == "medication"
                and g.context in ("given", "not_given")]
        stray = [i for i in free if isinstance(pvals[i][0], MedicationEntry) and pvals[i][1]["drug"] is not None]
        instead = dict(zip(lost, stray))
        for k, (g, gv) in enumerate(golds):
            self._score_record(utt, g, gv, matches[k], meta, pvals[instead[k]] if k in instead else None)
        for i in free:  # unmatched predictions are false positives
            for f in FIELDS:
                if pvals[i][1][f] is not None:
                    self.counts[f]["pred"] += 1
            p = pvals[i][0]
            self._errors.append({"id": utt.id, "input": utt.text, "kind": "extra_prediction", "dangerous": False,
                                 "dangerous_r10": False, "recorded_instead_of_gold": i in instead.values(),
                                 "flags": sorted({f.code for f in p.flags}),
                                 "high_flags": sorted({f.code for f in p.flags if f.severity == ACK}),
                                 "output": _show(pvals[i][1]), "expected": None, **(meta or {})})

    def _score_record(self, utt, g: GoldEntry, gv: dict, match, meta, instead=None) -> None:
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
        dangerous = dangerous_lenient = False
        if g.context != "given":
            self.context_den += 1
            missed = p is not None and CONTEXT_FLAGS[g.context] not in flags
            self.context_err += missed
            if g.context == "not_given":
                self.admin_den += 1
                self.admin_err += p is not None and "possible_not_given" not in flags
        else:
            self.danger_den += 1
            if p is not None and g.kind == "medication":
                bad = [f for f in DANGER_FIELDS if not same(f, gv[f], pv[f])]
                dangerous = is_dangerous(bad, flags)
                dangerous_lenient = is_dangerous(bad, flags, NON_CATCHING_LENIENT)
                self.danger += dangerous
                self.danger_lenient += dangerous_lenient
            if g.anomaly:
                self.anomaly_den += 1
                self.anomaly_caught += bool(flags - NON_CATCHING)
        # ---- round 11: not stated, per field ----
        if g.kind == "medication" and g.context in ("given", "not_given"):
            rec = p if p is not None else (instead[0] if instead is not None else None)
            rv = pv if p is not None else (instead[1] if instead is not None else None)
            self.not_stated["drug"][1] += 1
            self.not_stated["drug"][0] += rec is None
            if rec is not None:
                for f in ("dose_value", "dose_unit", "route", "time"):
                    if gv[f] is not None:
                        self.not_stated[f][1] += 1
                        self.not_stated[f][0] += rv[f] is None
        # ---- round 10 headline ----
        r10, r10_kind = False, None
        if g.context in ("given", "not_given"):
            self.r10_den += 1
            if p is not None:
                high = {fl.code for fl in p.flags if fl.severity == ACK}
                bad = [f for f in ("dose_value", "dose_unit", "route") if pv[f] is not None and not same(f, gv[f], pv[f])]
                omitted = [f for f in ("dose_value", "dose_unit", "route") if pv[f] is None and gv[f] is not None]
                if g.context == "given" and g.kind == "medication" and omitted:
                    self.r10_events["omitted dose/unit/route (shown as not stated; not counted)"] += 1
                if g.context == "given" and g.kind == "medication" and bad:
                    r10_kind, r10 = "wrong dose/unit/route", not high
                elif g.context == "not_given" and "possible_not_given" not in flags:
                    r10_kind, r10 = "status (not given recorded as given)", not high
            elif instead is not None:
                r10_kind, r10 = "wrong drug", not any(fl.severity == ACK for fl in instead[0].flags)
        if r10_kind:
            self.r10_events[r10_kind] += 1
            if r10:
                self.r10 += 1
                self.r10_kinds[r10_kind] += 1
        if wrong or p is None or r10_kind:
            row = {"id": utt.id, "input": utt.text, "category": utt.category, "lang": utt.lang,
                   "kind": "miss" if p is None else "wrong", "wrong_fields": wrong,
                   "dangerous": dangerous, "dangerous_lenient": dangerous_lenient, "flags": sorted(flags), "context": g.context,
                   "high_flags": sorted({fl.code for fl in p.flags if fl.severity == ACK}) if p else [],
                   "dangerous_r10": r10, "r10_kind": r10_kind,
                   "output": _show(pv) if p else None, "expected": _show(gv), **(meta or {})}
            if instead is not None:
                row["recorded_instead"] = _show(instead[1])
                row["recorded_instead_flags"] = sorted({fl.code for fl in instead[0].flags})
                row["recorded_instead_high_flags"] = sorted({fl.code for fl in instead[0].flags if fl.severity == ACK})
            self._errors.append(row)

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
            "dangerous_error_r10": {**_rate(self.r10, self.r10_den), "uncaught_by_kind": dict(self.r10_kinds),
                                    "errors_by_kind": dict(self.r10_events)},
            "not_stated": {f: _rate(*self.not_stated[f]) for f in ("drug", "dose_value", "dose_unit", "route", "time")},
            "dangerous_error": _rate(self.danger, self.danger_den),
            "dangerous_error_lenient": _rate(self.danger_lenient, self.danger_den),
            "context_error": _rate(self.context_err, self.context_den),
            "administration_status_error": _rate(self.admin_err, self.admin_den),
            "anomaly_flagged": _rate(self.anomaly_caught, self.anomaly_den),
            "source_quote_coverage": _rate(self.quote_ok, self.quote_den),
        }

    def errors(self) -> list[dict]:
        """Worst first: dangerous, then misses and wrong records, then extra predictions."""
        rank = lambda e: (not (e["dangerous"] or e.get("dangerous_r10")), e["kind"] == "extra_prediction",  # noqa: E731
                          -len(e.get("wrong_fields", [])))
        return sorted(self._errors, key=rank)


def _prf(tp: int, gold: int, pred: int) -> dict:
    p = tp / pred if pred else 0.0
    r = tp / gold if gold else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0}


def _rate(n: int, d: int) -> dict:
    return {"count": n, "denominator": d, "rate": round(n / d, 4) if d else 0.0}


def _show(v: dict) -> dict:
    return {k: (x.isoformat() if isinstance(x, datetime) else x) for k, x in v.items() if x is not None}
