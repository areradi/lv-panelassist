# Accepted-run EPLAN script and library publication

## Observed

Standalone C# script, EMA/EMP libraries and field-test kit APIs lacked complete
run context. Library exports wrote files directly into an existing directory,
including potentially user-edited macros and completed acceptance checklists.

## Expected / implementation

All four publication APIs now require validations=checks from the same engine run.
Missing context/stale inputs/changed results raise ExportSnapshotError. The C#
file uses private copied state and the shared pre/post accepted-report guard and
atomic file publication, preserving its UTF-8 BOM and CRLF encoding.

Libraries and field kits render into a private sibling staging directory, validate
the returned flat file list and nonempty files, fsync, recheck the captured run,
then rename the completed directory into place. Existing nonempty destinations
(or existing files at that path) are refused without modification; choose a new
parent in the GUI. Existing empty directories are accepted, removed only just
before publication, and restored empty if rename fails. No merging/deleting of
old macro sets or user-edited checklists is attempted. Unlisted, duplicate, empty
or out-of-staging outputs are refused.

GUI and ZIP callers forward checks. GUI library actions show localized stale,
occupied-destination and IO guidance, with no success on failure. The C# action
uses the shared save-only file action. The ZIP still receives the same asset
names/counts. Primitive script/XML builders and checklist validation remain
rendering/field-test helpers, not accepted engineering-run publication APIs.

## API migration

Pass validations=checks to EplanMacroExporter.export_file,
EplanMacroFileExporter.export_library, EplanPageMacroExporter.export_library and
EplanFieldTestKit.export_kit. EMP's optional ts argument remains supported. Library
folders must be absent or empty; a nonempty folder is never silently overwritten.
Existing test fixtures now retain actual checks from the same run; their XML,
macro-name, script encoding, quantity, checklist and compiler assertions remain.

## Tests / evidence

37 new cases cover stale/changed/missing-context data in four APIs, preservation
of existing user data, occupied library rejection after a successful real export,
renderer IO/mutation, failed directory publication restoring an empty directory,
and localized GUI occupied-folder guidance in FA/EN/DE. Together with the adjusted
absent-motor regression, 38 targeted cases pass. Existing file-structure tests
continue to exercise actual outputs, not just helper presence.
Raw logs: `/workspace/audit-evidence/eplan-preflight-*` outside the checkout.

## Remaining risks

This is not EPLAN execution/import acceptance or engineering approval. No source
lock, fully immutable renderer, authenticated metadata, directory-fsync/power-loss
or network-filesystem guarantee is supplied. Concurrent destination creation can
cause publication to fail; no conflict merge is attempted. Empty directory mode/
ACL metadata is not preserved, and recovery mkdir/temporary cleanup can fail under
OS errors. Parent directories newly created for a requested path may remain on
failure. Separate design-verification HTML and primitive builders still require
explicit scope treatment. Independent references/reviewer and Windows/EPLAN field
acceptance remain open. P0 stays OPEN; no merge or release is performed.

## Stable checkpoint validation

Full suite: **878 passed, 1 failed, 1 skipped** in 42.52 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New EPLAN cases plus the
adjusted absent-motor regression: 38 passed. New library helper/test module Ruff,
compilation and `git diff --check` pass. Global lint/type cleanliness is not
claimed. Actual GUI smoke recalculates four feeders and 71 validation rows.
No database/dependency/user-data change. Based on `b2f08fc`; requires previous
audit units. Main stays untouched.
