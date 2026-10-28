# Document bundle publication

## Observed

The document bundle builder opened the chosen ZIP with mode w before invoking
all report/macro generators. Failure in any early or late generator, ZIP writing
or finalization could replace an older complete bundle with a partial archive.

## Expected / implementation

The public build_document_bundle API now builds the existing documents into a
private temporary ZIP in the destination directory. After the builder closes the
archive, the publication helper checks CRC integrity and requires a positive,
matching, duplicate-free member count. It fsyncs the file using a read/write handle,
closes it and publishes via os.replace. Ordinary failures remove temporary output
and preserve the prior destination. The private builder retains the existing
asset generation, contents, CSV note, counts and optional-PDF behavior.

The GUI bundle action shows localized OS/invalid-ZIP failure guidance in FA/EN/DE
without a success notification. Other generator exceptions retain the existing
error display. API callers receive failures; there is no implicit retry.

## Tests / evidence

13 cases cover actual engine -> bundle generation failures in early XLSX and late
field-kit generation, a complete small-project archive reopened and inspected,
creation/fsync/publication errors, invalid ZIP, mismatched/empty archive counts,
failed first export and actual GUI action failure messages in three languages.
The small test project has 19 assets; existing demo bundle tests still require all
25 assets. No existing test or acceptance condition was removed.
Raw outputs: `/workspace/audit-evidence/bundle-atomic-*` outside the checkout.

## Remaining risks

ZIP integrity is not semantic or cross-format calculation parity. A requested PDF
that fails printing is still omitted under the existing optional-PDF policy; this
change does not claim a complete requested-format manifest or fix PDF rendering.
An explicit omissions/failures manifest remains necessary. No EPLAN/Windows field
acceptance, directory-fsync/power-loss guarantee, original ACL preservation,
concurrent-write conflict detection or network-filesystem guarantee is supplied.
Process termination or filesystem errors can prevent temporary cleanup. Standalone
HTML/SVG/DXF and other output paths remain outside this publication policy.
Engineering verification remains OPEN; no independent reference/reviewer approval,
merge or release is implied.

## Stable checkpoint validation

Full suite: **666 passed, 1 failed, 1 skipped** in 26.68 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New publication helper/test
module Ruff, compilation and `git diff --check` pass. Global lint/type cleanliness
is not claimed. Actual GUI smoke recalculates four feeders and 71 validation rows.
No database/dependency/user-data change. Based on `9ce0659`; requires previous
audit units. Main stays untouched.
