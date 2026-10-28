# Main XLSX report publication

## Observed

ExcelExporter wrote its completed workbook directly to the destination via
Workbook.save(filename). A serialization/disk error could leave a truncated ZIP
and destroy an older report. The GUI report action did not handle file-write
errors and the report lacked a publication boundary.

## Expected / implementation

The main engineering report now saves into a private temporary binary file in
the destination directory. After openpyxl finishes, it flushes and checks ZIP
integrity, required workbook/content-type entries, fsyncs and closes the file,
then publishes with os.replace. Temporary output is removed on ordinary failure.
This is a ZIP/basic structure check, not Excel semantic/engineering verification.

An existing destination is unchanged before successful publication; failed first
exports leave no destination. OS and invalid-ZIP failures reach the GUI as a
localized error in FA/EN/DE, with no success notification. API/bundle callers keep
receiving exceptions. Workbook values, cell types, sheet names, statuses, BOM and
calculations are unchanged; existing literal-string regressions remain enabled.

## Tests / evidence

Eleven new tests exercise the actual engine -> report path at partial save,
temporary creation, fsync, replacement, invalid ZIP, missing workbook entries and
failed first export. A successful replacement is reopened with openpyxl and
checked for manifest/schedule values. Actual GUI action failures are tested in
FA/EN/DE. Together with 23 literal-text cases, 34 targeted cases cover publication
and report content. Failure cases are injected, not real full-disk/Windows trials.
Raw outputs: `/workspace/audit-evidence/xlsx-atomic-*` outside the checkout.

## Remaining risks

This applies only to the main engineering XLSX report. Other workbooks, HTML,
ZIP bundles and generated diagrams still need format-specific publication policy.
No directory fsync/power-loss guarantee, original destination ACL preservation,
concurrent-write conflict detection or network-filesystem guarantee is provided.
New files use private temporary-file permissions. Cleanup can fail under OS
errors or process termination. Windows locked-file, Excel rendering, and EPLAN
acceptance remain open. P0 engineering verification remains OPEN; no independent
reference/reviewer approval, merge or release is implied.

## Stable checkpoint validation

Full suite: **653 passed, 1 failed, 1 skipped** in 27.93 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New helper/test module Ruff,
changed exporter F checks, compilation and `git diff --check` pass. Global lint/type
cleanliness is not claimed. Actual GUI smoke recalculates four feeders and
71 validation rows. No database/dependency/user-data change. Based on `bbd2f83`;
requires previous audit units. Main stays untouched.
