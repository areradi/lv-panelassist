# PE section inventory gate

## Observed / expected

The PE inventory coerced SQL values with float() and selected a row through a
separate SQL inequality. Invalid non-selected rows could escape validation, and
zero/negative requirements could produce the smallest section. The catalog CLI
did not inspect this inventory.

Both public lookup paths now share a positive finite native-number validator.
Boolean/text/null/nonfinite values and duplicate numeric sections are rejected;
sections are sorted numerically without rounding. The selection requirement must
also be positive and finite. The complete table is checked before choosing the
smallest recorded section at least as large as the requirement. No interpolation,
invented maximum, extrapolation or fallback is introduced. Empty inventory and
requirements above the recorded range return None. Empty inventory is structurally
allowed and reported with a zero count, not as engineering completeness.

The existing content-epoch cache handles external edits and failed reloads. The
selection path also rechecks the cached list before choosing, so invalid caller
mutations cannot become a selected section. General cache-object immutability
and concurrent database snapshots remain separate work.

The read-only catalog CLI uses the same validator for every PE row and returns
an additive pe_sections count and expanded structural_scope. Missing tables and
invalid rows fail with nonzero status; existing hash/sidecar guards still apply.
Minimum synthetic CLI fixtures add an empty required table with prior assertions
preserved. No source data is repaired, migrated or rewritten.

## Evidence / limits

46 new cases cover native numeric domains/overflow, weak copied SQL schemas,
duplicates, ordering/exact boundaries, empty/above-range inventory, cache
replacement/mutation, actual CLI success/invalid/missing-table exit codes with
byte preservation, and actual engine plus headless GUI error handling in FA/EN/DE.
The GUI retains the last results as stale rather than replacing them after failure.
226 targeted regressions pass. Raw logs: `/workspace/audit-evidence/pe-gate-*`.

These are structural software policy tests, not independent engineering cases.
The inherited geometric PE proposal, Cu/k assumptions, L-PE current, clearing
time, ADS, conductor applicability and approved tolerances still require separate
evidence and electrical review. A positive table entry proves none of these.
engineering_verification remains NOT_VERIFIED; P0 stays OPEN. No merge or release.

## Stable checkpoint validation

Full suite: **1221 passed, 1 failed, 1 skipped** in 52.01 s. The inherited
`TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and Windows compiler skip remain.
New helper/test Ruff, changed legacy-file F checks, compilation and diff checks
pass; global lint/types are not claimed clean. Actual GUI smoke recalculates four
feeders with 71 validation rows. Packaged CLI reports 17 PE sections alongside
the prior inventories, with NOT_VERIFIED. Packaged DB SHA256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `b252c4c`; earlier audit units are
required. Main remains untouched.
