# FHIR-lite JSON and the PDF made from it (`r9-fhir-pdf-example`, commit `183bfac`)

Synthetic incident, typed sentences: “gave 0.3 mg adrenaline IM two minutes ago” · “aspirin 300 mg PO at 10 40” · “patient allergic to morphine” · “blood glucose 3.2 mmol” · “started CPR” · “ondansetron 4, no sorry, 2 mg IV” · “gave furosemid 40 mg IV” · “gave levetiracetam 500 mg IV” · “atropine 0.6 mg per ml” · “unable to get IV access”. Aspirin and the morphine allergy were confirmed (the allergy's high flag acknowledged); the rest stay drafts.

Files: `example.json` (the bundle, schema-validated), `example.pdf` (rendered from that bundle), `example_pdf.txt` (text extracted from the PDF).

| Entry | Heard | FHIR status | Review status | Dose | High flags | Found in the PDF |
|---|---|---|---|---|---|---|
| epinephrine | adrenaline | in-progress | draft | 0.3 mg | — | True |
| aspirin | aspirin | completed | confirmed | 300 mg | — | True |
| morphine | morphine | not-done | confirmed | — | field_missing, possible_not_given | True |
| dextrose | glucose | not-done | draft | 3.2 mmol | possible_measurement | True |
| cpr | — | in-progress | draft | — | — | True |
| ondansetron | ondansetron | in-progress | draft | 2 mg | — | True |
| furosemide | furosemid | in-progress | draft | 40 mg | sound_alike_drug | True |
| levetiracetam | levetiracetam | in-progress | draft | 500 mg | drug_not_in_lexicon | True |
| atropine | atropine | in-progress | draft | — | concentration_not_dose | True |
| iv cannulation | — | not-done | draft | — | possible_not_given | True |

| Check | Result |
|---|---|
| schema_valid | True |
| every_bundle_entry_in_pdf | True |
| morphine_not_given_status | not-done |
| morphine_confirmed_yet_not_done | True |
| pdf_says_not_given | True |
| glucose_reading_status | not-done |
| every_resource_has_subject | True |
| transcripts_as_communications | True |
| sound_alike_heard_word_in_pdf | True |
| unknown_drug_kept | True |
| concentration_has_no_dose | True |
| procedure_not_done | True |
| no_completed_not_given | True |
