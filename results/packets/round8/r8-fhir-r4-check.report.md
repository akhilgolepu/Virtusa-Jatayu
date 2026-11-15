# Strict FHIR R4 check of the FHIR-lite example (`r8-fhir-r4-check`, commit `a1b2602`)

`fhir.resources` / pydantic: 6.5.0 1.10.27 (R4 models), in a separate virtual environment. Bundle: `results/r7-fhir-pdf-example/example.json` (synthetic). Our own check is our FHIR-lite JSON Schema; this only shows how far FHIR-lite is from strict R4.

**Whole bundle as R4 Bundle: NOT valid.** **Resources valid as R4 on their own: 0 of 6.**

| # | Resource | Status | Valid R4 | First errors | Valid with a placeholder `subject` added |
|---|---|---|---|---|---|
| 0 | MedicationAdministration | in-progress | False | subject: field required | True  |
| 1 | MedicationAdministration | completed | False | subject: field required | True  |
| 2 | MedicationAdministration | not-done | False | subject: field required | True  |
| 3 | MedicationAdministration | not-done | False | subject: field required | True  |
| 4 | Procedure | in-progress | False | subject: field required | True  |
| 5 | MedicationAdministration | in-progress | False | subject: field required | True  |

Bundle errors: meta.device: extra fields not permitted; entry.0.resource.subject: field required; entry.1.resource.subject: field required; entry.2.resource.subject: field required; entry.3.resource.subject: field required; entry.4.resource.subject: field required; entry.5.resource.subject: field required; incident: extra fields not permitted
