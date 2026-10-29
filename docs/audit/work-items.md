# Audit work register

Current output/product scope follows the user's
[companion-product decisions](../product/direction.md). Macro/DXF generation and
physical layout drawing are retired or replaced as recorded there; historical
audit units below describe their earlier state. Engineering evidence gates remain.

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

## Review unit 18 — Bundle inventory and explicit PDF outcomes

- **Observed:** requested but failed PDF was silently omitted, while GUI reported
  normal completion.
- **Expected:** distinguish generated/failed/not-requested PDF in the archive;
  warn on partial requested output without hiding other available documents.
- **Implementation:** JSON inventory with run metadata, localized status note,
  frozen structured result plus compatible integer API, specific PDF failure code
  and GUI warning. Atomic publication remains in use.
- **Tests:** 15 new actual bundle/GUI cases in three languages plus 13 atomic cases;
  asset counts updated only for the two new status/inventory files.
- **Evidence:** [bundle status policy](../engineering/bundle_export_status_policy.md).
- **Remaining risks:** real printing, full expected-format manifest, content hashes,
  all-format parity and engineering verification remain open. P0 stays OPEN.

## Review unit 19 — Bundle API run-identity preflight

- **Observed:** direct bundle calls bypassed GUI freshness and could combine a
  changed project with old or mixed feeder run identities; render inputs mutable.
- **Expected:** stale/missing/mixed runs cannot be published as current bundles;
  all files render from one private accepted snapshot.
- **Implementation:** deep copy, recorded project/revision/feeder/run/hash checks
  before staging and after rendering; typed stale error and localized GUI warning.
- **Tests:** 16 public API/late-change/isolation/GUI cases plus 28 bundle cases.
- **Evidence:** [bundle preflight policy](../engineering/bundle_snapshot_preflight_policy.md).
- **Remaining risks:** derived-output hashes, current in-memory/raw input API
  context, all-format guards and engineering verification remain open. P0 stays OPEN.

## Review unit 20 — Fingerprint calculated results and validation rows

- **Observed:** derived payloads/checks could change while preserving an accepted
  run ID, bypassing input-only freshness checks.
- **Expected:** edited currents/cables/devices/statuses/checks require recalculation
  before GUI-current state or bundle publication.
- **Implementation:** immutable metadata carries a canonical derived-result hash;
  engine stamps it, GUI and bundle pre/post checks compare it. Legacy missing hash
  remains deserializable but cannot be treated as a current export.
- **Tests:** 16 new payload/GUI/manifest/generator cases plus 16 preflight cases;
  old macro fixture now retains actual checks without altering asset assertions.
- **Evidence:** [result fingerprint policy](../engineering/calculated_result_fingerprint_policy.md).
- **Remaining risks:** authenticity, standalone API guards, immutable render
  context and engineering verification remain open. P0 stays OPEN.

## Review unit 21 — Standalone primary-report accepted-run guards

- **Observed:** direct primary Excel/HTML APIs bypassed bundle/GUI identity and
  result-fingerprint checks and could render stale/modified data.
- **Expected:** rejected runs cannot overwrite a prior report or be presented as
  accepted/current; rendering uses one private captured snapshot.
- **Implementation:** shared pre/post report guard, private copy and staged atomic
  publication for both public APIs, GUI stale warnings including PDF HTML source.
- **Tests:** 20 public-format/renderer/copy/GUI cases plus 34 XLSX cases. Prior
  synthetic badge fixture now explicitly separates public rejection from rendering.
- **Evidence:** [standalone report policy](../engineering/standalone_report_preflight_policy.md).
- **Remaining risks:** other standalone formats, immutable context, real printing,
  field acceptance and engineering verification remain open. P0 stays OPEN.

## Review unit 22 — Standalone engineering CSV accepted-run guards

- **Observed:** independent CSV APIs could export old/modified run data and did
  not receive the validation list required for full result-fingerprint checks.
- **Expected:** every engineering CSV mode uses the full current run context;
  missing checks cannot silently weaken verification.
- **Implementation:** validations keyword required for successful public exports,
  shared private-copy/pre-post guards and staging; GUI/bundle pass checks and GUI
  shows localized stale warnings.
- **Tests:** 45 new API/mode/context/renderer/GUI cases plus 42 mode/writer cases;
  prior CSV fixtures keep actual checks with unchanged content assertions.
- **Evidence:** [standalone CSV policy](../engineering/standalone_csv_preflight_policy.md).
- **Remaining risks:** diagrams/macros, immutable context, real field acceptance
  and independent engineering verification remain open. P0 stays OPEN.

## Review unit 23 — Accepted-run SVG/DXF file exports

- **Observed:** five drawing file APIs bypassed complete accepted-run checks and
  wrote directly to the chosen destination.
- **Expected:** stale/changed/missing-context runs cannot overwrite an existing
  drawing; successful publication uses one captured calculation.
- **Implementation:** complete checks keyword, shared guarded text publication,
  GUI forwarding/stale/IO messages, bundle context forwarding.
- **Tests:** 63 new five-format/API/render/structure/GUI cases; prior file fixtures
  retain checks and the cap SLD now uses one run without changing content assertions.
- **Evidence:** [drawing publication policy](../engineering/standalone_drawing_preflight_policy.md).
- **Remaining risks:** macros/scripts, CAD/EPLAN field acceptance, immutable context
  and engineering verification remain open. P0 stays OPEN.

## Review unit 24 — Accepted-run EPLAN script/libraries/field kit

- **Observed:** four standalone publication APIs bypassed accepted-run checks and
  library writes could overwrite edited macros or completed user checklists.
- **Expected:** full current checks are required; nonempty library destinations
  remain untouched; generation failure cannot publish a partial new library.
- **Implementation:** guarded staged script file and library directory publication,
  explicit occupied-destination refusal, GUI/bundle checks forwarding and messages.
- **Tests:** 37 new API/directory/renderer/GUI cases; existing structural/encoding/
  checklist fixtures retain actual engine checks without removing assertions.
- **Evidence:** [EPLAN publication policy](../engineering/eplan_export_preflight_policy.md).
- **Remaining risks:** real EPLAN/Windows acceptance, separate verification report,
  immutable context and engineering sign-off remain open. P0 stays OPEN.

## Review unit 25 — Preliminary design-checklist accepted-run publication

- **Observed:** standalone checklist HTML accepted incomplete context and mutable
  report statuses/evidence and wrote directly to the final path.
- **Expected:** only the canonical preliminary checklist for one accepted run is
  published; altered PASS/evidence cannot be smuggled into a run's report.
- **Implementation:** complete feeder/check keywords, copied supplied report,
  canonical pre/post report comparison, shared guarded atomic HTML publication,
  GUI/bundle forwarding and localized stale/IO messages.
- **Tests:** 27 new run/report/context/renderer/three-language GUI cases plus 19
  result-contract cases; previous content/no-PASS assertions unchanged.
- **Evidence:** [checklist publication policy](../engineering/design_checklist_preflight_policy.md).
- **Remaining risks:** real evidence/reviewer workflow, immutable context, signing
  and independent field/engineering acceptance remain open. P0 stays OPEN.

## Review unit 26 — Exportable input text and visible validation failure

- **Observed:** invalid XML/UTF-8 characters could survive input models and fail
  hashing/serialization later; mutable-input recalculation errors escaped the GUI.
- **Expected:** invalid text fails at the named field before arithmetic, without
  silent character replacement; valid FA/EN/DE/tags remain usable.
- **Implementation:** shared before-field text policy on four input model types,
  nested provenance checking, localized messages with ASCII code points; GUI keeps
  prior results stale and displays expected input errors.
- **Tests:** 60 model/nested/engine/actual-report/three-language GUI cases; previous
  input/numeric/export tests remain enabled and unchanged.
- **Evidence:** [text input policy](../engineering/exportable_input_text_policy.md).
- **Remaining risks:** auxiliary data schemas, tag grammar, font/RTL field tests
  and independent numerical/engineering verification remain open. P0 stays OPEN.

## Review unit 27 — Auxiliary curve/rule data gate

- **Observed:** raw trip-curve JSON/mutable caches bypassed consumed-field domain
  checks; duplicate records/keys could replace data and rule free text was unchecked.
- **Expected:** malformed data fails before arithmetic, without catalog repair or
  engineering approval inferred from a source label.
- **Implementation:** shared curve loader/domain validator, engine precheck,
  detached/revalidated lookup, read-only CLI curve scope and rule text policy.
- **Tests:** 62 new curve/cache/CLI/rule/GUI cases; 138 targeted regressions. The
  prior 20 ms fixture supplies explicit parameters with original assertions intact.
- **Evidence:** [curve data policy](../engineering/trip_curve_data_gate_policy.md).
- **Remaining risks:** source authentication, interpolation/runtime applicability,
  remaining auxiliary tables and independent engineering review stay open. P0 OPEN.

## Review unit 28 — Exact curve lookup and runtime domains

- **Observed:** unknown protective series silently inherited DEFAULT; invalid
  arguments/clamping could produce plausible times/bands and TCC/current limits.
- **Expected:** missing curves remain unknown; invalid numeric arguments fail;
  DEFAULT is used only when explicitly selected.
- **Implementation:** exact lookup/optional results, named runtime/overflow checks,
  missing-band engine handling, ratio-only selectivity and unavailable-curve TCC.
- **Tests:** 44 new domain/lookup/selectivity/engine/SVG cases plus 62 structural
  cases; explicit approximation fixtures retained and unsafe unknown expectations
  corrected without disabling tests.
- **Evidence:** [lookup policy](../engineering/explicit_trip_curve_lookup_policy.md).
- **Remaining risks:** reviewed ranges/tolerances, legacy known-curve clamping and
  endpoint behavior, source/setting applicability and engineering sign-off stay open.

## Review unit 29 — Shared catalog-cache content epochs

- **Observed:** only device reads refreshed auxiliary caches; standalone curve,
  rule/standard/PE reads could retain old data after an external database edit.
- **Expected:** every cached accessor detects a new file version or fails clearly;
  failed reloads cannot silently fall back to old rowsets.
- **Implementation:** shared hash epoch/pre/post load checks, whole-cache
  invalidation on change/failure and conservative nonempty WAL/journal rejection
  in catalog identity hashing, with localized guidance and no repair.
- **Tests:** 19 copied-DB/cache/loader/sidecar/actual-engine cases; 125 targeted
  regressions. No original database or sidecar is modified by tests.
- **Evidence:** [cache epoch policy](../engineering/catalog_cache_epoch_policy.md).
- **Remaining risks:** immutable transactions, races/retained references, full
  auxiliary validation and independent engineering verification remain open.

## Review unit 30 — Consumed ampacity/derating numeric domains

- **Observed:** raw SQL numbers/dictionary overwrites and nearest-higher thermal
  lookup could supply malformed or inapplicable data to selection arithmetic.
- **Expected:** invalid rows/duplicates fail before use; exact missing conditions
  remain unknown and cannot be repaired by implicit higher-temperature lookup.
- **Implementation:** shared consumed-row validation, unified exact ampacity APIs,
  runtime argument checks and existing-schema derating domains; localized errors.
- **Tests:** 54 new helper/SQL/engine/three-language GUI cases plus prior regressions;
  corrupted copied fixtures only, original database untouched.
- **Evidence:** [rating domain policy](../engineering/auxiliary_rating_domain_policy.md).
- **Remaining risks:** existing proposal bins/device fallbacks, full auxiliary CLI
  coverage, reviewed sources and independent engineering verification stay open.

## Review unit 31 — Read-only ampacity/thermal inventory CLI

- **Observed:** CLI success did not inspect rating tables outside current-project
  lookups, including unused malformed rows and dangling references.
- **Expected:** complete rating inventory is structurally checked before use;
  invalid catalogs exit nonzero, remain unchanged and are never certified.
- **Implementation:** shared grouped row validation/reference checks, inventory
  counts, pre/post file identity, explicit read-only connection closure and richer
  SQLite integrity diagnostics. Minimal fixtures add empty required tables.
- **Tests:** 31 helper/database/actual-CLI/version/sidecar cases; 132 targeted
  regressions, with prior fixture assertions preserved.
- **Evidence:** [rating CLI policy](../engineering/rating_catalog_cli_policy.md).
- **Remaining risks:** complete auxiliary schema, reference authenticity, immutable
  transactions and independent engineering verification remain open. P0 stays OPEN.

## Review unit 32 — PE section inventory and lookup domains

- **Observed:** unchecked/coerced PE rows, a separate SQL selection path and
  nonpositive requirements could yield misleading section proposals; CLI omitted PE.
- **Expected:** full inventory and request domains checked before selection;
  empty/above-range data stays unknown and invalid data fails without repair.
- **Implementation:** shared positive-finite/duplicate validator, numeric sorting,
  shared cached inventory selection with revalidation, full read-only CLI PE scope
  and count. Synthetic prior fixtures gain an empty required table.
- **Tests:** 46 new helper/SQL/lookup/cache/actual-CLI/engine/three-language GUI
  cases; 226 targeted regressions. Original database bytes remain unchanged.
- **Evidence:** [PE section policy](../engineering/pe_section_data_gate_policy.md).
- **Remaining risks:** PE applicability/thermal/ADS evidence, immutable snapshots,
  other auxiliary tables and independent engineering review remain open. P0 OPEN.

## Review unit 33 — Breaking capacity inventory and exact lookup gate

- **Observed:** first-row SQL selection and numeric coercion omitted duplicate,
  reference, other-voltage and whole-inventory validation.
- **Expected:** malformed normalized ratings fail before use; only explicitly
  recorded exact conditions can supply a capacity; missing conditions stay unknown.
- **Implementation:** shared device/voltage/Icu/optional-Ics parser, reference and
  duplicate checks, runtime request domains and pre/post file identity, explicit
  read-only connection closure, complete CLI inventory/counts. Stored zero/null
  Icu assertions are strengthened to the existing SQL contract; no tests disabled.
- **Tests:** 61 new parser/SQL/CLI/engine/GUI/version/sidecar cases and 258 targeted
  regressions. Copied/weak fixtures only; package database unchanged.
- **Evidence:** [breaking capacity policy](../engineering/breaking_capacity_data_gate_policy.md).
- **Remaining risks:** inherited migration/rating assumptions, manufacturer and
  Ics/duty/backup applicability, immutable snapshots and independent review remain
  open. P0 OPEN; numerical structure alone cannot approve a protection rating.

## Review unit 34 — Registry payload, report lookup and run identity gate

- **Observed:** unchecked JSON/dictionary overwrites, independent report reads,
  silent invalid-entry skips and content hashing without payload validation.
- **Expected:** supported registry shapes remain usable; malformed or duplicate
  sources cannot enter reports or completed engine metadata without a clear error.
- **Implementation:** shared row/shape/text/duplicate validator, cached report
  lookup with revalidation, validated raw-row hashing with file identity guards,
  full CLI registry payload scope/counts and explicit connection closure.
- **Tests:** 54 new parser/cache/hash/CLI/engine/three-language GUI/sidecar cases;
  171 targeted regressions. Existing synthetic fixture gains an explicit code;
  no original assertions are removed and the packaged database remains unchanged.
- **Evidence:** [registry payload policy](../engineering/standards_registry_data_gate_policy.md).
- **Remaining risks:** normalized SQL fields, source/edition/applicability and
  reference completeness, immutable snapshots and electrical review remain open.
  Structural success cannot validate a source or close P0.

## Review unit 35 — Selectivity SQL/JSON row and reference gate

- **Observed:** pre-validation flag filtering, unchecked SQL/JSON divergence and
  references, permissive coercion and silently ignored extra conditions.
- **Expected:** all stored rules checked before activation; malformed, dangling
  or unsupported conditions cannot enter calculation or imply reviewed evidence.
- **Implementation:** strict rule models, shared row identity/domain/consistency
  parser, full-inventory series/part linkage, explicit rejection of unrepresented
  restrictions, engine precheck and read-only CLI enabled/total counts.
- **Tests:** 58 new model/row/cache/actual-CLI/engine/three-language GUI cases;
  358 targeted regressions, including mutable caller catalog/source separation.
  Prior minimal fixtures add SQL columns without
  invented records, removed assertions or disabled tests. Package DB unchanged.
- **Evidence:** [selectivity row policy](../engineering/selectivity_rule_row_gate_policy.md).
- **Remaining risks:** actual source/duty/range/coordination applicability,
  inherited migration claims, immutable snapshots and independent electrical
  review remain open. SQL labels/flags cannot close P0 or authenticate a rule.

## Review unit 36 — Trip-curve SQL/JSON and approximation policy gate

- **Observed:** normalized thresholds, labels and approximation/verification
  flags were ignored by the reader; cached JSON policy claims were unchecked.
- **Expected:** full rows agree before use and cannot promote approximate curves;
  malformed or conflicting records fail without fallback or data repair.
- **Implementation:** shared complete row query/parser, exact threshold/metadata
  matching, existing SQL policy enforcement, cached JSON policy checks, explicit
  read-only connection closure and CLI approximation-policy/scope reporting.
- **Tests:** 59 new model/SQL/cache/actual-CLI/engine/three-language GUI cases;
  320 targeted regressions. Prior row fixtures gain required fields and valid
  cache-refresh data updates both representations; all assertions remain active.
- **Evidence:** [curve row policy](../engineering/trip_curve_row_gate_policy.md).
- **Remaining risks:** source/range/setting/time/coordination applicability,
  inherited interpolation/clamping, immutable snapshots and independent review
  remain open. Approximate-only data cannot close P0 or prove protection safety.

## Review unit 37 — Reproducible synthetic scenario runner

- **Observed:** policy regressions existed as separate tests without a single
  repeatable scenario/report command and explicit per-case difference output.
- **Expected:** reviewable fixed software expectations run in three locales,
  compare actual HTML/XLSX validation rows and fail clearly on drift/error without
  generating or claiming independently approved reference answers.
- **Implementation:** ten JSON-defined scenarios, CLI structured results and
  exit status, numeric/status locale comparison, public report generation/parity,
  source identity checks, temporary cleanup and strict definition validation.
- **Tests:** 19 new actual-CLI/corrupted-document/drift/error/schema cases;
  78 targeted regressions. Definitions, catalog and user files remain unchanged.
- **Evidence:** [scenario runner policy](../engineering/software_scenario_runner_policy.md).
- **Remaining risks:** zero independent engineering cases; physical models,
  source applicability/tolerances, other formats, immutable contexts and electrical
  review remain open. A synthetic software PASS cannot close P0.

## Review unit 38 — Device core SQL/JSON consistency gate

- **Observed:** normalized core fields were ignored and SQL quality overwrote raw
  quality, allowing conflicting representations to reach device selection.
- **Expected:** bounded duplicate identities/numbers/quality agree before use;
  native invalid values fail and existing unknowns cannot become certified ratings.
- **Implementation:** shared core query and exact row checks, raw numeric/type and
  exportable-text validation, explicit quality consistency before non-promotion,
  nullable/default conventions, read-only connection closure and CLI scope update.
- **Tests:** 60 new domain/row/cache/actual-CLI/engine/three-language GUI cases;
  234 targeted regressions. Minimal source fixtures align SQL fields and valid
  series refresh updates both representations; existing assertions remain active.
- **Evidence:** [device core row policy](../engineering/device_core_row_gate_policy.md).
- **Remaining risks:** other normalized/source fields, broader model coercion,
  actual duty/temperature/voltage/thermal applicability, immutable contexts and
  independent review remain open. Consistency alone cannot close P0.

## Review unit 39 — Device airflow/kvar/IP/pole metadata gate

- **Observed:** auxiliary duplicate fields were unchecked; IP numeric metadata
  could contradict the declaration and omitted source IP inherited model IP20.
- **Expected:** stored metadata agrees before use, invalid representations fail,
  unknown source IP remains unknown and matching metadata cannot certify a device.
- **Implementation:** extended shared device query/numeric domains, native pole
  metadata linkage, literal/derived IP consistency and explicit unknown IP when
  loading absent declarations. Existing IP compatibility restrictions remain.
- **Tests:** 65 new domain/row/cache/actual-CLI/engine/three-language GUI cases;
  292 targeted regressions. Old fixtures gain matching fields; all assertions stay
  active and the package database remains unchanged.
- **Evidence:** [device auxiliary row policy](../engineering/device_aux_row_gate_policy.md).
- **Remaining risks:** datasheet/FK provenance, physical pole/fan/capacitor/IP
  applicability, broader model coercion, immutable contexts and independent review
  remain open. No manufacturer/assembly approval or P0 closure is implied.

## Review unit 40 — Datasheet source records and device links

- **Observed:** source table shape and device source_id links were not checked,
  including unused corrupt records, duplicate IDs and dangling references.
- **Expected:** all source records and exact links are structurally valid before
  device/rule use, with absent links unverified and generic labels never proof.
- **Implementation:** shared source parser/reference checker, same-connection
  runtime/rule/CLI loading, source/link counts and existing cache/hash safeguards.
  Optional revision and legacy labels are preserved without inventing review.
- **Tests:** 44 new domain/record/link/cache/actual-CLI/engine/three-language GUI
  cases; 285 targeted regressions. Prior fixtures add empty source tables/null
  links with existing assertions intact; original database remains unchanged.
- **Evidence:** [datasheet source policy](../engineering/datasheet_source_gate_policy.md).
- **Remaining risks:** actual source authentication, exact property applicability,
  reviewed values/tolerances, publishing workflow, immutable contexts and independent
  electrical review remain open. Structural linkage cannot close P0.

## Review unit 41 — Native device numeric input boundary

- **Observed:** direct/API/JSON device construction coerced bool/numeric strings,
  including raw-only coil/SPD fields outside normalized SQL comparisons.
- **Expected:** all declared device numbers are finite native int/float values;
  invalid supplied or mutated inputs fail before calculation with a named error.
- **Implementation:** shared before-validator for 24 float device attributes,
  existing snapshot revalidation and catalog error wrapping for SQL model failures.
  Native defaults/zero sentinels, strings/enums and existing range checks remain.
- **Tests:** 66 new model/JSON/copy/actual-SQL/CLI/engine/three-language GUI cases;
  392 targeted regressions. Original data/assertions remain unchanged; only a new
  diagnostic-warning expectation was corrected without removing rejection checks.
- **Evidence:** [native numeric policy](../engineering/catalog_native_numbers_policy.md).
- **Remaining risks:** device-specific physical ranges, broader input/import
  boundaries, source/duty/setting applicability, mutable contexts and independent
  engineering review remain open. Native input types cannot close P0.

## Review unit 42 — Consolidated input, checklist and output consistency

- **Observed:** project/feeder inputs still coerced bool/text, Excel silently
  truncated counts and boolean cells, clipboard accepted NaN, a linked busbar
  error could disappear as NOT_VERIFIED, and diagrams/parts used source-only Ik
  or 400 V capacities outside their scope. Placeholder methods could claim
  COMPLETED merely with a source label.
- **Expected:** invalid inputs fail clearly; actual failures remain visible;
  exported fault/rating scope agrees with the engine and project voltage.
- **Implementation:** strict native numeric/boolean input boundary, explicit
  exact spreadsheet conversion and workbook closure, finite clipboard checks,
  method placeholder downgrade, linked ERROR-to-FAIL checklist behavior, exact
  voltage TCC/parts capacity and total-main-bus SLD/TCC fault display. Existing
  public export preflight and proposed/unverified statuses remain active.
- **Tests:** 103 new cases, including actual engine and three-language file
  exports; 106 focused cases pass. The prior TCC test now checks the correct
  total scope while retaining the network-only value assertion. No acceptance
  assertion or inherited PDF check was disabled. Final full suite: 1810 passed,
  1 inherited PDF failure, 1 Windows compiler skip; all 30 synthetic scenario
  runs and the four-feeder/71-check GUI smoke pass. Database bytes unchanged.
- **Evidence:** [consolidated pass and remaining acceptance](p0_remaining_acceptance.md),
  full command results and `/workspace/audit-evidence/p0-batch-*`.
- **Remaining risks:** six grouped acceptance areas remain, including unfinished
  physical models, source authentication, independent cases, immutable contexts
  and actual PDF/runtime acceptance. PDF diagnostics did not resolve rendering;
  no unsafe browser workaround was introduced. P0 remains OPEN; this batch is
  not completion of all software or engineering requirements.

## Review unit 43 — Continuous P0 software delivery

- **Observed:** output copies remained mutable and reads used live catalog/global
  language state; PDF rendering failed; IEC preview/file paths bypassed public
  preflight; invalid Excel imports replaced the current project; helper types
  could coerce/crash, and evidence ownership was hidden in checklist exports.
- **Expected:** immutable accepted context, consistent output scope/status and
  safe publication, actual PDF output, unchanged user state on invalid import,
  explicit evidence gaps and repeatable automated checks.
- **Implementation:** shared frozen export/context-local source/locale sessions,
  isolated paged PDF worker/process cleanup, shared project validation and
  atomic GUI import, secondary IEC export guards, all-format notices, explicit
  checklist evidence columns, blocked reference inventory/comparison tool and CI.
- **Tests:** actual three-language bundles with readable PDFs, source
  change/restore race, private cache/model isolation, spawned-child timeout,
  invalid GUI imports and helper boundaries, reference-schema/difference checks,
  full inherited suite, synthetic scenarios and actual Tk launch. Final outcomes
  are recorded in the linked delivery report; no success is inferred from code.
  Final full suite: **1874 passed, 1 Windows compiler skip, zero failures**;
  63 new cases. All 30 synthetic scenarios and the four-feeder/71-check real Tk
  smoke pass. The default independent-reference pack remains BLOCKED / exit 2.
- **Evidence:** [software delivery and remaining blocks](p0_software_delivery.md),
  raw `/workspace/audit-evidence/p0-completion-*` logs.
- **Remaining risks:** evidence-dependent physical implementation and independent
  sources/review still block P0; Windows/EPLAN acceptance is not available here.
  No authentication, engineering approval, merge or release is claimed.

## Review unit 44 — Companion scope and functional handoff

- **Observed:** macro/CAD generation and fabricated numeric wiring lists did
  not match the user's desired preliminary-design companion product.
- **Expected:** retire the explicitly rejected outputs; show functional
  connections and the separately approved architecture blocks; preserve remaining
  outputs pending one-at-a-time user review.
- **Implementation:** removed active macro/script/DXF/kit generators and UI/ZIP
  paths; shared equipment-level connection model in GUI/CSV/XLSX/HTML/PDF;
  conceptual block architecture with readable Persian labels and run status.
  Retained preview fault/rating fallback corrected; calculation models/data kept.
- **Tests:** new scope/absence/connection/architecture/locale/typography cases;
  retained library/CSV/atomic/report guards, full regression suite and GUI smoke.
  Final full suite: **1833 passed**, no failures/skips; all 30 synthetic scenario
  runs pass. Actual Tk smoke recalculates four feeders/71 checks and verifies
  displayed functional rows. Source DB is unchanged. The linked report records
  deliberate retirement of obsolete tests and the actual rendered sample review.
- **Evidence:** [delivery and limitations](companion_scope_delivery.md),
  [product decisions](../product/direction.md), actual architecture and connection
  samples under `/workspace/audit-evidence/companion-samples/`.
- **Remaining risks:** other outputs await explicit discussion; functional
  connections are not final wiring, and independent engineering/data review
  remains open. No target-tool compatibility, construction approval or release.
