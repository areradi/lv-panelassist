# Standalone primary reports require an accepted run

## Observed

Bundle and GUI freshness checks existed, but direct ExcelExporter.export_to_excel
and PrintableReportExporter.generate_html_report calls could still render changed
project/results or an altered check list under old run metadata. A GUI freshness
check also did not prevent source changes between that check and report rendering.

## Expected / implementation

The two public primary-report APIs now use the same accepted-result guard as the
bundle. The shared function is named require_current_result; the bundle name
remains a compatibility alias. Both APIs deep-copy one project/output/summary/check
snapshot, check input identity/versions and result fingerprint before rendering,
then repeat the check before publishing a same-directory temporary file. A changed
renderer snapshot/source aborts publication and preserves an old destination.
XLSX retains its existing workbook ZIP validation. HTML publication now also uses
a temporary file, fsync and atomic replacement, rather than writing the final path
directly. No report field/calculation/status semantics are changed.

The public APIs raise ExportSnapshotError when recalculation is needed. GUI primary
Excel, printable HTML and PDF's HTML-generation path display the existing localized
stale message and do not announce success/open the rejected report. Internal render
methods are private implementation details, not accepted-run export entry points.

## Tests / evidence

20 new cases exercise both public formats for changed project/payload/check list,
missing run identity, engine changes, renderer mutation, caller-copy isolation and
GUI warnings in FA/EN/DE even if the initial GUI check was forced to pass.
Together with XLSX publication/literal-text tests, 54 targeted cases pass.

Two existing fixtures were made explicit: the control-circuit XLSX test now passes
the actual engine checks instead of discarding them; the synthetic HTML badge test
asserts public rejection before testing the private renderer's display of injected
statuses. All original sheet/badge assertions remain. No test was disabled.
Raw outputs: `/workspace/audit-evidence/standalone-preflight-*` outside the checkout.

## Remaining risks

This protects only the primary Excel/HTML report APIs. Standalone CSV, diagram,
macro and separate design-verification HTML APIs still require their own accepted
context. The primitive HTML-to-PDF converter accepts arbitrary HTML and is not an
engineering-context validator. Real PDF printing remains unaccepted here.

There is no signature/authenticity guarantee, process-wide source lock, fully
immutable renderer state or API-wide ExportContext. A before/after fingerprint
cannot detect a renderer that changes and restores intermediate state. File ACL,
concurrent-write conflicts, directory-fsync/power-loss and network-filesystem
semantics remain outside this policy. P0 remains OPEN; no independent numerical
reference/reviewer approval, merge or release is implied.

## Stable checkpoint validation

Full suite: **733 passed, 1 failed, 1 skipped** in 32.69 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New standalone cases plus
XLSX publication/literal-text checks: 54 passed; the two adjusted old fixtures and
20 new cases also passed together (22). New report helper/test module Ruff,
changed exporter/preflight F checks, compilation and `git diff --check` pass.
Global lint/type cleanliness is not claimed. Actual GUI smoke recalculates four
feeders and 71 validation rows. No database/dependency/user-data change. Based on
`973752b`; requires earlier audit units. Main stays untouched.
