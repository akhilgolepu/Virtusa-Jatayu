# Strict FHIR R4 check of the FHIR-lite example (`r9-fhir-r4-check`, commit `183bfac`)

`fhir.resources` / pydantic: 6.5.0 1.10.27 (R4 models), in a separate virtual environment. Bundle: `results/r9-fhir-pdf-example/example.json` (synthetic), checked exactly as the app emitted it: nothing added or patched. Our own check, on every bundle, is our FHIR-lite JSON Schema.

**Whole bundle as R4 Bundle: valid.** **Resources valid as R4 on their own: 20 of 20.**

Checked: R4 structure and datatypes as encoded in the fhir.resources models (required elements, cardinality, types, required-binding status codes, choice-type names, extension shape). Not checked: HL7 validator invariants beyond those models, terminology (ATC / SNOMED codes are not looked up), profiles (no US Core / IPS), reference resolution (the patient is a logical reference keyed by the incident, not a Patient resource).

| # | Resource | Status | Valid R4 | First errors |
|---|---|---|---|---|
| 0 | MedicationAdministration | in-progress | True | — |
| 1 | MedicationAdministration | completed | True | — |
| 2 | MedicationAdministration | not-done | True | — |
| 3 | MedicationAdministration | not-done | True | — |
| 4 | Procedure | in-progress | True | — |
| 5 | MedicationAdministration | in-progress | True | — |
| 6 | MedicationAdministration | in-progress | True | — |
| 7 | MedicationAdministration | in-progress | True | — |
| 8 | MedicationAdministration | in-progress | True | — |
| 9 | Procedure | not-done | True | — |
| 10 | Communication | completed | True | — |
| 11 | Communication | completed | True | — |
| 12 | Communication | completed | True | — |
| 13 | Communication | completed | True | — |
| 14 | Communication | completed | True | — |
| 15 | Communication | completed | True | — |
| 16 | Communication | completed | True | — |
| 17 | Communication | completed | True | — |
| 18 | Communication | completed | True | — |
| 19 | Communication | completed | True | — |

Bundle errors: none
