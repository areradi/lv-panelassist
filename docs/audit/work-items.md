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

## Review unit 2 — PE/fault integration and missing cable data

- **Observed:** process_project substituted 10 kA, 25 m and 20 ms; PE used half
  the bus three-phase current. Detailed trip/PE/network helpers were not used
  to produce the actual feeder result. Unsupported ampacity combinations fell
  back to a Cu/PVC/C table. GUI hid missing-data counts.
- **Expected:** no assumed L-PE result or verification, no clipped known trip
  times, no numeric voltage drop for unknown length, and consistent proposed BOM.
- **Implementation:** actual feeder path now carries typed TripTimeEstimate,
  ShortCircuitProfile and CheckResult. Since the current project schema has no
  validated earthing-specific return path/settings, PE and L-PE results are None
  with INSUFFICIENT_DATA. The standalone curve estimator preserves known times
  including 8 s and labels instantaneous 20 ms as an estimate. Removed audit
  flags and the unused incompatible selectivity wrapper. Exact cable table
  combinations only; missing Iz remains None. GUI severity sort/four counters,
  HTML/XLSX preliminary notices, explicit proposed procurement lines, and SLD
  bridge preserve unknowns and operating-voltage Icu instead of a 400 V fallback.
- **Tests:** new integrated earthing x locale matrix, trip boundaries
  0.02/4.9/5/8/None/NaN/Inf, missing curve, and Cu/PVC/C vs missing
  Al/XLPE/E, B1 and 1P tables. Existing tests for the removed unsafe assumptions
  are replaced by explicit unknown/estimate expectations, not skipped.
- **Evidence:** `tests/test_p0_engine_path.py`; `pytest-pe.txt`; GUI smoke output.
- **Remaining risks:** no validated L-PE/ADS calculation is implemented. Diagnostic
  3P network estimates still require source/material/temperature modelling and
  engineer review. Unsupported ampacity uses a clearly marked geometry proposal,
  not a validated selected cable. k=143 in the standalone helper is inherited,
  unreviewed and never used to verify a feeder without loop data. Other legacy
  protection, thermal, busbar and property-provenance work remains open.

## Review unit 3 — Evidence, settings, IP and run traceability

- **Observed:** legacy quality labels and series/range selectivity rules could
  imply verification without an exact reviewed source. Adjustable breakers did
  not require actual settings. IP was compared as one integer; run identity and
  external catalog changes were not tracked consistently.
- **Expected:** unknown evidence remains preliminary; only exact applicable
  device rules may be considered, real settings are checked, and stale results
  can be distinguished from the current input/catalog/engine snapshot.
- **Implementation:** property provenance (document/revision/page/reviewer/date/
  applicability), evidence-gated quality, exact-voltage Icu, exact-pair/voltage/
  settings/reviewer selectivity matching, Ir/I2/range checks, and separate IP
  dimensions. A ratio alone neither proves nor disproves selectivity. Type 2
  coordination remains INSUFFICIENT_DATA without a tested combination. All
  undocumented legacy successes are WARNING, not COMPLETED. Input models reject
  unsupported 2P, blank IDs, duplicates/empty feeder sets and mutated invalid
  values. Packaged catalog connections are read-only. No database bytes changed.
  Added immutable run metadata with canonical input snapshot/fingerprint,
  UTC timestamp, project revision, engine/source hash, actual catalog selection
  hash, catalog file hash and registry hash. HTML/XLSX carry this metadata;
  long XLSX snapshots are split rather than silently truncated. GUI exports check
  input/catalog/source freshness. TCC SVG has an explicit preliminary watermark.
- **Tests:** synthetic policy and evidence-matching cases; integrated settings
  check; exact-voltage/IP comparisons; metadata immutability, cross-report
  fingerprints, changed input/catalog/version, read-only DB, and long snapshot.
  Rendering fixtures explicitly identify themselves as synthetic; none is an
  independently approved engineering reference. No original test was skipped to
  hide a regression; unsafe expected statuses were corrected explicitly.
- **Evidence:** final logs/screenshot under `evidence/`; see
  [final validation](final-validation.md) and
  [engineering verification matrix](../engineering/verification_matrix.md).
- **Remaining risks:** P0 is OPEN. The user confirmed that independent sources
  and reviewer are unavailable, so no sensitive result is certified. There is
  no fully migrated property catalog, validated L-PE/ADS solver, Ics/backup
  coordination, or independent numerical reference pack. API-wide immutable
  ExportContext, all-format manifest parity and project persistence remain for
  subsequent gated work. GUI freshness does not replace that future API contract.
  Existing thermal/busbar formula applicability remains unreviewed and their
  legacy checks are now explicitly warnings. Global lint/type debt, PDF printing,
  Windows/DPI/RTL acceptance, EPLAN 2024 import and human trials remain open.
