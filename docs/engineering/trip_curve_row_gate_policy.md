# Trip-curve SQL/JSON and approximation policy gate

## Observed / expected

Curve loading checked raw JSON but ignored normalized instantaneous thresholds,
labels and policy flags. SQL/JSON divergence could pass CLI validation, while a
cached JSON flag claiming permission for verification was also ignored.

Runtime loading and CLI now share a complete row query/parser. Both instantaneous
SQL multipliers must be positive finite native numbers and exactly match their
validated JSON equivalents. Curve labels must be nonblank exportable text;
nullable device categories remain unknown when absent. Explicit JSON name/category
values must match the corresponding SQL fields. An optional JSON id must match
curve_id. No label, alias, category or threshold is inferred or rewritten.

The existing packaged SQL contract is enforced by the reader independently of
SQLite CHECK constraints: is_approximate is integer 1 and allow_for_verification
is integer 0. Conflicting, null, text and noninteger flags fail. Optional JSON
flags accept native true/false or integer 1/0 only in those same policy states;
numeric strings, floats and attempts to promote a curve fail. Cached-map engine
prechecks and standalone lookups apply this JSON policy too. Absent JSON markers
are not populated with synthetic source evidence.

Named DATASHEET_POINTS curves and their existing points/reference requirements
remain supported but approximate-only. A bibliography string or source label
does not establish authenticated manufacturer data or reviewed applicability.
Existing interpolation, endpoint handling, runtime ranges/clamping and time
estimation remain unchanged and require separate engineering review.

SQL identities are validated before dictionary access/duplicate handling, so
malformed native identities cannot escape as a hash/type error. Read-only curve
connections close explicitly; existing content-epoch/sidecar safeguards remain.
CLI adds trip_curve_policy APPROXIMATE_ONLY and describes the expanded row scope,
still reporting engineering_verification NOT_VERIFIED. Empty inventory is allowed
structurally and supplies no curve information; missing required columns fail.

Prior minimal CLI fixtures gain the required SQL columns without inserted curves.
Old direct curve-row fixtures now supply those fields while preserving every
invalid-JSON/duplicate assertion. The valid cache-refresh fixture updates both
JSON and normalized upper thresholds together, so it represents a coherent new
catalog version; its refresh assertion remains. Separate new tests require an
incoherent version to fail without cached fallback. No data repair, migration or
packaged-catalog write is performed.

## Evidence / limits

59 new cases cover SQL domains/flags, threshold and explicit metadata mismatches,
bad identities, JSON metadata/flags, valid point/metadata preservation without
approval, copied weak-schema unused rows and cache invalidation, actual CLI
policy/errors/byte preservation, empty inventory/missing columns, pre-arithmetic
cached-policy rejection, and actual engine/GUI stale-result handling in FA/EN/DE.
320 targeted regressions pass, including the prior curve/lookup/cache/catalog and
selectivity gates. Raw logs: `/workspace/audit-evidence/curve-row-*` outside checkout.

These are software consistency tests, not independent engineering references.
Numerical accuracy/tolerances, source authenticity, protection settings and duty,
curve applicability, inherited clamping/endpoint behavior, immutable database
transactions and electrical review remain unresolved. No stored curve gains
verified status. P0 stays OPEN; no merge or release is implied.

## Stable checkpoint validation

Full suite: **1453 passed, 1 failed, 1 skipped** in 71.09 s. The inherited
`TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and Windows compiler skip remain.
Helper/new-test Ruff, changed legacy-file F checks, compilation and diff checks
pass; global lint/types are not claimed clean. Actual GUI smoke recalculates four
feeders and 71 validation rows. Packaged CLI checks 16 curves with APPROXIMATE_ONLY
and all previous inventories, still NOT_VERIFIED. Packaged DB SHA256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `26669b2`; prior audit units required.
Main remains untouched.
