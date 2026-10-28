# CSV publication preserves the previous destination

## Observed

The shared CSV writer opened the destination with mode w before writing rows.
A mid-write exception could truncate a previously valid export. The GUI export
helper had no handling for write failures. Mode validation already happened before
opening and is retained.

## Expected / implementation

Both spreadsheet and machine modes now write to a uniquely named temporary file
in the destination directory. The writer streams rows, flushes and fsyncs the
file, closes it, and uses os.replace for final publication on the same filesystem.
Failures before that point leave an existing destination unchanged. A finally
block removes temporary output on ordinary handled/unhandled exceptions.

The GUI catches OS, encoding and CSV serialization errors for all three CSV
actions. It shows translated disk/permission/file-lock guidance and does not show
a success message. Errors still propagate to API/bundle callers; no silent success
or implicit retry occurs. Export content, encoding, mode defaults and tag handling
are unchanged.

## Tests / evidence

18 new failure-injection/success cases cover both modes at mid-row generation,
encoding, fsync, temporary creation and publication boundaries, old destination
bytes and temporary cleanup. GUI action tests in FA/EN/DE exercise actual failing
writer calls in both modes and verify error messages/no success notification.
Together with the 24 mode cases, 42 targeted tests pass. These are deterministic
boundary simulations, not a real full-disk or Windows file-lock experiment.
Raw logs: `/workspace/audit-evidence/csv-atomic-*` outside the checkout.

## Remaining risks

No cross-platform power-loss guarantee is made: parent-directory fsync, network
filesystem behavior, process termination cleanup, original destination ACL/mode
preservation and concurrent-export conflict detection are not implemented. New
files use temporary-file permissions; concurrent successful writes use last-writer
publication. Temporary cleanup can itself fail under filesystem/permission errors.
XLSX/ZIP and other exports still need their own atomic-publication policy.
Spreadsheet/EPLAN field acceptance, immutable export context and engineering
verification remain open. P0 stays OPEN; no merge or release is performed.

## Stable checkpoint validation

Full suite: **642 passed, 1 failed, 1 skipped** in 28.66 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. Shared writer/new test module
Ruff, compilation and `git diff --check` pass. Only import ordering changed after
the full run. Global lint/type cleanliness is not claimed. Actual GUI smoke
recalculates four feeders and 71 validation rows. No database/dependency/user-data
change. Based on `26f6be6`; requires previous audit units. Main stays untouched.
