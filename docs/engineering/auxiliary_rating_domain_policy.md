# Consumed ampacity and derating table domains

## Observed

Ampacity rows were converted directly to float dictionaries, allowing bad values
or duplicate sections in inconsistent external schemas to enter selection or be
silently overwritten. Single-section queries used LIMIT 1. Derating read one
row at a greater-or-equal temperature without validating its numeric domain, so
an absent requested temperature could silently borrow an unrelated higher row.

## Expected / implementation

The three ampacity lookup APIs now share exact-combination lookup and row validation.
Sections and ampacities must be positive finite native numeric values; duplicate
sections are rejected. Section arguments and material/insulation/method identifiers
are validated. Loaded-conductor count must be a positive non-boolean integer that
fits SQLite's signed 64-bit parameter binding. Missing combinations/sections
remain empty/None; no scaling or repair is added.

Derating validates all rows for the requested device and rejects duplicate
temperatures. Stored temperature 20–80 C and positive factors <=1.2 mirror the
existing packaged SQL schema, not invented engineering tolerances. Runtime
arguments must be finite numeric values without bool/string coercion. Existing
<=40/<=50 proposal bins remain unchanged. Above 50, only the exact requested
temperature can supply a row; a higher-temperature row is not applicability proof.

Missing derating remains None at the repository API. The engine's existing
catalog-device-field fallback remains a preliminary proposal, and its existing
above-50 missing-rating validation remains active. This work does not establish
validated selection or manufacturer applicability for those legacy proposals.
Errors use localized guidance with literal table/field names in FA/EN/DE.

## Tests / evidence

54 new cases cover numeric domains, duplicate keys, supported existing factors
1.1/1.2, stored temperature bounds, conductor overflow, actual SQL query paths,
missing/exact rating conditions, and actual engine/GUI failure handling in three
languages. Corrupt DB fixtures disable CHECK enforcement only on test connections
to copied files; application code never disables constraints or repairs data.
Together with prior PE/engine regressions, 83 targeted cases pass. Invalid
calculation preserves the GUI's previous results as stale and shows an error.
Raw logs: `/workspace/audit-evidence/rating-gate-*` outside the checkout.

## Remaining risks

These are consumed-record structural checks, not full auxiliary-table CLI/schema
coverage, source authentication, physical reference limits or engineering approval.
SQLite may already normalize numeric strings/boolean-like integers before values
are read; this cannot authenticate original input representation. Unconsumed table
combinations, source applicability, real temperature interpolation and legacy
proposal bins/fallbacks still need independent review. No database/dependency/user
data change, merge or release is implied. P0 remains OPEN.

## Stable checkpoint validation

Full suite: **1144 passed, 1 failed, 1 skipped** in 43.54 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New validator/test module
Ruff, changed catalog F checks, compilation and `git diff --check` pass. Global
lint/type cleanliness is not claimed. Real GUI smoke recalculates four feeders
and 71 validation rows. Packaged DB SHA-256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
Based on `0a9aa68`; requires previous audit units. Main stays untouched.
