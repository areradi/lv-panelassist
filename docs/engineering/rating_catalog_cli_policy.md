# Read-only rating inventory validation

## Observed

The catalog CLI checked devices, selectivity and trip curves but did not inspect
ampacity/thermal inventory. Runtime validation covered only requested combinations,
so malformed or unreferenced rows unused by the current project could escape a
successful CLI report.

## Expected / implementation

The CLI now enumerates all cable ampacity and device thermal rows. Ampacity is
grouped by normalized material/insulation/method/conductor count before the shared
positive-finite/duplicate-section validator runs. Structural material/insulation
codes mirror the existing schema, while method remains a nonblank identifier.
Standard/table references must be valid text and standard IDs must exist.
Thermal rows must reference a known device and pass the shared schema-domain and
duplicate-temperature validator. Different valid combinations may share sections.

The reported inventory includes row/combination/device counts. A main-file hash
is checked before and after validation and returned as catalog_hash. Existing
nonempty WAL/journal rejection applies. Changed or untracked file states cannot
receive a normal structural-success response. The read-only connection is closed
explicitly. Integrity-check failures now include SQLite's table-level diagnostic.
No file is migrated, repaired, checkpointed or rewritten by the validator.

Minimum synthetic CLI fixtures add empty rating/standard tables for the expanded
required scope; no engineering reference or rating value is invented. Output
continues to declare engineering_verification NOT_VERIFIED, including on success.

## Tests / evidence

31 new cases cover unused malformed numeric/identity/source rows, duplicate
conditions and normalized case collisions, valid separate combinations, missing
required tables, actual CLI success/invalid JSON/exit codes with byte preservation,
nonempty sidecars without modification, and injected file-version change during
validation. Together with rating and prior catalog gates, 132 targeted cases pass.
Schemas are intentionally weak copied/synthetic fixtures so parser checks are
exercised independently of SQLite CHECK constraints.
Raw logs: `/workspace/audit-evidence/rating-cli-*` outside the checkout.

## Remaining risks

Presence of a referenced standard is not source authentication, field applicability,
numerical approval or assurance of complete catalog coverage. Registry payloads,
other auxiliary tables, full schema/FK/migration coverage and real operating
conditions still require separate validation. Hash checks are not a lock or a
multi-table immutable transaction and do not eliminate replace/restore races.
No independent reference/reviewer, merge or release is implied. P0 remains OPEN.

## Stable checkpoint validation

Full suite: **1175 passed, 1 failed, 1 skipped** in 49.64 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. Rating helper/new test module
Ruff, changed catalog-validator F checks, compilation and `git diff --check` pass.
Global lint/type cleanliness is not claimed. Actual GUI smoke recalculates four
feeders and 71 validation rows. Packaged CLI result: 102 devices, 12 selectivity
rules, 16 curves, 16 ampacity rows and 204 thermal rows; NOT_VERIFIED. DB hash stays
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependency/user-data change. Based on `af41944`; earlier audit units required.
Main stays untouched.
