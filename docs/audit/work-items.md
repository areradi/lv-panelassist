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

## Review unit 4 — Transformer/bus/end fault scopes

- **Observed:** transformer-only input still supplied a numerical panel-bus fault
  value; diagnostic R/X/copper/earth-loop defaults generated end-fault values.
- **Expected:** missing installation-location data cannot become a device
  comparison current or a calculated earth-fault result.
- **Implementation:** one explicitly unreviewed transformer diagnostic, separate
  panel and feeder scopes, explicit bus input required, unknown end-fault values,
  and structured scope checks in the actual GUI/HTML/XLSX validation stream.
  Source input guidance updated in all three languages. No catalog data changed.
- **Tests:** real engine/locale/output tests plus updated regressions for unsafe
  old assumptions; actual GUI log exercise. See `*network*` evidence files.
- **Evidence:** [fault scope policy](../engineering/fault_scope_policy.md).
- **Remaining risks:** physical network/loop solver, independent references and
  reviewer remain unavailable; motor/source topology remains preliminary.

## Review unit 5 — Real Ir vs frame rating

- **Observed:** 100 A frame / 50 A setting / 57 A Iz returned both WARNING and
  ERROR because the legacy cable rule still compared the frame to ampacity.
- **Expected:** one actual-setting verdict; missing data cannot pass and cannot
  hide a known inequality violation.
- **Implementation:** reuse CheckResult for both cable rules; validate stated
  range/fixed-device settings, preserve unknown bounds/device, show actual A
  values and use supplied Ir for geometry proposals. Unknown settings use an
  explicitly preliminary frame-based proposal only. No catalog mutation.
- **Tests:** synthetic integrated inequalities/ranges, unknown device/data,
  geometry, fixed device, invalid settings, and HTML/XLSX consistency.
- **Evidence:** [setting policy](../engineering/protection_setting_policy.md) and
  `*settings*` validation outputs.
- **Remaining risks:** manufacturer data/applicability and actual installed
  device/settings require engineering evidence. P0 remains open.

## Review unit 6 — Catalog input gates

- **Observed:** invalid numbers, identities and mutable catalog data could enter
  selection; SQL/JSON mismatches and conflicting rules were not rejected.
- **Expected:** reject malformed structural data before project output without
  modifying or auto-repairing the packaged database.
- **Implementation:** shared device/rule validation, engine snapshot revalidation,
  missing-file recovery error, strict Icu numeric lookup and read-only CLI.
- **Tests:** invalid numeric/identity/schema/mutation cases, actual project path,
  conflicting rule limits and actual CLI exit/status/unchanged file bytes.
- **Evidence:** [catalog policy](../engineering/catalog_input_policy.md) and
  `*catalog*` validation files; 450 passed, inherited PDF failure/Windows skip.
- **Remaining risks:** structural validity is not source correctness or engineering
  verification; full catalog schema/migration and independent references remain open.

## Review unit 7 — Bind property proof to actual values and conditions

- **Observed:** complete-looking source metadata could apply to the wrong value,
  unit, device or operating conditions, and group labels could promote a device.
- **Expected:** explicit subject/scope matching before treating a property as
  evidenced; no whole-device production approval inferred from metadata alone.
- **Implementation:** exact value/unit/applicability matcher; dated metadata
  checks; actual Icu and selectivity integration; source reference in reports;
  no favorable choice between overlapping proofs; aggregate/legacy labels remain
  unverified. Original catalog bytes remain unchanged.
- **Tests:** synthetic positive/negative scope cases, actual engine/report checks,
  overlapping rules, SQL invalid capacity and bibliography-only approval rejection.
- **Evidence:** [property policy](../engineering/property_evidence_policy.md) and
  `*evidence*` validation logs; 491 passed, inherited PDF failure and Windows skip.
- **Remaining risks:** record matching cannot authenticate document/reviewer;
  actual independent sources, approval workflow and P0 physical verification remain open.

## Review unit 8 — Separate busbar current and fault verdicts

- **Observed:** exhausted fault candidates caused an adequate current rating to
  be reported as an overload, including in actual engine reports.
- **Expected:** current adequacy and Icw/Ipk failures have independent verdicts.
- **Implementation:** candidate-selection flag describes current capacity only;
  known fault failures and missing-data statuses remain explicit.
- **Tests:** 12 synthetic current/fault boundary and integrated FA/EN/DE report
  cases, including unchanged true overload errors. No independent reference claim.
- **Evidence:** [busbar verdict policy](../engineering/busbar_verdict_policy.md).
- **Remaining risks:** physical busbar modelling, constants and manufacturer
  applicability remain unreviewed; P0 stays OPEN.

## Review unit 9 — Component IP upper bounds

- **Observed:** installed-fan path fabricated IP54 independently of fan data;
  natural ventilation copied the target without checking the proposed body.
- **Expected:** component declarations only bound a proposal; unknown ratings
  and unsupported water applicability cannot produce an effective assembly IP.
- **Implementation:** actual body/fan/target dimension ceiling, explicit missing
  status, unverified labels and installation guidance in FA/EN/DE and reports.
- **Tests:** synthetic dimensions, fan/body missing data, natural ventilation,
  special water categories and actual engine -> HTML/XLSX in three languages.
- **Evidence:** [IP upper-bound policy](../engineering/enclosure_ip_bound_policy.md).
- **Remaining risks:** assembly verification and independent source/reviewer
  unavailable; P0 remains OPEN.

## Review unit 10 — IP catalog applicability and missing fallback rating

- **Observed:** special water classes were treated as ordinal compatibility;
  hypothetical EST-PANEL inherited an unsupported generic IP20 declaration.
- **Expected:** unsupported applicability and absent enclosure data stay unknown.
- **Implementation:** conservative catalog comparison for water categories 0–6;
  explicit missing IP on EST-PANEL. Supported dimensions retain existing behavior.
- **Tests:** 24 synthetic comparison/repository/engine/FA/EN/DE report cases.
- **Evidence:** [catalog IP policy](../engineering/ip_catalog_applicability_policy.md).
- **Remaining risks:** manufacturer evidence and assembly verification absent;
  special water/combined markings need separate review. P0 stays OPEN.

## Review unit 11 — Enclosure selection uses the run catalog

- **Observed:** body selection bypassed the validated run catalog/manufacturer
  filter via the global repository; downstream BOM and geometry inherited it.
- **Expected:** an enclosure is in the recorded selection catalog or is an
  explicitly hypothetical EST-PANEL with missing IP data.
- **Implementation:** body candidates use the validated, filtered run catalog
  and the shared conservative IP comparison.
- **Tests:** eight new catalog/body/BOM/report/hash/repeated-run cases; previous
  ceiling fixtures now supply real catalog inputs without changing assertions.
- **Evidence:** [scope policy](../engineering/enclosure_catalog_scope_policy.md).
- **Remaining risks:** auxiliary repository data and all-format immutable export
  context remain open; no engineering approval and P0 stays OPEN.

## Review unit 12 — PDF integrity and specific failure messages

- **Observed:** old destination could imply false success; fixed browser/HTML
  paths mixed attempts; all GUI failures incorrectly claimed a missing browser.
- **Expected:** only this attempt's output is published; old file survives failure;
  user sees a meaningful, localized failure reason.
- **Implementation:** isolated temporary output/profile and GUI HTML, basic PDF
  marker guard, atomic publication, structured result plus compatible bool API.
- **Tests:** 15 synthetic browser/GUI-action tests; actual minimal Chromium print
  timed out independently of the engineering report.
- **Evidence:** [PDF integrity policy](../engineering/pdf_export_integrity_policy.md).
- **Remaining risks:** real PDF rendering and Windows/RTL acceptance unresolved;
  the existing PDF roundtrip test stays enabled. P0 remains OPEN.

## Review unit 13 — Literal XLSX report text

- **Observed:** a cable BOM row bypassed text handling; other rows changed stored
  engineering tags with apostrophe prefixes.
- **Expected:** all report text stays literal, numbers stay numeric, no formula
  cell is generated from user input or engineering tags.
- **Implementation:** shared writer explicitly sets string cell types; cable row
  uses it. Existing regression asserts original values plus persisted text type.
- **Tests:** 23 engine/report/reopen/XML and direct-boundary cases in FA/EN/DE.
- **Evidence:** [XLSX text policy](../engineering/xlsx_literal_text_policy.md).
- **Remaining risks:** CSV machine-import vs spreadsheet-safe mode remains open;
  no Excel field acceptance or engineering sign-off. P0 remains OPEN.

## Review unit 14 — Explicit CSV export destinations

- **Observed:** raw CSV fields can become spreadsheet formulas; automatic escaping
  would change EPLAN tags and break the literal interchange contract.
- **Expected:** user/API explicitly distinguish protected spreadsheet viewing
  from unchanged machine interchange, with no silent tag conversion.
- **Implementation:** shared two-mode writer in all three CSV exporters, GUI
  destination/cancel choice and localized guidance, machine-CSV note in ZIP.
- **Tests:** 24 mode/writer/actual-export/GUI cases; bundle expectations retain all
  existing files plus the new explanatory note.
- **Evidence:** [CSV mode policy](../engineering/csv_export_mode_policy.md).
- **Remaining risks:** real spreadsheet/EPLAN field acceptance and atomic CSV
  writes remain open; P0 engineering gate remains OPEN.

## Review unit 15 — Atomic CSV publication and visible write errors

- **Observed:** direct CSV writing could truncate an old export on mid-write
  failure; GUI did not handle OS/encoding/serialization errors.
- **Expected:** old destination survives failed attempts; no GUI success on error.
- **Implementation:** same-directory temporary file, flush/fsync/close, atomic
  replace and cleanup; localized GUI error handling for all three CSV actions.
- **Tests:** 18 new boundary/GUI cases plus 24 existing mode cases, both modes.
- **Evidence:** [CSV publication policy](../engineering/csv_atomic_write_policy.md).
- **Remaining risks:** power loss, network filesystems, concurrent write conflicts,
  other formats and Windows field acceptance remain open; P0 stays OPEN.

## Review unit 16 — Main XLSX report publication

- **Observed:** direct workbook saving could truncate a prior report; GUI did not
  handle file-write failure.
- **Expected:** failed attempts preserve an old report or leave no new file;
  GUI reports failure, not success.
- **Implementation:** private same-directory temporary file, ZIP validation,
  flush/fsync/close, atomic replacement and cleanup; localized GUI errors.
- **Tests:** 11 new actual export/GUI boundary cases plus 23 literal-text cases.
- **Evidence:** [XLSX publication policy](../engineering/xlsx_atomic_write_policy.md).
- **Remaining risks:** Windows field tests, other formats and power-loss/concurrent
  write behavior remain open; P0 remains OPEN.

## Review unit 17 — Atomic document-bundle publication

- **Observed:** opening the target ZIP before generating assets could destroy an
  old bundle when an early/late generator or ZIP finalization failed.
- **Expected:** failed attempts preserve the old archive or leave no new file;
  success requires a closed, structurally intact, count-consistent archive.
- **Implementation:** private same-directory staging, ZIP/count checks, fsync,
  atomic replacement/cleanup; localized OS/invalid-ZIP GUI errors.
- **Tests:** 13 actual generation/publication/archive/GUI boundary cases; existing
  demo asset checks and optional-PDF behavior remain unchanged.
- **Evidence:** [bundle publication policy](../engineering/bundle_atomic_write_policy.md).
- **Remaining risks:** omitted-format manifest, PDF printing, all-format parity,
  Windows field tests and engineering verification remain open. P0 stays OPEN.
