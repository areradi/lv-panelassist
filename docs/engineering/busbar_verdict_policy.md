# Busbar current and fault verdicts

## Observed

A synthetic 100 A design / 1000 kA fault case exhausted the fault-withstand
candidates. The selected fallback was rated 1464 A, yet RULE-BUS-024 reported
an overload error. One selection flag was used for both continuous-current
capacity and fault withstand. The same false error reached actual reports.

## Expected and implementation

The selection flag now describes only the selected candidate's continuous-current
capacity. When all current-rated candidates fail Icw/Ipk, the existing fallback
is retained and the separate RULE-BUS-025/026 errors remain. When no candidate
meets current demand, RULE-BUS-024 still reports ERROR. Missing fault data still
produces INSUFFICIENT_DATA for RULE-BUS-025/026/027. Existing legacy successes
remain WARNING, never engineering approval.

## Tests and evidence

`tests/test_busbar_verdicts.py` exercises current below/at/above catalog capacity,
known small/excessive and missing faults, and actual process_project -> HTML/XLSX
in FA/EN/DE. These deliberately extreme synthetic cases test verdict separation,
not independently approved numerical references. Before the fix: 5 failed,
7 passed. After: 12 passed. Raw logs are outside the checkout under
`/workspace/audit-evidence/busbar-*`.

## Remaining risks

No change to current tables, copper constants, peak factors, withstand formulas,
geometry, support limits or physical verification. Those assumptions still need
independent sources, applicability review and an electrical reviewer. The largest
fallback remains a preliminary proposal with explicit fault errors; it is not a
valid assembly selection. P0 stays OPEN. No merge or release is implied.

## Validation at this checkpoint

- Full suite: **503 passed, 1 failed, 1 skipped** in 24.92 s. The inherited failure
  remains `TestPhase3Pdf::test_html_to_pdf_roundtrip`; the skip remains the Windows
  compiler case. No test disabled or existing expected result changed.
- The 12 new cases passed again after strengthening XLSX status assertions.
- Real GUI startup/recalculation: four feeders, 70 validation results.
- New test module passes Ruff; busbar.py retains the same 18 pre-existing Ruff
  findings as its parent version. Global lint/type cleanliness is not claimed.
- `git diff --check` passes. No database, dependency, user data or main-branch
  changes. This branch is based on `e70207c` and requires the earlier audit units.
