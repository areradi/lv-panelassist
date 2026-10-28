# Standalone engineering CSV accepted-run guards

## Observed

Primary reports and bundles checked complete run/result identity, while direct
parts, aggregated parts and control-connection CSV calls could still export stale
projects or altered devices. Their signatures lacked the validation list needed
to verify the complete calculated-result fingerprint.

## Expected / implementation

All three public engineering CSV APIs now accept a validations keyword carrying
the checks returned by the same process_project call. Without it, they raise
ExportSnapshotError before opening an output. There is no implicit reconstruction
or omission of checks. The generic writer remains an unguarded low-level CSV
utility; it is not an accepted engineering-run export API.

The CSV exporters use the same private-copy, pre/post identity/fingerprint guard
and staged publication as the primary reports. The existing machine/spreadsheet
writer still determines text protection and preserves its encoding/column/number
behavior. Mandatory engineering context applies to both modes, including the
legacy default machine mode. GUI actions and ZIP generation now pass the full
check list automatically. GUI displays the existing stale/recalculate warning for
an API rejection, with no success notification.

## Python API migration

Callers must retain all engine results, including checks:

```python
outputs, summary, checks = engine.process_project(project, inputs)
EplanExporter.export_csv(path, project, outputs, summary,
                         validations=checks, mode=CsvMode.MACHINE)
```

The same validations keyword applies to EplanPartsExporter.export_csv and
ControlCircuitGenerator.export_connections_csv. Omitting it is intentionally no
longer a successful export; no legacy bypass is provided. Internal render methods
are not supported substitutes for the public accepted-run APIs.

## Tests / evidence

45 new cases cover all three exporters and both modes for changed project/device/
check list, missing identity, missing context and renderer mutation; actual GUI
calls exercise stale warnings in FA/EN/DE. Together with existing mode/atomic
writer cases, 87 targeted cases pass. Existing CSV fixtures now retain/pass the
actual engine checks; their raw-tag/column/group/quantity assertions remain.
GUI writer-failure fixtures accept the additional context keyword without altering
their failure/preservation assertions. No test is disabled or failure hidden.
Raw outputs: `/workspace/audit-evidence/csv-preflight-*` outside the checkout.

## Remaining risks

Freshness/fingerprint checks are not engineering sign-off or authenticity. Machine
CSV remains unsuitable for spreadsheet opening; spreadsheet CSV changes stored
formula-like tags by design and is not for EPLAN import. Real EPLAN/Excel field
acceptance, process-wide source locks, fully immutable render context, concurrent
write conflict handling and guards for standalone diagrams/macros remain open.
P0 remains OPEN; no independent reference/reviewer approval, merge or release.

## Stable checkpoint validation

Full suite: **778 passed, 1 failed, 1 skipped** in 40.85 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New/adjusted CSV test modules
Ruff, changed output/preflight F checks, compilation and `git diff --check` pass.
Global lint/type cleanliness is not claimed; inherited control-circuit findings
remain. Actual GUI smoke recalculates four feeders and 71 validation rows.
No database/dependency/user-data change. Based on `cf140ae`; requires previous
audit units. Main stays untouched.
