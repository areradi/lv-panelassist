# P0 remaining acceptance and consolidated software pass

Update after this checkpoint: [continuous software delivery](p0_software_delivery.md)
adds immutable export/catalog/locale snapshots, actual working PDF rendering,
atomic invalid-import handling, secondary IEC guards, evidence columns and CI.
The validation figures and PDF diagnosis below describe review unit 42; they
are historical and are superseded by the newer delivery report.

وضعیت به زبان ساده: فاز P0 هنوز تمام نشده و برای اعلام درصد دقیق مبنای
قابل‌اعتماد نداریم. شش گروه کار اصلی در جدول زیر باقی است؛ بخشی از خود مدل‌های
محاسباتی نیز هنوز تکمیل و اعتبارسنجی نشده‌اند. اصلاحات نرم‌افزاری را می‌توان
پیوسته انجام داد، اما پایان P0 به منابع مستقل، نمونه‌های مرجع و تأیید واقعی
مهندس برق نیاز دارد. بسته‌های شماره‌دار قبلی، تعداد فازهای تمام‌شده نیستند.

P0 is **OPEN**. The numbered review units in the work register are software
change packages, not completed product phases or a percentage of P0. There is
no measured basis for a completion percentage. Important physical models and
their independent acceptance remain unfinished; this is more than obtaining a
signature for finished calculations. The user has confirmed that independent
sources are unavailable and asked to retain unverified status.

## Remaining acceptance, grouped for planning

These six groups collect the open requirements; they are not six small tasks.
The detailed topic matrix remains [verification_matrix.md](../engineering/verification_matrix.md).

| Group | Work still required | Evidence needed to close |
| --- | --- | --- |
| Network, L-PE, ADS and PE | Implement applicable source/route/return-path and temperature models, feeder-end maximum/minimum faults, separate TN-S/TN-C-S/TT/IT behavior and applicable disconnection/PE checks. Existing transformer diagnostics are insufficient. | Reviewed formula/domain/units and independent network cases, including the three network reference cases requested in the original brief; missing-data cases must remain unknown. |
| Protection and coordination | Review exact curve/setting/time applicability, cable/neutral/harmonic assumptions, actual Ir/I2, Ics and duty, motor Type 1/2/VFD/soft-starter coordination, and separate backup/cascading. Ratio screening and approximate curves cannot certify these. | Applicable manufacturer documents for exact parts, voltage, settings and conditions, reviewed limits and mismatches. |
| Assembly behavior | Review busbar Icw/Ipk/support geometry, thermal model/limits/ventilation and assembled IP; complete the evidence/reviewer fields for all 13 checklist rows. | Applicable assembly/manufacturer/test evidence. Current calculated recommendations do not prove IEC 61439 compliance. |
| Property evidence and ingestion | Complete authentication, exact property applicability, review and safe publication of critical catalog/standard data. Existing structural SQL/JSON consistency and source links cannot authenticate it. | Document/revision/page/table, units/conditions, exact subject/value and named reviewer/date. No fabricated VERIFIED records. |
| Independent numerical acceptance | Supply and automate the original reference pack: at least ten controlled cases with independently obtained expected results, justified tolerances and electrical review. | **Zero** independent cases currently available. Ten synthetic scenarios across three locales do not count as independent cases. |
| Software and target-runtime acceptance | Shared immutable run/catalog/locale context, invalid-input/import protections, current-run file guards and working Linux PDF are now delivered in unit 43. Remaining evidence-dependent model coverage and actual Windows/EPLAN acceptance require their inputs/target environments. | See the newer software delivery report for current executed checks. No beta/construction/EPLAN-ready claim based on Linux tests. |

Work that does not require invented engineering values can continue in batches.
Engineering-sensitive completion must wait for actual applicable evidence and
review. The test plan must preserve both explicit failures and unknown results.
P1/P2/P3 product development remains deferred by the original P0 gate.

## Consolidated software changes

This pass follows review unit 41 and groups related input/result/output fixes:

- ProjectSpec and FeederInput accept native finite numbers and explicit booleans;
  bool-as-number, numeric text/bytes and nonfinite values cannot silently become
  calculated quantities. Native integer fields reject floats/text; integer
  interchange uses a signed 64-bit representation limit, not a physical limit.
  Existing physical constraints, enums, native defaults and optional unknowns
  remain. Existing engine snapshot revalidation catches invalid assignment/copy.
- Spreadsheet conversion remains explicit at the import boundary. Quantities
  reject booleans/nonfinite/formula cells; count/phase text is checked exactly
  rather than truncated or rounded through float. Optional short rows retain
  defaults; recognized boolean representations include FA/EN/DE. Invalid boolean
  cells report sheet/row/column instead of silently becoming false. Workbooks
  close on both success and failure. Formula text is read with `data_only=False`
  rather than borrowing cached results; literal function tags remain text.
  Template phase choices match the supported 1P/3P domain.
- Clipboard power/length reject NaN/Inf while retaining other valid rows and
  reporting the invalid row/column.
- Blank/UNSPECIFIED/legacy methods cannot claim COMPLETED merely because a
  source label is present. This is a placeholder guard, not full evidence review.
- A checklist row linked to an actual ERROR now remains FAIL. In particular,
  RULE-BUS-024 overload can no longer disappear as a generic NOT_VERIFIED row
  in Clause 10.7. Missing assembly evidence still cannot create PASS.
- TCC and EPLAN parts capacity output use exact project-voltage Icu, omitting
  unavailable ratings rather than substituting 400 V. The SLD heading and TCC
  bus marker use the engine's main-bus total including its explicitly preliminary
  motor contribution; the scoped TCC caption sits above the graph so it remains
  visible near the right-edge marker. Neither diagram proves motor-model validity or a
  feeder-end fault. Public file exports retain current-run preflight guards.

No numerical reference, catalog database, engineering formula, tolerance,
dependency, release, main merge or manufacturer verification is introduced.
The existing import API still raises on invalid quantitative input; this pass
does not claim the later editable/atomic preview or arbitrary column mapping UX.
Engine source identity changes require recalculation of earlier saved results.

## PDF investigation

A minimal local HTML input fails before producing a PDF in this command sandbox
(Chromium exit -5, crashpad setsockopt permission error). In the approved process
runtime it times out, including a bounded check with valid Fontconfig paths and
safe shared-memory/background-network flags. D-Bus/Mojo diagnostics persist;
the precise rendering cause remains unresolved. No application PDF code was
changed, browser sandbox disabled, test skipped, or printing success claimed.
Diagnostic browser process groups were stopped. Raw diagnostics are under
`/workspace/audit-evidence/p0-consolidated-pdf/` in this cloud workspace.

## Validation

These are software checks, not independent numerical or signed engineering
acceptance. The 103 new cases cover strict native inputs, exact spreadsheet
counts, clipboard nonfinite rejection, actual invalid/short workbook loading,
closure on failure, placeholder methods, mutated-input engine rejection, and
actual engine/checklist/HTML/XLSX/TCC/SLD/parts exports in EN/FA/DE.

The existing TCC regression previously expected the network-only `22.0 kA`
label. It now asserts that the network value remains 22.0 in the result, motors
increase the main-bus total, and the diagram shows the labeled total instead.
No assertion was removed to conceal an unexpected calculation failure. The
inherited PDF roundtrip remains enabled; the Windows compiler skip is retained.

| Command | Actual outcome |
| --- | --- |
| `.venv/bin/python -m pytest -q --tb=short` | **1810 passed, 1 failed, 1 skipped** in 201.43 s; sole failure is inherited `TestPhase3Pdf.test_html_to_pdf_roundtrip`, skip requires Windows `csc.exe` |
| `.venv/bin/python -m pytest -q tests/test_p0_consolidated_software.py test_lv_assist.py::TestPhase3Tcc --tb=short` | 106 passed |
| `.venv/bin/python scripts/run_regression_scenarios.py` | 30 runs PASS: ten synthetic scenarios × EN/FA/DE; NOT_VERIFIED, zero independent cases |
| `DISPLAY=:129 bash /workspace/.cloud-setup/start.sh --smoke` with isolated Xvfb | GUI rendered and recalculated four feeders, 71 validation rows |
| `.venv/bin/python scripts/validate_catalog.py` | STRUCTURALLY_VALID: 102 devices, 12 rules, 16 curves; engineering NOT_VERIFIED |
| `.venv/bin/ruff check lv_assist/input_numbers.py tests/test_p0_consolidated_software.py` | Passed |
| Ruff F checks on changed legacy application files, compileall, `git diff --check` | Passed; no global lint/type-clean claim |

Raw outputs use `/workspace/audit-evidence/p0-batch-*`. The packaged database
remains byte-identical, SHA256
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
Final scenario identity reports engine source hash
`8989a72cf8d1ffcd0707246a40740010f1dbb8fd787234f042ad9259282efe43`.
This checkpoint follows `3170ff1` and requires the earlier audit units. It has
no newly failing test relative to that baseline; the suite is not wholly green
and PDF readiness is not claimed. Main remains untouched.
