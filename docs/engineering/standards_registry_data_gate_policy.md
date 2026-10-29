# Standards registry payload gate

## Observed / expected

The cached registry used unchecked json.loads()/dictionary assignment. The report
registry independently reread SQL and silently skipped unrecognized payloads;
duplicate localized identities could overwrite each other. Registry version
hashing identified raw rows without checking their contents, so malformed unused
records could accompany a completed calculation. CLI checked IDs only.

One shared parser now preserves both packaged shapes: code/optional-edition
metadata rows and direct or collected localized title/scope entries. Row and
localized IDs must be nonblank exportable strings without surrounding whitespace.
IDs retain their spelling; no alias or standard-code equivalence is inferred.
An optional payload id must match its owning row or nested entry. Duplicate SQL
IDs, duplicate JSON keys at every level and duplicate flattened localized IDs
fail even if their values agree. Non-object/empty unsupported payloads, invalid
title/scope maps and blank/nontext translations fail instead of being skipped.

Localized titles require a nonempty map; scope is optional and may be empty.
Language keys are not restricted to FA/EN/DE. Metadata code is nonblank text;
edition remains optional text/null and is never invented. JSON-compatible extra
metadata is preserved. Nonfinite numbers, unsupported/cyclic cached values and
unexportable text anywhere are rejected. Unsafe duplicate keys are checked before
building diagnostic text, preserving structured CLI errors for surrogate input.

Cached SQL loading and CLI share this parser. Report titles/scopes use that cache
and revalidate the flattened view to catch invalid caller mutations. Existing
FA/EN/DE lookup and English/identifier/empty-scope fallbacks for absent translations
or unknown valid IDs remain. Cache reloads retain existing content-epoch guards.
Read-only registry connections now close explicitly.

Registry hashing validates the complete rowset before creating run metadata and
checks main-file identity before/after reading, including existing sidecar guards.
The hash still covers the original ordered raw rows, so whitespace-only source
changes remain detectable and existing hash semantics are preserved. No malformed
registry can receive a completed engine result. This is not a multi-table immutable
transaction and does not eliminate concurrent replace/restore races.

CLI reports additive standards_registry_rows/localized_standard_entries counts
and expanded structural_scope. A successful structural check still declares
engineering_verification NOT_VERIFIED. The synthetic ampacity fixture now supplies
an explicit synthetic code instead of an unsupported empty object; previous
assertions and all tests remain active. No edition/reference is fabricated.

## Evidence / limits

54 new cases cover raw/native/schema/text/nonfinite domains, duplicate keys/IDs,
mixed supported shapes, nullable edition, cache reload/mutation, raw-hash
compatibility and file changes, actual CLI structured success/failure and byte
preservation, sidecars, and actual engine/GUI failures in FA/EN/DE. GUI keeps the
previous run as stale when recalculation fails. 171 targeted regressions pass.
Raw logs: `/workspace/audit-evidence/registry-gate-*` outside the checkout.

These tests establish software structure only. Normalized registry SQL columns,
standard editions/applicability, source authentication, actual reference pages,
approved tolerances, catalog-wide reference completeness and electrical review
remain separate work. Unknown identifiers are not evidence of a known source.
General cached-object immutability remains open. P0 stays OPEN; no merge/release
or engineering sign-off is implied.

## Stable checkpoint validation

Full suite: **1336 passed, 1 failed, 1 skipped** in 56.90 s. The inherited
`TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and Windows compiler skip
remain. New-helper/test Ruff, changed legacy-file F checks, compilation and diff
checks pass; global lint/types are not claimed clean. Actual GUI smoke recalculates
four feeders and 71 validation rows. Packaged CLI reports two registry rows and
16 localized entries alongside prior inventories, still NOT_VERIFIED. Packaged
DB SHA256 remains `d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `01025c3`; prior audit units are
required. Main remains untouched.
