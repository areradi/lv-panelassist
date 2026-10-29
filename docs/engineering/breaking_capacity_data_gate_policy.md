# Breaking capacity inventory gate

## Observed / expected

The exact-voltage Icu query selected only the first matching row. It coerced SQL
text with float(), omitted duplicate/reference checks and ignored malformed rows
for other voltages of that device. The structural CLI omitted the normalized
breaking-capacity table entirely.

The shared parser now requires valid nonblank exportable device IDs that exist
in the device table, positive finite native voltage/Icu numbers, and distinct
device/voltage keys. Optional Ics remains None when absent; a supplied value must
be positive and finite. Ics is never inferred from Icu by this reader. No Ics/Icu
relationship, source authenticity, standard applicability or sufficiency is
claimed by these numeric checks.

Runtime lookup validates the requested device ID, voltage and native finite zero
tolerance, reads all rows for that device, then selects only an exact recorded
voltage. Different recorded voltages may have different capacities. Missing exact
conditions or a missing device with no rating rows return None. A dangling rating
is an error. Nearby-voltage substitution stays unsupported. Read-only connections
close explicitly, and pre/post file hashes plus existing sidecar guards reject
detected version changes. These checks are not an immutable database transaction
and cannot eliminate replace/restore races.

Stored zero/null Icu is now rejected in both runtime and CLI, matching the existing
normalized SQL positive/NOT NULL contract. Prior unit-1 assertions expecting these
sentinels to mean unknown are explicitly strengthened to require rejection. The
assertions for valid, negative, nonfinite and text values remain. The prior minimal
fixture adds the required Ics column and an empty table for CLI coverage. General
device-model zero sentinels are unchanged. Absence is represented by a missing
exact-condition row, not by an invalid stored rating.

The CLI checks every row, including unused devices/voltages, and reports additive
breaking_capacity_rows and breaking_capacity_devices counts with expanded scope.
It exits nonzero for invalid/missing tables and preserves file bytes. Empty
inventory can be structurally valid but does not establish complete rating data.
No repairs, migration, new ratings or package-database edits are performed.

## Evidence / limits

61 new cases cover numeric/identity/request domains including bool/text/overflow,
nullable Ics, exact/missing conditions, duplicates, bad non-selected rows, dangling
references, file-version changes/sidecars, actual CLI counts/errors/missing tables
with byte preservation, and actual engine plus GUI error handling in FA/EN/DE.
GUI retains the prior results as stale on failure. 258 targeted regressions pass.
Raw logs: `/workspace/audit-evidence/breaking-gate-*` outside the checkout.

These are software policy checks, not independent engineering reference cases.
The existing migration's assumptions (including copied 400/415 V ratings and
Ics defaults), manufacturer documents, Ics/Icu relations and duty, source/voltage
applicability, backup/coordination, and electrical review remain unresolved. No
existing generated value gains verified status. engineering_verification stays
NOT_VERIFIED and P0 stays OPEN. No merge or release is implied.

## Stable checkpoint validation

Full suite: **1282 passed, 1 failed, 1 skipped** in 50.17 s. The inherited
`TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and Windows compiler skip
remain. New-test Ruff, changed legacy-file F checks, compilation and diff checks
pass; global lint/types are not claimed clean. Actual GUI smoke recalculates four
feeders and 71 validation rows. Packaged CLI reports 70 breaking-capacity rows
for 35 devices alongside previous inventories, still NOT_VERIFIED. Packaged DB
SHA256 remains `d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `3444df9`; preceding audit units are
required. Main remains untouched.
