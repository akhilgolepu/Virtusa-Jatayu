"""python -m eval.ner_baseline --tag r7-ner-baseline   (dev only; a separate evaluation, not part of the pipeline)

Compares the rules-first clinical NER with one off-the-shelf pretrained NER model, d4data/biomedical-ner-all
(DistilBERT trained on MACCROBAT clinical case reports; no fine-tuning by us), on the dev typed sentences: the dev
template split and the hand-written off-template dev set.

Scoring is per entity type, on the SET of normalised values each system recognises in an utterance vs the gold values
(any administration status): drug, dose value, dose unit, route, procedure. Time is not scored here (the model's
Date/Time spans would need our time parser to become comparable). The pretrained model's spans are normalised with our
lexicon (exact name/alias, else fuzzy >= 88), so both systems are judged on the same values:
  Medication -> drug · Dosage -> dose value (+ unit) · Administration -> route ·
  Therapeutic_procedure / Diagnostic_procedure -> procedure."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from datagen.splits import load_split
from eval.runlog import log_run
from jatayu import config

TYPES = ("drug", "dose_value", "dose_unit", "route", "procedure")
MODEL = config.MODELS_DIR / "ner" / "biomedical-ner-all"
LABELS = {"Medication": "drug", "Dosage": "dosage", "Administration": "route",
          "Therapeutic_procedure": "procedure", "Diagnostic_procedure": "procedure"}


def _gold(u) -> Counter:
    c = Counter()
    for g in u.entries:
        for t in TYPES:
            f = getattr(g, t, None)
            if f is not None and f.value is not None:
                c[(t, round(float(f.value), 6) if t == "dose_value" else str(f.value))] += 1
    return c


def _ngrams(words: list[str]):
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            yield " ".join(words[i:i + n])


def _span_values(label: str, text: str, lex) -> list[tuple[str, object]]:
    from jatayu.normalise import normalise

    toks = [t for t in normalise(text).tokens if t.kind != "punct"]
    words = [t.text for t in toks]
    out = []
    if label == "drug":
        hit = next((lex.lookup_drug(g) for g in _ngrams(words) if lex.lookup_drug(g)), None)
        if hit is None and words:
            fz = lex.fuzzy_drug(" ".join(words), 88)
            hit = fz[0] if fz else None
        out.append(("drug", hit or text.strip().lower()))
    elif label == "dosage":
        nums = [t for t in toks if t.kind == "number"]
        if nums:
            out.append(("dose_value", round(float(nums[0].value), 6)))
        unit = next((lex.canonical_unit(g) for g in _ngrams(words) if lex.canonical_unit(g)), None)
        if unit:
            out.append(("dose_unit", unit))
    elif label == "route":
        r = next((lex.canonical_route(g) for g in _ngrams(words) if lex.canonical_route(g)), None)
        out.append(("route", r or text.strip().lower()))
    elif label == "procedure":
        p = next((lex.lookup_procedure(g) for g in _ngrams(words) if lex.lookup_procedure(g)), None)
        out.append(("procedure", p or text.strip().lower()))
    return out


def _rules(u, x, lex) -> Counter:
    from jatayu.validate import validate_all

    c = Counter()
    for e in validate_all(x.extract(u.text, datetime.fromisoformat(u.capture_time)), lex, []):
        for t in TYPES:
            f = getattr(e, t, None)
            if f is not None and f.value is not None:
                c[(t, round(float(f.value), 6) if t == "dose_value" else str(f.value))] += 1
    return c


def _score(pairs: list[tuple[Counter, Counter]]) -> dict:
    out = {}
    for t in TYPES:
        tp = fp = fn = 0
        for pred, gold in pairs:
            p = Counter({k: v for k, v in pred.items() if k[0] == t})
            g = Counter({k: v for k, v in gold.items() if k[0] == t})
            hit = sum((p & g).values())
            tp, fp, fn = tp + hit, fp + sum(p.values()) - hit, fn + sum(g.values()) - hit
        P = tp / (tp + fp) if tp + fp else 0.0
        R = tp / (tp + fn) if tp + fn else 0.0
        out[t] = {"precision": round(P, 4), "recall": round(R, 4), "f1": round(2 * P * R / (P + R), 4) if P + R else 0.0,
                  "gold": tp + fn}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, default=config.ROOT / "results")
    args = ap.parse_args(argv)
    from transformers import pipeline

    from eval.offtemplate import load as load_offtemplate
    from jatayu.extract.rules import RulesExtractor
    from jatayu.lexicon import Lexicon

    start = log_run(args.out, runner="eval.ner_baseline", split="dev", tag=args.tag, model=MODEL.name)
    lex = Lexicon.load()
    rules = RulesExtractor(lex)
    ner = pipeline("token-classification", model=str(MODEL), aggregation_strategy="simple", device=0)
    sets = {"dev template sentences": load_split("dev"), "off-template dev sentences (hand-written)": load_offtemplate()}
    res, labels_seen = {}, Counter()
    for name, utts in sets.items():
        pr, pb = [], []
        for u in utts:
            gold = _gold(u)
            pr.append((_rules(u, rules, lex), gold))
            base = Counter()
            for ent in ner(u.text):
                labels_seen[ent["entity_group"]] += 1
                if ent["entity_group"] in LABELS:
                    base.update(_span_values(LABELS[ent["entity_group"]], ent["word"], lex))
            pb.append((base, gold))
        res[name] = {"utterances": len(utts), "rules": _score(pr), "pretrained": _score(pb)}
    out = args.out / args.tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps({"commit": start["commit"], "model": MODEL.name, "results": res,
                                                  "pretrained_labels_seen": dict(labels_seen.most_common())}, indent=2) + "\n")
    L = [f"# Rules-first clinical NER vs a pretrained NER baseline (`{args.tag}`, dev, commit `{start['commit']}`)", "",
         "Baseline: `d4data/biomedical-ner-all` (DistilBERT, trained on MACCROBAT clinical case reports), used as "
         "downloaded — no fine-tuning, and nothing run on test or final_test. Its spans are normalised with our lexicon "
         "so both systems are scored on the same values. Per entity type, P / R / F1 over the values recognised in each "
         "utterance vs gold. Time is not scored here. **Typed dev sentences, synthetic or hand-written by us.**", ""]
    for name, r in res.items():
        L += [f"## {name} ({r['utterances']} utterances)", "",
              "| Entity (gold) | rules-first NER P / R / F1 | pretrained baseline P / R / F1 |", "|---|---|---|"]
        for t in TYPES:
            a, b = r["rules"][t], r["pretrained"][t]
            L.append(f"| {t} ({a['gold']}) | {a['precision']:.3f} / {a['recall']:.3f} / {a['f1']:.3f} | "
                     f"{b['precision']:.3f} / {b['recall']:.3f} / {b['f1']:.3f} |")
        L.append("")
    L += ["Pretrained labels produced (all sets): " + ", ".join(f"{k} {v}" for k, v in labels_seen.most_common(12)), "",
          "Caveat: the dev template sentences come from templates built with the same lexicon the rules NER uses, so the "
          "rules side is favoured there; the off-template sentences were written by us. The baseline was trained on "
          "written case reports, not dictated ambulance notes."]
    (out / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
