"""Seeded template expansion -> GoldUtterance list. Gold labels are correct by construction (spans recorded as
surfaces are appended), and every surface is drawn from the same lexicon the extractor uses. Gold doses come only from the lexicon's dose ranges
(datagen/doses.py), the same table the validator checks against."""
from __future__ import annotations

import hashlib
import random
import re
from functools import lru_cache
from pathlib import Path

import yaml

from datagen.compose import Composer
from datagen.doses import dose_specs, in_cited_range
from datagen.numbers import surfaces as number_surfaces
from datagen.numbers import to_words
from datagen.schema import GoldUtterance
from jatayu.lexicon import Lexicon

HERE = Path(__file__).resolve().parent
CAPTURE_TIME = "2026-10-31T10:45:00+05:30"
CAPTURE_HH, CAPTURE_MM = 10, 45

OPTIONAL_P = 0.7
FILLER_P = 0.5
ANOMALY_P = 0.05
VERBS = ["gave", "given", "pushed", "administered"]
FILLERS = ["uh", "um", "okay so", "right,"]
HI_VERBS = ["de diya", "diya", "lagaya", "chadhaya", "de di"]
CORRECTION_MARKERS = ["no sorry", "sorry", "no", "actually", "I mean"]
# Written-only unit spellings a speaker never says (keeps TTS renderings sensible).
UNSPOKEN_UNITS = {"µg", "ug", "l/min"}
SWAP = {"mg": "mcg", "mcg": "mg", "g": "mg"}
SLOT_RE = re.compile(r"(\{[^}]+\})")


@lru_cache(maxsize=1)
def load_templates() -> list[dict]:
    return yaml.safe_load((HERE / "templates.yaml").read_text("utf-8"))["families"]


def _rng(*parts) -> random.Random:
    digest = hashlib.sha256(":".join(map(str, parts)).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _cap(s: str, rng: random.Random) -> str:
    return s[0].upper() + s[1:] if s[:1].isalpha() and rng.random() < 0.25 else s


class _Renderer:
    def __init__(self, lexicon: Lexicon, family: dict, rng: random.Random):
        self.lex, self.fam, self.rng = lexicon, family, rng
        self.c = Composer()
        self.plan: dict = {}

    # ---- per-entry planning -------------------------------------------------------------
    def _plan_medication(self, segment: str) -> dict:
        rng, lex = self.rng, self.lex
        drug = rng.choice(self.fam.get("drugs") or sorted(d for d in lex.drug_names() if dose_specs(lex, d)))
        spec = rng.choice(dose_specs(lex, drug))
        value, unit, anomaly = float(rng.choice(spec["values"])), spec["unit"], None
        # A deliberate out_of_range_case: only when the dose is spoken (a unit swap only when the unit is spoken
        # too), and only if the result really is outside the drug's range on every route.
        if self.fam.get("context", "given") == "given" and "{dose}" in segment and rng.random() < ANOMALY_P:
            if unit in SWAP and "{unit}" in segment and rng.random() < 0.5:
                kind, new_value, new_unit = "unit_swap", value, SWAP[unit]
            else:
                kind, new_value, new_unit = "10x", round(value * 10, 4), unit
            if not in_cited_range(lex, drug, None, new_unit, new_value):
                anomaly, value, unit = kind, new_value, new_unit
        return {"kind": "medication", "drug": drug, "route": spec["route"], "unit": unit, "value": value,
                "anomaly": anomaly, "spec_values": spec["values"], "range_class": spec["range_class"]}

    def _plan_procedure(self) -> dict:
        return {"kind": "procedure", "proc": self.rng.choice(self.fam.get("procs") or self.lex.procedure_names())}

    # ---- surfaces -------------------------------------------------------------------------
    def _drug_surface(self, drug: str) -> str:
        if self.fam.get("drug_surfaces"):
            return self.rng.choice(self.fam["drug_surfaces"])
        aliases = self.lex.drug(drug).aliases
        if aliases and self.rng.random() < 0.5:
            self.c.tags.append("alias")
            return _cap(self.rng.choice(aliases), self.rng)
        return _cap(drug, self.rng)

    def _number_surface(self, value: float) -> str:
        forms = number_surfaces(value)
        if self.rng.random() < 0.5:
            return forms[0]
        self.c.tags.append("spoken_number")
        return self.rng.choice(forms[1:])

    def _time(self, forced: str | None = None) -> None:
        rng, c = self.rng, self.c
        kind = forced or rng.choices(["relative", "clock", "now"], weights=[55, 25, 20])[0]
        if kind == "now":
            c.time("relative", surface=rng.choice(["just now", "right now"]), offset_s=0)
        elif kind == "relative":
            n = rng.choice([1, 2, 3, 5, 10, 15])
            unit = rng.choice(["minutes ago", "mins ago", "min ago"])
            if n == 1 and rng.random() < 0.4:
                surface = "a minute ago"
            else:
                surface = f"{rng.choice([str(n), to_words(n)])} {unit}"
            c.time("relative", surface=surface, offset_s=-60 * n)
        else:
            hh = rng.choice([9, 10])
            mm = rng.randint(10, 59) if hh == 9 else rng.randint(10, CAPTURE_MM - 1)
            surface = rng.choice([f"at {hh} {mm:02d}", f"at {hh}:{mm:02d}", f"at {to_words(hh)} {to_words(mm)}"])
            c.time("clock", surface=surface, hh=hh, mm=mm)

    # ---- slots ----------------------------------------------------------------------------
    def slot(self, name: str) -> None:
        rng, c, p, lex = self.rng, self.c, self.plan, self.lex
        optional = name.endswith("?")
        name = name.rstrip("?")
        if optional and rng.random() >= (FILLER_P if name == "filler" else OPTIONAL_P):
            return
        if name == "drug":
            c.field("drug", self._drug_surface(p["drug"]), p["drug"])
        elif name == "dose":
            c.field("dose_value", self._number_surface(p["value"]), p["value"])
            if p["anomaly"]:
                c.entry.anomaly = p["anomaly"]
                c.tags += [f"anomaly:{p['anomaly']}", "out_of_range_case"]
            if p["range_class"] == "illustrative":
                c.tags.append("range:illustrative")
        elif name == "unit":
            options = [u for u in lex.unit_synonyms(p["unit"]) + [p["unit"]] if u not in UNSPOKEN_UNITS]
            c.field("dose_unit", rng.choice(options), p["unit"])
        elif name == "route":
            c.field("route", rng.choice(lex.route_synonyms(p["route"])), p["route"])
        elif name == "time":
            self._time()
        elif name == "clock":
            self._time("clock")
        elif name == "verb":
            c.add(" " + rng.choice(VERBS) + " ")
        elif name == "filler":
            c.add(" " + rng.choice(FILLERS) + " ")
            c.tags.append("filler")
        elif name == "hi_verb":
            c.add(" " + rng.choice(HI_VERBS) + " ")
        elif name == "correction":
            others = [float(v) for v in p["spec_values"] if float(v) != p["value"]]
            wrong = rng.choice(others) if others else p["value"] * 2
            c.add(f" {self._number_surface(wrong)}, {rng.choice(CORRECTION_MARKERS)}, ")
            c.tags.append("correction")
        elif name == "route_correction":
            wrong = rng.choice([r for r in lex.route_codes() if r not in (p["route"], "IN")])
            c.add(f" {rng.choice(lex.route_synonyms(wrong))}, no sorry, ")
            c.tags.append("correction")
        elif name == "mvalue":
            v = rng.choice(self.fam["mvalues"])
            c.field("measured_value", v, float(v))
        elif name == "proc":
            proc = p["proc"]
            aliases = lex.procedure(proc).aliases
            surface = rng.choice(aliases) if aliases and rng.random() < 0.6 else proc
            c.field("procedure", _cap(surface, rng), proc)
        elif name == "detail":
            d = rng.choice(self.fam["details"])
            c.field("detail", d, d)
        else:
            raise ValueError(f"unknown slot {{{name}}} in family {self.fam['id']}")

    def render(self, pattern: str, utt_id: str) -> GoldUtterance:
        context = self.fam.get("context", "given")
        for seg in pattern.split("{next}"):
            self.plan = self._plan_procedure() if "{proc}" in seg else self._plan_medication(seg)
            self.c.new_entry(self.plan["kind"], context=context)
            for part in SLOT_RE.split(seg):
                if part.startswith("{"):
                    self.slot(part[1:-1])
                elif part:
                    self.c.add(part)
        return self.c.build(id=utt_id, family=self.fam["id"], category=self.fam["category"],
                            lang=self.fam.get("lang", "en"), capture_time=CAPTURE_TIME)


def generate(seed: int, per_pattern: int = 20, lexicon: Lexicon | None = None) -> list[GoldUtterance]:
    lexicon = lexicon or Lexicon.load()
    out = []
    for fam in load_templates():
        for p_idx, pattern in enumerate(fam["patterns"]):
            for n in range(per_pattern):
                utt_id = f"{fam['id']}-{p_idx}-{n:03d}"
                out.append(_Renderer(lexicon, fam, _rng(seed, utt_id)).render(pattern, utt_id))
    return out
