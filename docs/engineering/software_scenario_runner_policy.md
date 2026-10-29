# Reproducible synthetic software scenarios

## Run

From the repository root:

```sh
.venv/bin/python scripts/run_regression_scenarios.py
.venv/bin/python scripts/run_regression_scenarios.py --locale fa
```

The default runs ten scenarios in EN/FA/DE (30 runs). The JSON report goes to
stdout; optionally redirect it to a file outside the checkout. Exit 0 means all
software expectations matched; exit 1 means at least one difference/error or
invalid scenario input. Argument errors use argparse's standard exit behavior.
`--scenarios PATH` selects an explicitly reviewed scenario definition file.
Expectations are never regenerated or rewritten automatically.

Definitions: [software_scenarios.json](../audit/software_scenarios.json).
Report fields always identify SYNTHETIC_SOFTWARE_REGRESSION, NOT_VERIFIED and
independent_reference_cases 0. A software PASS never supplies an engineering
reference case, tolerance, reviewer, construction permission or P0 sign-off.

## Scenario scope

| Scenario | Specific policy observation |
| --- | --- |
| missing_network | No bus/transformer input becomes a known fault value; unknown length leaves voltage drop unknown |
| transformer_only | Transformer diagnostic does not invent a panel-bus contribution |
| explicit_bus | Supplied bus input is preserved; supported cable table/known length provide preliminary results |
| bus_with_transformer | Transformer diagnostic does not replace the explicit bus input |
| motor_contribution | Existing preliminary motor contribution increases the explicitly supplied network contribution |
| missing_al_xlpe_table | Missing exact ampacity combination remains unknown |
| single_phase_table_gap | Absent loaded-conductor table cannot be borrowed from the 3P table |
| tt_without_loop | Known bus does not fabricate missing TT loop/PE results |
| it_without_loop | Known bus does not fabricate missing IT loop/PE results |
| long_tncs_feeder | Known 200 m length can produce preliminary voltage drop without invented end/earth-fault results |

Common expectations preserve unknown PE/end-fault values, proposed selections,
unverified assembly conclusion and a consistent engine run identity. Input bus
numbers are explicit input echoes, not independent calculated reference values.
Current numeric outputs are recorded and compared exactly across locales within
one run; they are not automatically accepted as golden engineering answers.
Validation rule/subject/status sequences must also remain identical across locales.
Changing catalog coverage or supported physical models can legitimately change a
policy expectation; that change requires explicit review of these definitions.

Each successful calculation creates actual HTML and XLSX reports through the
public guarded APIs. The runner compares complete ordered validation rows to the
engine: HTML status labels/IDs/subjects/references/descriptions/evidence/actions,
and every XLSX validation-log column. It also checks input/result fingerprints,
preliminary notices, literal multilingual/special-character description text and
numeric XLSX input-power cell type/value. This does not claim every report number
or every export format is covered. PDF, CSV, SVG/DXF and EPLAN remain outside this
runner; their existing tests remain active.

## Failure and provenance behavior

Differences carry field/expected/actual values; locale differences name the first
locale used as their internal comparison. A calculation/export error records its
type/message and fails that run while subsequent cases continue. No failed case
counts as a pass. Language state is restored even on failures. Generated documents
live in temporary directories and are removed on completion/error; the command
does not modify the package database, scenario definitions or project user data.

The runner checks catalog structure first, preserves engine/catalog/registry
identities across calculations and compares the main catalog hash before/after.
JSON includes those identities plus definition/script file hashes for reproduction.
These are traceability checks, not signatures, source authentication or immutable
multi-table transactions. Strict definition checks reject duplicate JSON keys/IDs,
unsupported expectation/input fields, invalid evidence kind/types and bad text.

## Evidence / remaining acceptance

19 new tests include an actual default CLI run from another working directory,
actual nonzero difference output without baseline rewriting, deliberately corrupted
HTML/XLSX, numeric locale drift, export failure/continuation/temp cleanup, source
identity mismatch, malformed definitions and structured error output. Together
with existing fault-scope/engine/metadata cases, 78 targeted tests pass.
Raw evidence: `/workspace/audit-evidence/scenario-runner-*` outside the checkout.

The independent reference pack in [verification matrix](verification_matrix.md)
is still blocked on actual reviewed sources, expected values, applicability and
approved tolerances. No synthetic case contributes to that acceptance count.
Physical network/ADS/thermal/coordination validation, remaining format coverage,
immutable contexts and independent electrical review remain open. P0 remains OPEN.
No dependency, engine formula, GUI flow, merge or release changes are introduced.

## Stable checkpoint validation

Actual standalone runner: **30 PASS** (10 scenarios x 3 locales), NOT_VERIFIED,
zero independent references, unchanged catalog. Its JSON is saved externally as
`/workspace/audit-evidence/scenario-runner-all.json`. Full suite: **1472 passed,
1 failed, 1 skipped** in 75.73 s. The inherited PDF roundtrip failure and Windows
compiler skip remain. Runner/new-test Ruff, compilation and diff checks pass;
global lint/types are not claimed clean. Actual GUI smoke recalculates four feeders
and 71 validation rows. Packaged DB SHA256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
Based on `dd12962`; prior audit units required. Main remains untouched.
