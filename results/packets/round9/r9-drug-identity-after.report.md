# Drug identity on dev speech (`r9-drug-identity-after`, commit `1fa9301`)

480 dev speech clips (synthetic speech, saved transcripts `results/r4-dev-audio-rules-no-asr-flag/transcripts.jsonl`), rules NER + validator + low_asr_confidence. Dev only.

## 1. Wrong drug recorded as a known drug

- Entries: **10** (6 exact word, 4 by sound).
- With no identity flag stronger than low_confidence / low_asr_confidence: **6**.
- With no high-severity flag at all (confirmable without ticking anything): **1**.
- Needing the sound-alike acknowledgement: **4**.
- Correct drugs matched by sound: 55, of which 49 now need the acknowledgement.

| Utterance | Heard | Recorded | Gold drug(s) | Match | Identity flags | High flags |
|---|---|---|---|---|---|---|
| mx07-1-016 | adenosine | adenosine | calcium chloride, epinephrine | exact word (1.0) | — | dose_range_stated, route_not_allowed |
| mc01-1-011 | ASTEL | salbutamol | ondansetron | by sound (0.889) | sound_alike_drug | field_missing, sound_alike_drug |
| mi02-1-015 | oxygen | oxygen | calcium chloride | exact word (1.0) | low_asr_confidence | field_missing |
| mi02-1-018 | salbutamol | salbutamol | methylprednisolone | exact word (1.0) | low_asr_confidence | field_missing |
| hi01-0-001 | Atropine | atropine | epinephrine | exact word (1.0) | low_asr_confidence | — |
| hi01-1-019 | At event | ipratropium | lorazepam | by sound (0.909) | low_asr_confidence, sound_alike_drug | dose_out_of_range, sound_alike_drug |
| hi01-1-019 | chadrin | amiodarone | lorazepam | by sound (0.889) | low_asr_confidence, sound_alike_drug | field_missing, sound_alike_drug |
| hi01-1-019 | adenosine | adenosine | lorazepam | exact word (1.0) | low_asr_confidence | field_missing |
| cn04-0-012 | salin | normal saline | salbutamol | by sound (0.909) | sound_alike_drug | possible_not_given, sound_alike_drug, unit_not_allowed |
| tc01-1-019 | Salbutamol | salbutamol | methylprednisolone | exact word (1.0) | low_asr_confidence | route_not_allowed |

## 2. drug_not_in_lexicon flag, against the hand labels

Flags raised: **42** — drug 37, junk 2, other 3. Precision **0.881**, recall **0.974** (of 38 drug-labelled entries).

| Utterance | Heard | Label |
|---|---|---|
| mb07-0-011 | Vomicind | drug |
| mb07-0-014 | Tixa | drug |
| mb07-0-017 | Matbok | drug |
| mm02-1-000 | Thaxia | drug |
| mm02-2-015 | averse | drug |
| mx07-0-001 | glucetin | drug |
| mx07-0-004 | cackle | drug |
| mx07-0-015 | Epitropion | drug |
| mx07-0-018 | ringless | drug |
| mx07-1-000 | nacin | drug |
| mx07-1-002 | linolectate | drug |
| mx07-1-005 | metrolizarin | drug |
| mx07-1-006 | naco | drug |
| mx07-1-011 | valion | drug |
| mx07-1-013 | drumming | drug |
| mx07-1-015 | adenogenic | drug |
| mx07-1-019 | catalyzed | drug |
| mc01-0-008 | Nesolam | drug |
| mc01-0-011 | thalumidiol | drug |
| mc01-0-012 | Heterol | drug |
| mc01-1-011 | VOMITINE | drug |
| mc01-2-001 | Benetryl | drug |
| mi02-1-018 | tivendat | junk |
| hi01-0-007 | Chloron | drug |
| hi01-0-008 | benatev | drug |
| hi01-0-011 | slows | drug |
| hi01-1-016 | Textures | drug |
| hi01-2-012 | kefelol | drug |
| cn04-0-000 | NOPY | drug |
| cn04-0-004 | Koehler | drug |
| cn04-0-010 | perinol | drug |
| cn04-0-015 | spring | drug |
| cn04-1-003 | Larco | drug |
| cn04-1-012 | noregenerant | drug |
| cn04-1-016 | Homefuls | drug |
| cm05-1-002 | Deromegnesium | other |
| cm05-1-006 | Ceramachinesium | other |
| cm05-1-012 | Ceramagnesian | other |
| tc01-0-002 | adenergic | drug |
| tc01-0-016 | adenogenic | drug |
| tc01-1-006 | Vucose | drug |
| tc01-1-013 | elida | junk |
