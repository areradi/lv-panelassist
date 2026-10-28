# Bundle API run-identity preflight

## Observed

GUI freshness checks existed, but direct build_document_bundle calls could combine
a changed ProjectSpec with old calculated outputs and publish mixed metadata and
report values. Missing/mixed feeder run identities were not rejected by the API.
Generators also received the caller's mutable objects directly.

## Expected / implementation

The public structured bundle API now deep-copies project, feeder outputs, summary
and validations for one private render snapshot. Before any staging, it requires
summary metadata, parseable model-valid recorded inputs, matching project/revision,
matching feeder IDs/order and feeder run identities, and the existing input hash,
engine version/source hash, catalog file hash and standards-registry freshness
checks. The same check runs after rendering and before atomic publication, so a
source/catalog version change during generation aborts the attempt.

Stale/mixed/missing identities raise ExportSnapshotError. The GUI shows the existing
localized recalculation/stale message, not success. The integer compatibility API
uses the same guard. A failed preflight or post-render check preserves the old ZIP.
A caller mutation after capture cannot alter the private snapshot being rendered;
the exported run retains its own accepted inputs and identity.

## Tests / evidence

16 new cases use the public API for changed project/revision, missing/mixed run
identity, wrong feeder ID, malformed recorded snapshot, engine/source/catalog/
registry changes, source changes during rendering, private-copy isolation, and
GUI stale warnings in FA/EN/DE even when its initial check is forced to pass.
Together with prior inventory/atomic cases, 44 targeted cases pass. Version-change
cases inject hash/version changes, not modifications to the packaged database.
Raw logs: `/workspace/audit-evidence/bundle-preflight-*` outside the checkout.

## Remaining risks

This checks recorded input/run identity, not an authenticated signature or a hash
of every calculated output/check value. In-place edits to derived values with the
same identity are not yet detected. The API does not receive the caller's current
in-memory catalog or current raw feeder list; it checks the recorded raw feeder
snapshot and packaged catalog/registry. GUI still separately checks current raw
inputs/catalog selection. No process-wide source/catalog lock eliminates the
post-check/publication race. A private deep copy is not a fully immutable,
API-wide ExportContext, and standalone export APIs remain outside this guard.
Independent reference/reviewer, all-format parity and field acceptance remain
open. P0 stays OPEN; no engineering approval, merge or release is implied.

## Stable checkpoint validation

Full suite: **697 passed, 1 failed, 1 skipped** in 28.17 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New helper/test module Ruff,
compilation and `git diff --check` pass. Global lint/type cleanliness is not
claimed. Actual GUI smoke recalculates four feeders and 71 validation rows.
No database/dependency/user-data change. Based on `6893cf0`; requires previous
audit units. Main stays untouched.
