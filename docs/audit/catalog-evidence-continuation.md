# P0 continuation — catalog integrity and property-specific evidence

Starting head `9e044b9` was clean. A pre-change Git bundle is retained at
`/workspace/audit-backups/pre-catalog-inputs-9e044b9.bundle`. The changes use two
review branches, preserving existing branches and main:

1. `fix/audit-06-catalog-inputs`, commit `f4c36a7`, based on
   `fix/audit-05-protection-settings`: reject invalid catalog records before
   calculation and provide a shared read-only structural validator.
2. `fix/audit-07-property-evidence`, based on that catalog branch: bind property
   proof to actual value/unit/subject/conditions, show the matching proof in
   actual engine reports, and prevent whole-device/bibliography approval claims.

See [catalog input policy](../engineering/catalog_input_policy.md),
[property evidence policy](../engineering/property_evidence_policy.md), and the
Observed / Expected / Implementation / Tests / Evidence / Remaining risks in
the [work register](work-items.md).

## Actual checks

- Catalog stage: 450 passed, one inherited PDF failure and one Windows compiler
  skip. Original packaged 102 devices / 12 selectivity records structurally valid.
- Latest full suite: **491 passed, 1 failed, 1 skipped**. The failure is still
  `TestPhase3Pdf::test_html_to_pdf_roundtrip`; `csc.exe` is still absent here.
  No assertion or test was newly disabled.
- Targeted property/evidence/catalog tests: **120 passed**, including actual
  project processing, SQL lookups, HTML/XLSX evidence rows and CLI exit codes.
- New validator/matcher modules pass selected mypy checks; new modules/tests and
  the CLI pass Ruff. The overall repository remains at 868 Ruff findings and
  21 mypy errors in 8 files; green global lint/type/CI is not claimed.
- Package compilation and real GUI startup/recalculation pass. The final GUI
  smoke processes four demo feeders and 70 validation rows.
- All catalog operations are read-only. The packaged database SHA-256 remains
  `d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
  Dependencies, lockfiles and user project data are unchanged.

Raw evidence is retained in `evidence/*catalog*` and `evidence/*evidence*`.
Input validation rejects malformed catalog data; source matching checks recorded
declarations. Neither authenticates real documents or reviewer competence.
Fixtures are explicitly synthetic and do not supply an independent engineering
reference, numerical tolerance, manufacturer approval or production sign-off.

P0 remains OPEN, as requested while independent sources/reviewer are unavailable.
Complete source/topology/earth-loop/ADS and thermal/busbar verification, catalog
schema/migration coverage, aggregate approval, all-format export acceptance and
Windows/EPLAN field tests remain outside this software-policy delivery. No merge
or release is performed.
