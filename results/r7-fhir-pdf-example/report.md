# FHIR-lite JSON and the PDF made from it (`r7-fhir-pdf-example`, commit `cb1de5e`)

Synthetic incident, typed sentences: “gave 0.3 mg adrenaline IM two minutes ago” · “aspirin 300 mg PO at 10 40” · “patient allergic to morphine” · “blood glucose 3.2 mmol” · “started CPR” · “ondansetron 4, no sorry, 2 mg IV”. Aspirin and the morphine allergy were confirmed (the allergy's high flag acknowledged); the rest stay drafts.

Files: `example.json` (the bundle, schema-validated), `example.pdf` (rendered from that bundle), `example_pdf.txt` (text extracted from the PDF).

| Entry | FHIR status | Review status | Dose | Found in the PDF |
|---|---|---|---|---|
| epinephrine | in-progress | draft | 0.3 mg | True |
| aspirin | completed | confirmed | 300 mg | True |
| morphine | not-done | confirmed | — | True |
| dextrose | not-done | draft | 3.2 mmol | True |
| cpr | in-progress | draft | — | True |
| ondansetron | in-progress | draft | 2 mg | True |

| Check | Result |
|---|---|
| schema_valid | True |
| every_bundle_entry_in_pdf | True |
| morphine_not_given_status | not-done |
| morphine_confirmed_yet_not_done | True |
| pdf_says_not_given | True |
| glucose_reading_status | not-done |
| no_completed_not_given | True |
