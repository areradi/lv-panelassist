# Enclosure proposals use the run catalog

## Observed

EngineeringEngine validated and fingerprinted its supplied catalog, but selected
enclosures via the global repository. A supplied catalog without any enclosure
could receive a packaged enclosure, while a custom enclosure was ignored. The
selected body could therefore be absent from the recorded run catalog and the
manufacturer-filtered device set. Downstream dimensions, thermal estimates and
BOM inherited this hidden selection.

## Expected / implementation

Body proposals now come from the same validated `self.catalog` used for device
selection and catalog-selection hashing, including the existing manufacturer
filter. Supported IP comparison is retained. No matching enclosure yields the
existing EST-PANEL geometry proposal, empty IP and missing-data checks, not an
outside-catalog device. A preferred manufacturer's device set without a suitable
body now produces that explicit proposal rather than silently using another maker.
The existing behavior when the preferred manufacturer has no devices at all is
unchanged. Repeated runs restore the supplied catalog before applying preference.

## Tests / evidence

Eight new synthetic cases fail before the change. They cover in-catalog/missing
body in FA/EN/DE with an outside-repository candidate, exact BOM/body consistency,
HTML/XLSX identifiers, actual catalog-selection hash, repeated manufacturer
switches, and unsupported IP. After correction, 59 related cases pass (8 new,
27 ceiling, 24 applicability). Prior ceiling fixtures now supply their bodies
through the real catalog argument instead of overriding the bypassed repository
method. Their expectations and case counts remain intact; no test is disabled.
Raw logs: `/workspace/audit-evidence/enclosure-scope-*` outside the checkout.

## Remaining risks

This corrects body-selection scope only. Cable/curve/derating/selectivity and
standards auxiliary data still use separately tracked repository paths; an
API-wide immutable ExportContext and full source isolation remain open. Geometry,
ventilation and body selection remain preliminary, with no installation, thermal
or IP certification. No independent engineering source/reviewer is available;
P0 stays OPEN. No merge or release is performed.

## Stable checkpoint validation

Full suite: **562 passed, 1 failed, 1 skipped** in 27.54 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. GUI renders/recalculates
four feeders and 71 validation rows. New/adjusted test modules pass Ruff; changed
engine F checks, compilation and `git diff --check` pass. Only whitespace in a
test signature changed after the full run. Global lint/type cleanliness is not
claimed. No database/dependency/user data change. Based on `f14003a`; requires
earlier audit units. Main stays untouched.
