# Bind calculated values and checks to a run

## Observed

Input/run preflight rejected changed project data and mixed identities, but callers
could edit derived current, cable, selected device or validation status while
retaining the same immutable run metadata. The bundle then appeared to belong to
the original run even though its calculated payload had changed.

## Expected / implementation

The engine now computes a canonical SHA-256 result_fingerprint over ordered feeder
outputs, panel summary and the complete ordered validation list, after statuses
are finalized. Top-level run_metadata fields are excluded to avoid a recursive
hash; every other persisted result/check field is included. One immutable metadata
instance carrying that fingerprint is assigned to the summary and all feeders.

The metadata field is optional for deserializing older records, but missing
fingerprints require recalculation before bundle export or GUI-current status.
Bundle preflight compares the full derived payload before rendering and again
before publication. GUI freshness also compares it, so GUI export actions using
the existing freshness gate cannot silently use edited results. Existing bundle
metadata manifests automatically carry the new field.

## Tests / evidence

16 new cases cover unchanged deep-copy identity and manifest parity, changed
current/cable/part/summary/status/check reason, removed checks, missing legacy
fingerprint, GUI stale behavior and a generator changing the accepted snapshot
before publication. Together with 16 prior preflight cases, 32 targeted cases pass.
One old macro-bundle fixture previously discarded all checks; it now supplies the
actual engine checks from the same demo run. Its macro/asset/count assertions
remain unchanged. No failure assertion or existing test was disabled.
Raw outputs: `/workspace/audit-evidence/result-fingerprint-*` outside the checkout.

## Remaining risks

This detects inconsistent payloads, not malicious forgery: a caller controlling
metadata can recompute a hash. No signature, trusted reviewer or independent
engineering verification is supplied. Standalone export APIs still need their own
accepted immutable context; this is not an API-wide ExportContext. The private
render snapshot remains mutable internally, so before/after checks do not prove
that no generator changed and restored intermediate state. Canonical hashes bind
exact serialized values/order and do not establish numerical tolerance equivalence.
P0 remains OPEN; no merge or release is performed.

## Stable checkpoint validation

Full suite: **713 passed, 1 failed, 1 skipped** in 31.16 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. After an explicit None guard
and test import ordering, 36 result/preflight/run-metadata cases passed again.
New test/preflight helper Ruff, changed engine/metadata F checks, compilation and
`git diff --check` pass. Global lint/type cleanliness is not claimed. Actual GUI
smoke recalculates four feeders and 71 validation rows. No database/dependency/
user-data change. Based on `0d16bb5`; requires earlier audit units. Main untouched.
