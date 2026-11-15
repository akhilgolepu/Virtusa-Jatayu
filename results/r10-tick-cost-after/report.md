# Tick cost of the sound-alike flag (`r10-tick-cost-after`, commit `8761138`) — IN-SAMPLE

480 dev speech clips (synthetic speech, saved transcripts), rules NER. One note = one clip. Classes use <= 2 letter edits; chosen while looking at these same clips: **in-sample**.

Drugs matched by sound: 55 correct, 4 wrong.

| Class | Correct | Wrong |
|---|---|---|
| canonical spelling variant | 25 | 0 |
| alias/brand spelling variant | 20 | 2 |
| look-alike | 10 | 2 |

| Option | Ticks per note, all (mean / p90 / max) | Sound ticks per note (mean / p90 / max) | Correct matches still ticked | Wrong drugs still sound-flagged | Wrong drugs with any high flag |
|---|---|---|---|---|---|
| current rule (round 9/10 code) | 0.719 / 2 / 5 | 0.069 / 0 / 2 | 29 | 4 of 4 | 4 of 4 |
| exempt canonical spelling variants | 0.719 / 2 / 5 | 0.069 / 0 / 2 | 29 | 4 of 4 | 4 of 4 |
| exempt canonical + alias/brand spelling variants | 0.675 / 2 / 4 | 0.025 / 0 / 1 | 10 | 2 of 4 | 4 of 4 |

## Wrong drugs matched by sound

| Utterance | Heard | Recorded | Class | Edits to canonical / nearest alias | Flag |
|---|---|---|---|---|---|
| mc01-1-011 | ASTEL | salbutamol | look-alike | 7 / 4 | sound_alike_drug |
| hi01-1-019 | At event | ipratropium | alias/brand spelling variant | 9 / 2 | sound_alike_drug |
| hi01-1-019 | chadrin | amiodarone | look-alike | 7 / 5 | sound_alike_drug |
| cn04-0-012 | salin | normal saline | alias/brand spelling variant | 7 / 1 | sound_alike_drug |

## Correct drugs matched by sound

| Utterance | Heard | Recorded | Class | Edits to canonical / nearest alias | Flag |
|---|---|---|---|---|---|
| mb07-0-004 | Solumadrol | methylprednisolone | alias/brand spelling variant | 14 / 1 | sound_alike_drug |
| mb07-1-000 | Morphin | morphine | canonical spelling variant | 1 / 8 | low_confidence |
| mb07-1-016 | Ventiline | salbutamol | alias/brand spelling variant | 10 / 2 | sound_alike_drug |
| mb07-1-018 | lorazepam1 | lorazepam | canonical spelling variant | 0 / 7 | low_confidence |
| mm02-0-008 | Narcon | naloxone | alias/brand spelling variant | 4 / 1 | sound_alike_drug |
| mm02-0-013 | furosenide | furosemide | canonical spelling variant | 1 / 3 | low_confidence |
| mm02-1-004 | decadrin | dexamethasone | alias/brand spelling variant | 9 / 1 | sound_alike_drug |
| mm02-1-014 | Salut medral | methylprednisolone | look-alike | 15 / 3 | sound_alike_drug |
| mm02-1-017 | Atropina | atropine | canonical spelling variant | 1 / 7 | low_confidence |
| mm02-2-002 | sublimates | fentanyl | alias/brand spelling variant | 9 / 2 | sound_alike_drug |
| mm02-2-004 | add an objects | adenosine | look-alike | 8 / 4 | sound_alike_drug |
| mm02-2-005 | Kettler | ketamine | alias/brand spelling variant | 5 / 2 | sound_alike_drug |
| mm02-2-009 | adextrose | dextrose | canonical spelling variant | 1 / 6 | low_confidence |
| mm02-2-012 | adexa | dexamethasone | alias/brand spelling variant | 10 / 1 | sound_alike_drug |
| mm02-2-013 | ahydrocortisone | hydrocortisone | canonical spelling variant | 1 / 6 | low_confidence |
| mm02-2-018 | add an object | adenosine | look-alike | 7 / 3 | sound_alike_drug |
| mx07-0-000 | It prevents | ipratropium | look-alike | 9 / 3 | sound_alike_drug |
| mx07-0-007 | glucagon4 | glucagon | canonical spelling variant | 0 / 1 | low_confidence |
| mx07-0-009 | Corderone | amiodarone | alias/brand spelling variant | 5 / 1 | sound_alike_drug |
| mx07-0-011 | Compose | diazepam | alias/brand spelling variant | 8 / 2 | sound_alike_drug |
| mx07-0-012 | mitroglycerin | nitroglycerin | canonical spelling variant | 1 / 2 | low_confidence |
| mx07-0-013 | cyclocaparin | tranexamic acid | look-alike | 11 / 4 | sound_alike_drug |
| mx07-1-000 | nalpinephrine | norepinephrine | look-alike | 3 / 8 | sound_alike_drug |
| mx07-1-002 | benaduel | diphenhydramine | alias/brand spelling variant | 12 / 2 | sound_alike_drug |
| mx07-1-019 | phenamine | pheniramine | canonical spelling variant | 2 / 7 | low_confidence |
| mc01-0-000 | Furosmide | furosemide | canonical spelling variant | 1 / 3 | low_confidence |
| mc01-0-002 | magsulfate | magnesium sulfate | alias/brand spelling variant | 6 / 0 | low_confidence |
| mc01-0-005 | Norepineframe | norepinephrine | look-alike | 4 / 7 | sound_alike_drug |
| mc01-0-013 | Pentazocine-60 | pentazocine | canonical spelling variant | 0 / 7 | low_confidence |
| mc01-1-019 | corderone | amiodarone | alias/brand spelling variant | 5 / 1 | sound_alike_drug |
| mc01-2-004 | at even | lorazepam | alias/brand spelling variant | 7 / 2 | sound_alike_drug |
| mc01-2-007 | paracetamoliol | paracetamol | look-alike | 3 / 9 | sound_alike_drug |
| mc01-2-009 | metroglycerin | nitroglycerin | canonical spelling variant | 2 / 3 | low_confidence |
| mc01-2-015 | hydroportisone | hydrocortisone | canonical spelling variant | 1 / 6 | low_confidence |
| mi02-0-000 | anguised | nitroglycerin | alias/brand spelling variant | 11 / 1 | sound_alike_drug |
| mi02-0-004 | paranorm | metoclopramide | alias/brand spelling variant | 11 / 2 | sound_alike_drug |
| mi02-0-008 | solumadrolite | methylprednisolone | look-alike | 13 / 4 | sound_alike_drug |
| mi02-0-013 | an adeno jiktiv | adenosine | look-alike | 7 / 6 | sound_alike_drug |
| mi02-1-006 | Cacol | calcium chloride | alias/brand spelling variant | 11 / 1 | sound_alike_drug |
| mi02-1-009 | Pexamethasone | dexamethasone | canonical spelling variant | 1 / 9 | low_confidence |
| mi02-1-017 | Solucortif | hydrocortisone | alias/brand spelling variant | 9 / 1 | sound_alike_drug |
| mi02-1-019 | glucogen | glucagon | canonical spelling variant | 2 / 1 | low_confidence |
| hi01-0-000 | furosmide | furosemide | canonical spelling variant | 1 / 3 | low_confidence |
| hi01-0-005 | Mirzolam | midazolam | canonical spelling variant | 2 / 2 | low_confidence |
| hi01-0-006 | dextrose-25G | dextrose | canonical spelling variant | 1 / 6 | low_confidence |
| hi01-1-003 | ipratopium | ipratropium | canonical spelling variant | 1 / 6 | low_confidence |
| hi01-1-011 | Solocort F100 | hydrocortisone | alias/brand spelling variant | 9 / 2 | sound_alike_drug |
| hi01-1-012 | Phenamine | pheniramine | canonical spelling variant | 2 / 7 | low_confidence |
| hi01-2-005 | g-ketamine | ketamine | canonical spelling variant | 1 / 5 | low_confidence |
| hi01-2-015 | salucortif | hydrocortisone | alias/brand spelling variant | 9 / 2 | sound_alike_drug |
| cn04-0-008 | phenamine | pheniramine | canonical spelling variant | 2 / 7 | low_confidence |
| cn04-0-013 | Keterol | ketorolac | alias/brand spelling variant | 3 / 1 | sound_alike_drug |
| cn04-1-013 | phenamine | pheniramine | canonical spelling variant | 2 / 7 | low_confidence |
| cn04-1-018 | hydropotisone | hydrocortisone | canonical spelling variant | 2 / 7 | low_confidence |
| tc01-0-009 | metazolam | midazolam | canonical spelling variant | 2 / 2 | low_confidence |
