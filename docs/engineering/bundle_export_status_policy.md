# Bundle export inventory and explicit PDF outcomes

## Observed

A requested PDF that failed printing was silently omitted from the ZIP. The GUI
still displayed a normal completion message. No archive record distinguished
failed PDF generation from a deliberate request to exclude PDF.

## Expected / implementation

Every successful bundle now contains 00_Export_Manifest.json and a localized
00_Export_Status.txt. The schema-versioned manifest records locale, preliminary
scope, existing run metadata (or null when absent), an actual generated-file
inventory, and PDF GENERATED / FAILED / NOT_REQUESTED status with a failure code
when available. The two inventory files explicitly exclude themselves to avoid
recursive inventory. These export states are distinct from engineering statuses;
GENERATED never means verified for construction.

The frozen BundleExportResult exposes archive file count and PDF status/reason.
The old build_document_bundle API still returns an integer count. Both use the
existing atomic-publication boundary. A failed optional PDF allows other documents
to be published with an explicit failure record; the GUI warns instead of showing
normal complete success. A mandatory generator error still aborts publication and
preserves the previous bundle. The PDF exporter supplies its specific reason.

Existing assets remain unchanged. Two inventory files add two to each count:
small-project archive 19 -> 21, demo archive 25 -> 27 (without PDF). Existing count
expectations were updated accordingly; no asset acceptance check was removed.

## Tests / evidence

15 new cases exercise actual bundle generation in FA/EN/DE with each PDF state,
exact inventory vs ZIP members, actual run-metadata parity, PDF inclusion/exclusion,
localized status notes, and actual GUI warning/success behavior. Synthetic PDF
fixtures simulate renderer outcomes only; they are not real printing evidence.
Together with 13 atomic-bundle cases, 28 targeted cases pass. Raw logs:
`/workspace/audit-evidence/bundle-status-*` outside the checkout.

## Remaining risks

This inventories existing generators' output, not a full expected-format contract,
content signing, per-file hash verification, or cross-format calculation parity.
Actual PDF printing remains broken in this cloud environment. Renderer exceptions
that escape its structured result still abort publication rather than being
silently downgraded. Run metadata is traceability, not engineering approval.
Windows/EPLAN field tests, immutable ExportContext and independent numerical
references/reviewer remain open. P0 stays OPEN; no merge or release is performed.

## Stable checkpoint validation

Full suite: **681 passed, 1 failed, 1 skipped** in 28.74 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. Bundle helper/new test module
Ruff, compilation and `git diff --check` pass. Only test import ordering changed
after the full run. Global lint/type cleanliness is not claimed. Actual GUI smoke
recalculates four feeders and 71 validation rows. No database/dependency/user-data
change. Based on `41ef302`; requires previous audit units. Main stays untouched.
