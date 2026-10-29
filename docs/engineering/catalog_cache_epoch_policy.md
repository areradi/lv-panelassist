# Content-hash epochs for cached catalog tables

## Observed

Only devices access checked the database hash and invalidated auxiliary caches.
Reading cached curves, rules, standards or PE sections after an external file edit
could therefore return old data until devices happened to be read. A main-file
hash also could not identify committed data still held in a SQLite WAL sidecar.

## Expected / implementation

All five cached accessors now share one catalog file-hash epoch. Each checks the
file before and after its read/load. A changed hash invalidates all rowsets,
including the currently unused ampacity-cache slot. New values are cached only
after the post-read hash matches. A load/hash failure clears the epoch/caches and
propagates; it never serves the previous good rowset as a fallback. Device loading
is no longer required to refresh auxiliary data.

The shared catalog_file_hash rejects nonempty -wal/-journal sidecars, because the
main bytes alone cannot identify those data. It reports a localized requirement
for a closed consistent snapshot; it does not checkpoint, remove or repair files.
This is conservative, including nonempty inactive persistent journal files. Empty
sidecars are allowed. Existing engines continue to reject changed catalog hashes;
a new engine can use the refreshed data and record the new identity.

## Tests / evidence

19 new cases use copied databases for actual data changes in devices, curves,
rules, standards and PE sections; invalidation triggered independently by each
accessor; malformed reload without fallback and restoration; change during load;
nonempty sidecars with FA/EN/DE errors and no repair; and an old-engine rejection /
new-engine calculation whose metadata and explicit curve lookup use the new file.
Together with curve gate/lookup tests, 125 targeted cases pass. Sidecar cases are
synthetic indicators, not a live SQLite recovery/checkpoint experiment.
Raw logs: `/workspace/audit-evidence/cache-epoch-*` outside the checkout.

## Remaining risks

Hash checks do not lock the database or create an immutable read transaction across
all accesses. Rapid replace/restore races, changes after the last check, network
filesystems and current callers retaining previously returned references are not
eliminated. Rowsets remain mutable; existing structural gates still apply. This
is cache versioning, not full auxiliary-table validation, data authenticity or
independent numerical approval. The app must use a stable closed catalog snapshot;
no automatic recovery/migration is performed. P0 stays OPEN; no merge/release.

## Stable checkpoint validation

Full suite: **1090 passed, 1 failed, 1 skipped** in 40.09 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New test module Ruff, changed
catalog/metadata F checks, compilation and `git diff --check` pass. Global lint/type
cleanliness is not claimed. Actual GUI smoke recalculates four feeders and
71 validation rows. Packaged DB SHA-256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependency or user-data change. Based on `a3f74cc`; requires earlier audit units.
Main stays untouched.
