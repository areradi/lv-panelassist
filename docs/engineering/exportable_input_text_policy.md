# Exportable engineering input text

## Observed

Project/feeder/catalog/provenance strings could contain NUL, invalid XML control
characters or surrogate code points. Such values could survive input construction
and later fail UTF-8 hashing, XLSX/XML serialization or report generation. GUI
recalculation did not handle an expected ValueError from revalidation of mutable
input models.

## Expected / implementation

A shared before-field validator on ProjectSpec, FeederInput, CatalogDevice and
PropertySource rejects XML 1.0-invalid C0 characters (except TAB/LF/CR), UTF-16
surrogate code points and U+FFFE/U+FFFF. It scans nested input containers/model
instances, including provenance mapping keys and a mutated PropertySource passed
into a device. Visited-container tracking prevents the scanner itself cycling;
normal schema validation still determines whether the input structure is valid.

The scanner never removes/replaces text. Persian ZWNJ, German characters, emoji,
markup/formula-like text and engineering tags remain permitted; existing outer
whitespace stripping/schema constraints are unchanged. Error messages identify
the model field and unsupported code point in FA/EN/DE. The diagnostic U+XXXX code
is kept ASCII independently of localized digit formatting.

Existing engine snapshot revalidation applies the same policy to mutated project,
feeder and catalog inputs before arithmetic. GUI recalculation now handles expected
ValueError: prior results remain intact but stale, and the error is displayed;
there is no new successful calculation or automatic removal of the bad character.

## Tests / evidence

60 new cases cover 11 invalid code points across four input model types, localized
field/code messages, nested provenance/mutated source instances, actual engine
rejection before arithmetic, valid multilingual/ZWNJ/emoji/tag/newline input through
engine -> XLSX/HTML, and GUI error/stale behavior in three languages. No engineering
values or tolerances are asserted as independently verified.
Raw logs: `/workspace/audit-evidence/text-input-*` outside the checkout.

## Remaining risks

This covers the four named input models, not every raw auxiliary database table,
computed annotation or external file/parser. It is an interchange-character policy,
not complete BMK/tag grammar validation, font/RTL acceptance, Unicode normalization,
HTML escaping or spreadsheet-formula protection; those remain separate layers.
TAB/LF/CR are intentionally valid; existing model outer-whitespace normalization
still applies. OS/process failures beyond expected input ValueError are not newly
handled by the recalculation callback. Numeric/reference correctness, real field
acceptance and independent engineering reviewer remain open. P0 stays OPEN; no
merge or release is performed.

## Stable checkpoint validation

Full suite: **965 passed, 1 failed, 1 skipped** in 48.18 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New text/engine/report/GUI
cases: 60 passed. New helper/test module Ruff, compilation and `git diff --check`
pass. Global lint/type cleanliness is not claimed. Actual GUI smoke recalculates
four feeders and 71 validation rows. No database/dependency/user-data change.
Based on `96f964b`; requires earlier audit units. Main stays untouched.
