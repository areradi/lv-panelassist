# CSV export destinations

## Observed

The three CSV exporters wrote raw strings using csv.writer. Quoting handles field
boundaries, not spreadsheet formulas. Blindly prefixing all fields would alter
EPLAN function/location/device tags, so a single implicit format cannot serve both
spreadsheet viewing and literal machine interchange.

## Implementation / user behavior

CsvMode.MACHINE preserves existing UTF-8-BOM encoding, headers, fields, order,
quantities and tags. It remains the API default for compatibility. It is explicitly
not spreadsheet-safe and EPLAN 2024 compatibility remains untested.

CsvMode.SPREADSHEET prefixes formula-like string fields with an apostrophe,
including leading whitespace/BOM before =,+,-,@. Actual numeric values are not
converted to protected strings. No tag whitelist bypasses text protection. The
file is for spreadsheet viewing, not machine import; its stored tag value differs.
Keep the original export: spreadsheet save/reimport behavior is not guaranteed.
An invalid mode is rejected before opening the destination.

All three GUI CSV actions ask for the intended destination (Yes spreadsheet,
No EPLAN machine, Cancel no export), use destination-specific filenames and show
localized completion guidance. The ZIP retains machine CSVs and includes a
localized 00_CSV_README.txt explaining use and the XLSX/spreadsheet-CSV alternative.
Existing bundle count tests now require 25 files instead of 24 and validate the
added note; no previous expected bundle asset was removed.

## Tests / evidence

24 cases exercise attack-like strings without executing them, whitespace/BOM,
negative numeric values, mode validation with old-file preservation, actual engine
results through each exporter (default byte equality to explicit machine mode and
field-by-field protected output), three GUI actions, target/cancel behavior and
messages in FA/EN/DE. Existing tests retain raw EPLAN tag expectations.
Raw outputs: `/workspace/audit-evidence/csv-modes-*` outside the checkout.

## Remaining risks

No real Excel/LibreOffice or EPLAN import acceptance is claimed. Apostrophe-based
CSV protection depends on consumer behavior; use the typed XLSX report when possible.
Formula safety after manually removing prefixes or saving in another application
is not established. Raw machine CSVs must not be opened as spreadsheets. Output
write atomicity for CSV, API-wide ExportContext and all-format status parity remain
open. No database, dependency or engineering formula changes. P0 stays OPEN and no
engineering reference/reviewer approval or release/merge is implied.

## Stable checkpoint validation

Full suite: **624 passed, 1 failed, 1 skipped** in 32.68 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New writer/test module Ruff,
outputs.py F checks, compilation and `git diff --check` pass. Control-circuit
module retains its existing unused Optional/tag findings; global lint/type
cleanliness is not claimed. GUI renders/recalculates four feeders and 71 validation
rows. No database/dependency/user-data change. Based on `5a14204`; requires earlier
audit units. Main stays untouched.
