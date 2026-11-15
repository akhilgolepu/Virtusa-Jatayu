# Rules-first clinical NER vs a pretrained NER baseline (`r7-ner-baseline`, dev, commit `472e627`)

Baseline: `d4data/biomedical-ner-all` (DistilBERT, trained on MACCROBAT clinical case reports), used as downloaded — no fine-tuning, and nothing run on test or final_test. Its spans are normalised with our lexicon so both systems are scored on the same values. Per entity type, P / R / F1 over the values recognised in each utterance vs gold. Time is not scored here. **Typed dev sentences, synthetic or hand-written by us.**

## dev template sentences (480 utterances)

| Entity (gold) | rules-first NER P / R / F1 | pretrained baseline P / R / F1 |
|---|---|---|
| drug (460) | 1.000 / 1.000 / 1.000 | 0.256 / 0.350 / 0.295 |
| dose_value (380) | 0.905 / 1.000 / 0.950 | 0.670 / 0.626 / 0.648 |
| dose_unit (380) | 1.000 / 1.000 / 1.000 | 0.993 / 0.697 / 0.819 |
| route (360) | 1.000 / 1.000 / 1.000 | 0.183 / 0.108 / 0.136 |
| procedure (60) | 1.000 / 1.000 / 1.000 | 0.169 / 0.783 / 0.278 |

## off-template dev sentences (hand-written) (56 utterances)

| Entity (gold) | rules-first NER P / R / F1 | pretrained baseline P / R / F1 |
|---|---|---|
| drug (65) | 1.000 / 1.000 / 1.000 | 0.306 / 0.508 / 0.382 |
| dose_value (50) | 0.889 / 0.960 / 0.923 | 0.731 / 0.760 / 0.745 |
| dose_unit (55) | 0.982 / 0.964 / 0.973 | 0.978 / 0.818 / 0.891 |
| route (53) | 0.961 / 0.924 / 0.942 | 0.667 / 0.264 / 0.378 |
| procedure (6) | 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 |

Pretrained labels produced (all sets): Medication 738, Dosage 531, Lab_value 316, Administration 234, Diagnostic_procedure 213, Detailed_description 189, Time 121, Therapeutic_procedure 79, Biological_structure 68, Sign_symptom 23, Date 17, Coreference 9

Caveat: the dev template sentences come from templates built with the same lexicon the rules NER uses, so the rules side is favoured there; the off-template sentences were written by us. The baseline was trained on written case reports, not dictated ambulance notes.
