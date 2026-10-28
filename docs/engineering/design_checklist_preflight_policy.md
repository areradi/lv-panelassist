# Preliminary design checklist publication

## Observed

The separate DesignVerificationExporter.generate_html API accepted a project,
summary and mutable DesignVerificationReport without complete feeder/check context.
A caller could change a checklist status, conclusion, source or claimed reviewer
and publish it under the original calculation. It also wrote the final HTML path
directly, bypassing the guarded primary-report pipeline.

## Expected / implementation

Successful publication now requires feeders=outputs and validations=checks from
the same engine run. The shared accepted-report pipeline captures private state,
checks current input/result identity, stages the HTML, rechecks and publishes
atomically. Missing context or stale run data is rejected before final output.

The supplied checklist is separately deep-copied and compared in full with a
fresh build_design_verification result from that captured run/current locale.
Rows, sources, reviewer/evidence fields, conclusions and order must match. The
internal rendered report is compared again after rendering to reject report
mutation before publication. A caller cannot invent PASS/evidence by editing the
report object. GUI and bundle callers forward the complete context; GUI shows
localized stale/IO messages and does not open/announce a rejected report.

This does not authenticate real evidence: the canonical builder still leaves
unevidenced assembly checks NOT_VERIFIED, preserving definite FAIL conditions.
No external reviewer/evidence-ingestion workflow is added. A checklist built for
a different locale must be regenerated with the current locale.

## API migration

```python
report = build_design_verification(project, outputs, summary, checks)
DesignVerificationExporter.generate_html(path, project, summary, report,
                                        feeders=outputs, validations=checks)
```

Omitting the new context keywords no longer produces a successful export. Private
_render_html remains a rendering primitive, not a supported accepted-run API.
Existing report/contract fixtures now supply their actual engine context; their
13-clause/no-PASS/content assertions remain unchanged.

## Tests / evidence

27 new cases cover stale project/results/checks/missing metadata, invented item or
conclusion PASS, altered evidence/reviewer/source, removed clauses, missing context,
actual preliminary output in FA/EN/DE, renderer IO/mutation, and actual GUI stale/
IO/success behavior in three languages. With the existing result-contract cases,
46 targeted cases pass. No test or prior acceptance assertion was disabled.
Raw logs: `/workspace/audit-evidence/design-preflight-*` outside the checkout.

## Remaining risks

This is software consistency checking, not independent IEC 61439 verification or
authentication of a document/reviewer. Primitive builders, manual file edits,
forged metadata and a renderer changing/restoring intermediate state are outside
the guarantee. A fully immutable ExportContext, content signing, real PDF/Windows/
EPLAN field acceptance and engineering reference/reviewer remain open. The shared
publication policy has no process-wide source lock, power-loss/ACL/network-file-
system guarantee or concurrent-write conflict handling. P0 stays OPEN; no merge
or release is performed.

## Stable checkpoint validation

Full suite: **905 passed, 1 failed, 1 skipped** in 43.84 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. New checklist cases plus
existing result-contract cases: 46 passed. New test-module Ruff, changed exporter
F checks, compilation and `git diff --check` pass. Global lint/type cleanliness
is not claimed. Actual GUI smoke recalculates four feeders and 71 validation rows.
No database/dependency/user-data change. Based on `def914e`; requires earlier
audit units. Main stays untouched.
