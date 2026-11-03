"""Hybrid extractor (default): the rules layer finds candidate spans; the LLM only LINKS candidate ids into entries.
It cannot introduce text, so every value is a span the rules layer already read. If the LLM is unavailable or
fails, the rules result is returned with a warning, so no utterance is lost."""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from jatayu.extract.llm import FIELDS, KIND_FIELDS, LLM_CONFIDENCE, _kind, assemble
from jatayu.extract.rules import Candidate, RulesExtractor
from jatayu.lexicon import Lexicon
from jatayu.llm import LlmRunner
from jatayu.models import Entry, Field, Flag

log = logging.getLogger(__name__)
FIELD_KIND = {"drug": "drug", "dose": "number", "unit": "unit", "route": "route", "time": "time",
              "procedure": "procedure", "detail": "detail"}
CONTEXT_CODES = {"possible_not_given", "possible_measurement"}

SYSTEM = (
    "You link pre-found spans of an ambulance responder's transcript into entries. You get the transcript and a "
    "numbered list of candidate spans (drug, number, unit, route, time, procedure, detail). Return one entry per drug "
    "given or procedure done (never repeat an entry), using candidate NUMBERS only; omit fields that were not said. dose must be a number candidate, "
    "unit a unit candidate, and so on. Link each value to the drug it belongs to, as the speaker meant it; if the "
    "speaker corrected themselves ('4, no sorry, 2 mg'), use the corrected value.\n"
    "context: 'given' if administered; 'not_given' for allergies, refused, withheld, not given, or the patient's own "
    "regular medication; 'measurement' for readings such as blood glucose or oxygen saturation."
)
SHAREABLE = {"time"}  # one time phrase may cover several drugs ("at 10 40 aspirin ... and ondansetron ...")
def schema_for(cands: list[Candidate]) -> dict:
    """Per-utterance schema: each field may only name candidates of its kind (or null); fields with no candidate are
    left out. The model then cannot link a unit to a time or fill fields with stray ids, and writes fewer tokens."""
    props: dict = {"context": {"enum": ["given", "not_given", "measurement"]}}
    for name in FIELDS:
        ids = [c.id for c in cands if c.kind == FIELD_KIND[name]]
        if ids:
            props[name] = {"enum": [*ids, None]}
    item = {"type": "object", "properties": props, "required": []}
    # At most one entry per drug/procedure candidate (an entry reusing an anchor is dropped anyway). Without this cap
    # the model can repeat one entry until max_tokens and the JSON is cut off: all 15 hybrid fallbacks in the round-2
    # dev speech runs were this loop (evaluator round 3, item 6).
    anchors = sum(c.kind in ("drug", "procedure") for c in cands)
    entries = {"type": "array", "items": item, "maxItems": max(anchors, 1)}
    return {"type": "object", "properties": {"entries": entries}, "required": ["entries"]}


def _describe(c: Candidate) -> str:
    extra = f" -> {c.value}" if c.kind in ("drug", "unit", "route", "procedure") and str(c.value) != c.text else ""
    return f'[{c.id}] {c.kind} "{c.text}"{extra}'


class HybridExtractor:
    name = "hybrid"

    def __init__(self, lexicon: Lexicon, runner_factory: Callable[[], LlmRunner], fallback: RulesExtractor):
        self.lexicon, self.runner_factory, self.fallback = lexicon, runner_factory, fallback

    def extract(self, raw: str, capture_time: datetime) -> list[Entry]:
        return self.extract_with_warnings(raw, capture_time)[0]

    def extract_with_warnings(self, raw: str, capture_time: datetime) -> tuple[list[Entry], list[str]]:
        cands = self.fallback.candidates(raw, capture_time)
        if not any(c.kind in ("drug", "procedure") for c in cands):
            return [], []
        rules_entries = self.fallback.extract(raw, capture_time)
        prompt = f"Transcript: {raw}\nCandidates:\n" + "\n".join(_describe(c) for c in cands)
        try:
            out = self.runner_factory().complete_json(SYSTEM, prompt, schema_for(cands))
            linked = self._link(out, cands, rules_entries, capture_time)
        except Exception as exc:  # LlmError, missing model, CUDA trouble, malformed output: never lose the utterance
            log.warning("hybrid falling back to rules: %s", exc)
            return rules_entries, [f"llm unavailable: {exc}; used rules"]
        return self._keep_omitted(self._prefer_corrections(linked, rules_entries), rules_entries)

    @staticmethod
    def _prefer_corrections(linked: list[Entry], rules_entries: list[Entry]) -> list[Entry]:
        """Where the rules layer saw a spoken correction ("1.5, no, 8 mg") for the same drug span, its dose stands: the
        LLM linked the value said BEFORE the correction in all 10 extraction-origin dangerous errors of round 3."""
        out = []
        for e in linked:
            anchor = getattr(e, "drug", None)
            r = next((r for r in rules_entries if getattr(r, "drug", None) is not None and anchor is not None
                      and r.drug.span == anchor.span and any(f.code == "self_correction" for f in r.flags)), None)
            if r is None or r.dose_value.span == e.dose_value.span:
                out.append(e if r is None else e.model_copy(update={"flags": [*e.flags, *[f for f in r.flags if f.code == "self_correction"]]}))
                continue
            unit = r.dose_unit if r.dose_unit.value is not None else e.dose_unit
            replaced = {"dose_value"} | ({"dose_unit"} if r.dose_unit.value is not None else set())
            keep = [f for f in e.flags if not (f.field in replaced and f.code in ("field_missing", "llm_unsupported"))]
            if unit.value is None and not any(f.code == "field_missing" and f.field == "dose_unit" for f in keep):
                keep.append(Flag(code="field_missing", field="dose_unit", severity="high", message="Dose has no unit."))
            out.append(e.model_copy(update={"dose_value": r.dose_value, "dose_unit": unit,
                                            "flags": keep + [f for f in r.flags if f.code == "self_correction"]}))
        return out

    @staticmethod
    def _keep_omitted(linked: list[Entry], rules_entries: list[Entry]) -> tuple[list[Entry], list[str]]:
        """A drug or procedure the rules layer found but the LLM left out is kept (from rules) and flagged, so the
        LLM can never silently drop an administration. Where the rules layer read a repeat dose ("then another
        2 mg") both of its entries stand: the LLM can link a drug name only once."""
        anchor_of = lambda e: (getattr(e, "drug", None) or getattr(e, "procedure", None)).span  # noqa: E731
        repeated = {anchor_of(r) for r in rules_entries if any(f.code == "repeat_dose_inferred" for f in r.flags)}
        if repeated:
            linked = [e for e in linked if anchor_of(e) not in repeated]
            linked += [r for r in rules_entries if anchor_of(r) in repeated]
        covered = {anchor_of(e) for e in linked}
        omitted = []
        for r in rules_entries:
            anchor = getattr(r, "drug", None) or getattr(r, "procedure", None)
            if anchor is not None and anchor.span not in covered:
                flag = Flag(code="llm_omitted", field="drug" if r.kind == "medication" else "procedure",
                            severity="medium", message="The model did not link this mention; kept from the rule-based reading.")
                omitted.append(r.model_copy(update={"flags": [*r.flags, flag]}))
        warnings = [f"llm left out {len(omitted)} mention(s); kept from rules"] if omitted else []
        return linked + omitted, warnings

    def _link(self, out: dict, cands: list[Candidate], rules_entries: list[Entry], capture_time: datetime) -> list[Entry]:
        by_id = {c.id: c for c in cands}
        used: dict[str, set[int]] = {f: set() for f in FIELDS}
        entries = []
        for item in out.get("entries", []):
            kind = _kind(item)
            if kind is None:
                continue
            context = item.get("context") or "given"
            fields: dict[str, Field | None] = {}
            unsupported: list[str] = []
            for name in KIND_FIELDS[kind]:  # a medication's stray "procedure" id is ignored, not consumed
                cid = item.get(name)
                if cid is None:
                    continue
                c = by_id.get(cid)
                if c is None or c.kind != FIELD_KIND[name] or (cid in used[name] and name not in SHAREABLE):
                    unsupported.append(name)
                    continue
                used[name].add(cid)
                fields[name] = Field(value=c.value, span=c.span, confidence=min(c.confidence, LLM_CONFIDENCE),
                                     source="llm", raw=c.text)
            anchor = fields.get("drug" if kind == "medication" else "procedure")
            if anchor is None:
                continue  # an entry without its drug/procedure (or one reusing it) is not an entry
            extra = self._rules_flags(anchor, rules_entries, fields.get("time"))
            match = by_id[item["drug"]].confidence if kind == "medication" else 1.0  # lexicon match, not LLM certainty
            if match < 0.95:
                extra.append(Flag(code="low_confidence", field="drug", severity="medium",
                                  message=f"Drug name matched approximately ({match:.2f})."))
            entry = assemble(kind, context, fields, unsupported, capture_time, extra)
            if entry is not None:
                entries.append(entry)
        return entries

    @staticmethod
    def _rules_flags(anchor: Field, rules_entries: list[Entry], time: Field | None = None) -> list[Flag]:
        """Context cues the rules layer saw around the same drug span ("allergic to", "blood glucose") are kept even
        if the LLM called the entry 'given'. A time the LLM linked from outside the drug's own clause is flagged."""
        for r in rules_entries:
            r_anchor = getattr(r, "drug", None) or getattr(r, "procedure", None)
            if r_anchor is not None and r_anchor.span == anchor.span:
                out = [f for f in r.flags if f.code in CONTEXT_CODES | {"dose_range_stated"}]
                own = None if any(f.code in ("time_borrowed", "time_not_stated") for f in r.flags) else r.time.span
                if time is not None and time.span != own:
                    out.append(Flag(code="time_borrowed", field="time", severity="medium",
                                    message=f"Time '{time.raw}' was said in another part of the sentence; check it "
                                            "applies here."))
                return out
        return []
