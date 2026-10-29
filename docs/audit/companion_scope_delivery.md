# Companion-product scope delivery

Base: `363ff45`, branch `feat/companion-design-scope`. The checkout started clean.
The user's current product direction authorizes retiring low-quality macro/CAD
generation and replacing numeric connection lists with functional relationships.
The user then explicitly chose a block architecture view in place of physical
panel-layout output. Other output removal decisions remain pending.

## Observed / expected

The UI/bundle exposed EMA/EMP/C# generators, DXF and macro field-test kits.
Connection schedules invented wire/pin/color/section details. The panel image
presented device placement and fabrication-style dimensions. These conflicted
with the requested companion role beside EPLAN/AutoCAD.

Expected: remove the retired generation paths; offer one equipment-level
connection model across UI/CSV/reports; replace only the approved layout output
with conceptual blocks, preserving calculations and the remaining output choices.

## Implementation

- Removed the four active macro/script/field-test/DXF modules, their GUI actions,
  buttons and ZIP entries. No generated/user/recovery files were deleted.
- Introduced immutable functional connection rows with explicit panel/feeder
  scopes, power/control/signal/protection relationships and actual proposed part
  references. Unknown controller/part/interface details stay unspecified.
- The same rows drive the visible GUI table, CSV, XLSX and HTML/PDF section.
  The compatibility CSV method delegates to the functional export. Existing
  snapshot/freshness/injection/atomic-write guards remain active.
- The approved architecture view reuses those relationships as power/group
  blocks. It shows selected part references and separates surge protection from
  the main path. It has no manufacturing scale, dimensions, rail/duct/gland or
  physical placement output. Internal preliminary space/capacity calculations
  remain unchanged.
- Persian SVG labels are shaped for consistent rendering while retaining the
  complete original text in accessible labels. The preliminary status/run notice
  sits above the blocks. Actual sample rendering exposed and corrected detached
  letters, combining-mark dotted circles and the central watermark obstruction.
- Found and fixed a retained IEC preview bridge's hidden 25 kA fallback and
  main-breaker 400 V Icu reuse. Missing bus/rating data stays unknown at the correct
  project voltage; no electrical formula/reference value was introduced.

## Tests / evidence

Retired-feature test classes/cases were removed with their generators. Library
publication guards were retargeted from EPLAN macros to the retained IEC SVG
library; CSV guards now test functional connections. Tests for retained physical
estimates/calculations remain. New tests explicitly require retired modules and
GUI actions to be absent and prohibit retired assets in actual ZIPs.

37 new cases cover load types, locale/export row parity, literal XML/CSV text,
visible functional UI rows, architecture groups without execution dimensions,
panel/feeder scope collisions, Persian typography and missing-data preview scope.
The older bundle fixture was corrected after a broad sheet-name replacement
accidentally renamed its expected retained control-SVG asset. The unchanged
control drawing is still required, and the absence checks remain explicit.

| Executed check | Actual result |
| --- | --- |
| `.venv/bin/python -m pytest -q --tb=short` | **1833 passed** in 154.31 s; no failures or skips. |
| Focused new-scope/bundle tests | 38 passed before the final optional-mark display adjustment; all final cases also executed in the full suite. |
| `scripts/run_regression_scenarios.py` | All 30 runs PASS: ten synthetic scenarios × EN/FA/DE. Engineering NOT_VERIFIED, zero independent reference cases. |
| `DISPLAY=:133 .venv/bin/python scripts/gui_smoke.py` with isolated Xvfb | Actual GUI rendered/recalculated four feeders and 71 validation rows; additionally checks that all functional connection rows are populated in the GUI table. |
| New module/test Ruff and changed legacy-file F checks | Passed. No global lint/type-clean claim. |
| Compileall, dependency check and `git diff --check` | Passed. |
| Actual sample handoff | Demo yields 25 functional relationships and a 13-file no-PDF ZIP without any retired assets. Final Persian architecture SVG was rendered to PDF/PNG and visually inspected after typography/notice corrections. |

The suite count changes intentionally: 79 retired-feature cases, including the
Windows-only C# compiler check, were removed or replaced; 37 new scope cases were
added. Coverage for retained calculations, current-run/export failures and
publication integrity remains active. An earlier running suite was invalidated
by the SVG typography source update; only the final stable-source run above is
used as checkpoint evidence.

Raw evidence uses `/workspace/audit-evidence/companion-*`; samples are in
`companion-samples/`. The packaged database remains byte-identical, SHA256
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
The sample CSV intended for spreadsheet review uses spreadsheet-safe mode.

## Remaining risks / product decisions

The [product decision record](../product/direction.md) lists the retained outputs
for individual discussion. Detailed control/SLD SVGs are still preliminary and
have not been approved as final product outputs. The functional list does not
implement terminal assignment, PE/ADS, safety-circuit engineering or verified
manufacturer control interfaces. Those require reviewed inputs and detailed
design in the target tool. No EPLAN/AutoCAD import or construction approval is
claimed. P0's independent engineering/data blocks remain open; obsolete macro
acceptance work is retired by the current user direction.
