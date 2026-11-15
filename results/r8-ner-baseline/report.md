# Rules-first clinical NER vs a pretrained NER baseline (`r8-ner-baseline`, dev, commit `c391366`) — NOT FOR SLIDES

Word-piece merging: `first`. Procedure labels of the model: Diagnostic_procedure, Therapeutic_procedure — both mapped.

Baseline: `d4data/biomedical-ner-all` (DistilBERT, trained on MACCROBAT clinical case reports), used as downloaded — no fine-tuning, and nothing run on test or final_test. Its spans are normalised with our lexicon so both systems are scored on the same values. Per entity type, P / R / F1 over the values recognised in each utterance vs gold. Time is not scored here. **Typed dev sentences, synthetic or hand-written by us.**

## dev template sentences (480 utterances) — NOT FOR SLIDES

| Entity (gold) | rules-first NER P / R / F1 | pretrained baseline P / R / F1 |
|---|---|---|
| drug (460) | 1.000 / 1.000 / 1.000 | 0.723 / 0.665 / 0.693 |
| dose_value (380) | 0.905 / 1.000 / 0.950 | 0.672 / 0.626 / 0.648 |
| dose_unit (380) | 1.000 / 1.000 / 1.000 | 1.000 / 0.705 / 0.827 |
| route (360) | 1.000 / 1.000 / 1.000 | 0.699 / 0.303 / 0.422 |
| procedure (60) | 1.000 / 1.000 / 1.000 | 0.228 / 0.917 / 0.365 |

## off-template dev sentences (hand-written) (56 utterances) — NOT FOR SLIDES

| Entity (gold) | rules-first NER P / R / F1 | pretrained baseline P / R / F1 |
|---|---|---|
| drug (65) | 1.000 / 1.000 / 1.000 | 0.724 / 0.846 / 0.780 |
| dose_value (50) | 0.889 / 0.960 / 0.923 | 0.731 / 0.760 / 0.745 |
| dose_unit (55) | 0.982 / 0.964 / 0.973 | 0.978 / 0.818 / 0.891 |
| route (53) | 0.961 / 0.924 / 0.942 | 0.850 / 0.321 / 0.466 |
| procedure (6) | 1.000 / 1.000 / 1.000 | 0.091 / 0.167 / 0.118 |

## blind v1, evaluator-authored (spent; now dev) (32 utterances) — NOT FOR SLIDES

| Entity (gold) | rules-first NER P / R / F1 | pretrained baseline P / R / F1 |
|---|---|---|
| drug (37) | 0.892 / 0.892 / 0.892 | 0.800 / 0.540 / 0.645 |
| dose_value (30) | 0.812 / 0.867 / 0.839 | 0.650 / 0.433 / 0.520 |
| dose_unit (28) | 1.000 / 0.821 / 0.902 | 0.938 / 0.536 / 0.682 |
| route (31) | 1.000 / 0.903 / 0.949 | 0.714 / 0.161 / 0.263 |
| procedure (3) | 1.000 / 1.000 / 1.000 | 0.056 / 0.333 / 0.095 |

Pretrained labels produced (all sets): Medication 524, Dosage 499, Lab_value 332, Diagnostic_procedure 197, Administration 183, Detailed_description 154, Time 124, Therapeutic_procedure 73, Biological_structure 69, Sign_symptom 21, Date 17, Quantitative_concept 5

Caveat: the dev template sentences come from templates built with the same lexicon the rules NER uses, so the rules side is favoured there; the off-template sentences were written by us. The baseline was trained on written case reports, not dictated ambulance notes.
