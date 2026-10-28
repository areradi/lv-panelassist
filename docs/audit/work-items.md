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
