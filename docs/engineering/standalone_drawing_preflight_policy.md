# Accepted-run drawing file exports

## Observed

SLD/TCC/control SVG, layout SVG and control DXF file APIs wrote directly to their
destinations using mutable project/results without complete validation context.
They could bypass the accepted-run/result-fingerprint checks used by reports and
bundles, and failure could truncate an older drawing.

## Expected / implementation

All five file APIs now require validations=checks from the same process_project
call for successful export. Missing context raises ExportSnapshotError before
opening output. The shared text-export adapter uses the accepted-report pipeline:
private copied state, pre/post identity/fingerprint checks, same-directory staging,
fsync/close and atomic replacement. Original SVG UTF-8 and DXF ASCII/replace
encoding are retained.

GUI drawing actions share target selection, full-context forwarding, localized
stale/IO failure messages and no open/success on rejection. SVG opens only after
successful publication; DXF retains its existing save-only behavior. Bundle file
generators now forward the checks too. No drawing geometry or calculations change.

Python callers must retain the engine checks and pass validations=checks to
SldGenerator.generate_svg_file, TccGenerator.generate_svg_file,
ControlCircuitGenerator.generate_svg_file, PanelLayoutGenerator.generate_svg_file
and ControlLadderDxfExporter.export_file. Calling them without it no longer
succeeds. String-returning generate_svg/generate functions remain rendering
primitives for internal composition/tests, not accepted-run publication APIs.

## Tests / evidence

63 new cases cover all five file types for changed project/payload/check list,
missing identity/context, successful XML or ASCII-DXF/EOF output, renderer IO error,
renderer mutation and GUI stale behavior in FA/EN/DE. Three of these GUI IO cases
verify localized errors/no browser/no success. Five successful GUI cases verify
actual full-context forwarding and SVG-open/DXF-save-only behavior. The new cases plus an existing cap
SLD regression pass together (64 cases).

Existing file fixtures now retain checks. The capacitor SLD fixture previously
mixed outputs and summary from two runs of the same inputs; it now uses one actual
run without changing its cap-branch/content assertions. Existing raw SVG/DXF
rendering tests stay intact; no test is disabled or asset assertion removed.
Raw evidence: `/workspace/audit-evidence/drawing-preflight-*` outside the checkout.

## Remaining risks

XML parsing and DXF structure/ASCII tests do not prove CAD/EPLAN import, geometry,
physical wiring or engineering validity. Macro/script/library/field-kit and the
separate design-verification HTML APIs still need accepted-context treatment.
String renderers are not guards and must not be substituted for public publication
APIs. No signature, source lock, fully immutable renderer state, intermediate
mutation detection or Windows filesystem/power-loss guarantee is provided.
Independent engineering reference/reviewer and real field tests remain open.
P0 stays OPEN; no merge or release is performed.

## Stable checkpoint validation

Full suite: **841 passed, 1 failed, 1 skipped** in 41.32 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New drawing cases plus the
adjusted cap SLD case: 64 passed. Shared helper/new test module Ruff, changed
output-module F checks, compilation and `git diff --check` pass. Global lint/type
cleanliness is not claimed; inherited layout/control/DXF debt remains. Actual GUI
smoke recalculates four feeders and 71 validation rows. No database/dependency/
user-data change. Based on `8e0fae3`; requires earlier audit units. Main untouched.
