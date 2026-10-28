# Audit work register

Statuses refer to software delivery, never engineering certification. Every item
uses Observed / Expected / Implementation / Tests / Evidence / Remaining risks.

## S0 — Baseline

- **Observed:** clean checkout exactly at the requested SHA; 274 tests collected.
- **Expected:** preserve data and capture actual commands before changes.
- **Implementation:** dedicated branch, external source/Git backups, baseline report.
- **Tests:** 272 passed / 1 failed / 1 skipped; lint/type failures recorded.
- **Evidence:** [baseline](baseline.md), raw output and GUI screenshot.
- **Remaining risks:** browser printing, Windows/EPLAN and independent review absent.

## P0 — Technical gate (OPEN)

- **Observed:** detailed verification helpers exist outside the real calculation
  path; hidden PE assumptions, legacy clipping flag, and unsupported verification
  claims need investigation. See baseline source at the requested commit.
- **Expected:** no unknown or approximate input produces an unqualified pass;
  one result/status/provenance contract reaches the engine, UI and exports.
- **Implementation:** delivered changes must be listed individually below.
- **Tests:** require integrated `ProjectSpec -> process_project -> outputs` checks,
  not helper tests alone; preserve unaffected baseline coverage.
- **Evidence:** changes and command output will accompany each local review unit.
- **Remaining risks:** independent reference formulas/tolerances, exact manufacturer
  documents/settings, and a named electrical reviewer must be supplied and signed
  off before this gate closes. Do not invent references or tolerances.

## P1 / P2 / P3 — Deferred by P0 gate

- **Observed:** requested scope includes imports, project persistence, unified UI,
  packaging, procurement, EPLAN field tests, human trials and licensing research.
- **Expected:** develop these after P0 acceptance, preserving FA/EN/DE.
- **Implementation:** not started; no paywall, beta release, or compatibility claim.
- **Tests:** Windows clean install, EPLAN 2024, 3 locales/DPI/themes, and participant
  studies require their actual target environments and consenting participants.
- **Evidence:** none; no completion claimed.
- **Remaining risks:** technical gate open; hardware/software and human review are
  unavailable in this Linux task. Sprint labels are not delivery-time commitments.

## Review unit 1 — Result contract and unevidenced design verification

- **Observed:** two status enums, WARNING taking precedence over missing data in
  the design checklist, duplicate exporter classes, and demo claims of passed
  physical checks without test documents.
- **Expected:** shared severity, complete check field names, and no assembly PASS
  inferred from calculated recommendations or device-level quality labels.
- **Implementation:** one status enum and mapping; backward-compatible structured
  ValidationResult fields; CheckResult adapter; unknown catalog records default to
  ESTIMATED. The preliminary checklist includes separate physical PE continuity
  evidence (13 rows), retains failures, and marks absent assembly evidence
  NOT_VERIFIED. Removed the shadowed duplicate exporter. FA/EN/DE retained.
- **Tests:** 16 status combinations, actual demo-to-checklist/export integration,
  unknown-device default, and existing design checklist regression tests. Existing
  assertions that expected an unevidenced PASS now require NOT_VERIFIED; locale
  tests compare exact key sets instead of a hardcoded key count.
- **Evidence:** `tests/test_result_contract.py`, `pytest-contracts.txt`. New modules
  pass Ruff. No catalog/DB modification.
- **Remaining risks:** legacy checks explicitly retain method LEGACY_UNDOCUMENTED
  and missing structured numeric/source fields; this is visibility, not a claim
  that every legacy calculation is migrated. No physical evidence ingestion or
  engineer sign-off workflow yet. This unit does not close the P0 gate.
