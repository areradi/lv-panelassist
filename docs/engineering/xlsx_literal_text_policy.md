# XLSX report strings are literal cells

## Observed

Most report rows prefixed strings beginning =,+,-,@ with an apostrophe, altering
engineering tags in stored values. The cable BOM row bypassed that helper and
openpyxl could store its =FUNC+LOC-W1 tag as a formula. Existing tests checked
apostrophe prefixes on only three schedule values, not persisted workbook types.

## Expected / implementation

The shared row writer now explicitly types every string cell as text, preserving
its literal value without adding a prefix. Numeric/None cells keep their normal
types. The cable BOM row uses that writer too. No report formulas are intended in
this static engineering report. The old regression now verifies exact original
values and text cell types instead of the former implementation's apostrophes.

## Tests / evidence

23 new cases cover actual engine -> XLSX -> reopen in FA/EN/DE with =,+,-,@ and
whitespace-prefixed input, real =INCOMING tags, cable BOM tags and quantities,
numeric values, absence of formula cell types, and worksheet XML without formula
elements. Direct writer cases cover whitespace before a formula-like string and
negative numeric data. Input-model whitespace normalization remains unchanged;
XML normalizes CR line endings to LF, while cell type remains text. These cases
do not execute formulas. Raw evidence: `/workspace/audit-evidence/xlsx-*`.

## Scope / remaining risks

This changes the main engineering XLSX report only. EPLAN parts/connections CSVs
remain machine-oriented and preserve raw tags. They are not certified safe to open
as spreadsheets: a distinct spreadsheet-safe CSV mode and explicit machine-import
contract are still required. No CSV import compatibility claim, real Excel field
trial or blanket security claim is made. Templates and other generated workbooks
are outside this change. No engineering calculation/verification was approved;
P0 stays OPEN. No release or merge is performed.

## Stable checkpoint validation

Full suite: **600 passed, 1 failed, 1 skipped** in 27.32 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New test module Ruff, changed
exporter F checks, compilation and `git diff --check` pass. Global lint/type
cleanliness is not claimed. GUI renders/recalculates four feeders and 71 validation
rows. No database/dependency/user-data change. Based on `41f0d30`; requires previous
audit units. Main stays untouched.
