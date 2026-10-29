# P0 software delivery and remaining technical blocks

وضعیت ساده: اصلاحات مستقل از مرجع مهندسی در این بسته پیوسته انجام شده‌اند،
از جمله PDF واقعی، ثابت‌بودن داده و زبان خروجی، حفظ پروژه در ورود نامعتبر و
کنترل مسیرهای فرعی نقشه. پایان کل P0 هنوز اعلام نمی‌شود: بخشی از پیاده‌سازی
مدل‌های مهندسی نیز به روش و ورودی مرجعِ بازبینی‌شده نیاز دارد. آن بخش‌ها با
نتیجهٔ نامعلوم باقی می‌مانند و با تعداد تست‌ها «تمام‌شده» محسوب نمی‌شوند.

## Delivered behavior

| Area | Concrete behavior in this batch |
| --- | --- |
| Immutable export input | ExportContext stores accepted project/results/checks as immutable JSON plus catalog bytes and language/translation bytes. Each renderer receives detached validated models; changed render models fail preflight. Reports, drawings, scripts, libraries and the complete bundle use this context. |
| Catalog reads | Render sessions use a private read-only SQLite snapshot and private caches. Cached mutable values are detached on access. Changing and restoring the original source during rendering cannot mix rows from different source contents. The original source identity is still checked before publication. Remaining read-only connection lifetimes are explicitly closed. |
| Locale stability | Context-local FA/EN/DE language and translation tables remain fixed for the whole export, even when the user changes the global language while it runs. Nested exporters inherit the effective language/tables. User language selection remains available for subsequent work. |
| Actual PDF | WeasyPrint 68.x provides paged HTML/SVG rendering in an isolated bounded worker. Linux auto mode uses it; Windows/macOS retain the installed-browser path when available. Explicit browser mode and structured failure reasons remain. The existing PDF roundtrip is enabled and now succeeds locally. No browser sandbox is disabled. |
| Renderer lifecycle | Dedicated process groups, timeout/failure cleanup, unique private profile/output directories, PDF format validation, fsync and atomic destination replacement protect existing documents. POSIX descendant cleanup is exercised with an actual spawned child. Windows process-tree handling still needs a Windows acceptance run. |
| Numeric boundaries | Helper APIs reject boolean/text/collection/overflow inputs without producing a pass or crashing on type conversion. Nonrepresentable PE results are rejected; an undocumented k factor remains WARNING even if a caller claims an exact trip curve. Existing missing-data and >5 s behavior remains. No new engineering formula or tolerance is introduced. |
| Atomic input state | Engine and spreadsheet ingestion share project/feeder validation, including duplicate/empty feeder rejection. Missing worksheets and duplicate project keys fail explicitly. GUI commits imported state only after successful validation; invalid enums, numbers, duplicates or empty files preserve the current project and results. |
| Secondary IEC exports | Single SVG, browser preview, folder export and HTML schematic injection now use current-run preflight and atomic writers. Existing libraries are never overwritten. Feeder identities are preserved inside drawings while filename separators are encoded. Injected base reports must contain the accepted run identity. |
| Output notices | Public SVGs include the run identity, status and preliminary watermark; DXF, C# and macro XML carry a preliminary/status/run notice. Generic parts and connections CSV retain their existing columns and append selection status, overall status and run fingerprint. Parts Management keeps its fixed headers and carries the notice in Description 2. Actual EPLAN mapping/import acceptance remains open. |
| Checklist evidence | All 13 rows expose source/applicability, evidence document, reviewer and review date in XLSX/HTML. Missing evidence is explicitly “not recorded” in all three languages; no reviewer or approval is invented. |
| Reference comparison preparation | A read-only tool accepts supplied reference claims with source/revision/page/method/reviewer/date, supported quantities/units and explicit finite tolerances/rationale. It reports differences and rejects invalid/duplicate records. The shipped ten-case inventory contains no fabricated expected values and returns BLOCKED/exit 2. Matching supplied claims never authenticates them or promotes engineering quality. |
| Repeatable checks | A repository GUI smoke command and GitHub Actions workflow run the full suite, actual PDF rendering, synthetic three-language scenarios and GUI launch. Remote CI execution must be checked separately; local results do not imply remote workflow success. |

## Run locally

Install Python requirements with `python -m pip install -r requirements-dev.txt`.
Linux PDF rendering also requires Pango/font libraries. The Ubuntu CI job installs
`libpango-1.0-0`, `libpangoft2-1.0-0` and `fonts-dejavu-core`; Tk/GUI smoke uses
`python3-tk` and Xvfb. Windows retains Edge/Chrome as the default installed-browser
route and requires actual target-machine testing. WeasyPrint needs its documented
native libraries when selected explicitly on Windows/macOS.

Run `python -m pytest -q --tb=short` for software checks and actual PDF tests.
Run `python scripts/run_regression_scenarios.py` for the ten synthetic scenarios
in EN/FA/DE. Run `xvfb-run -a python scripts/gui_smoke.py` on Linux with Xvfb.
PDFs are tested using pypdf for page structure, readable project/feeder text and
the preliminary notice, including actual bundle generation in all three locales.
The full manifest stays available in HTML; print/PDF shows the compact run
fingerprint so an unwrapped JSON snapshot cannot run across the page edge.
These checks do not replace visual approval of every page, Windows DPI testing
or real EPLAN import. Changes to source identity require recalculation.

Run `python scripts/run_reference_acceptance.py` to inspect reference readiness.
The default exits **2 / BLOCKED**. It is deliberately not a passing numerical
reference suite. A supplied pack uses all ten case IDs in
`tests/reference_cases/pending.json`; completed rows replace the pending state
with `PROVIDED` and the fields declared by ReferenceCase/ReferenceMetric in
`lv_assist/reference_acceptance.py`. Expectations are never generated from the
application automatically. The current comparison supports selected feeder
numeric/fault quantities; this does not close every assembly/protection reference
acceptance requirement. Independent source authentication/sign-off remains external.

## Explicit remaining blocks

- Reviewed source/route/return-path/temperature methods and input schemas are
  still needed before implementing and validating the missing feeder-end/L-PE,
  TN/TT/IT ADS, PE/PEN and RCD models. They currently return unknown. This is
  unfinished evidence-dependent implementation, not merely missing paperwork.
- Exact Ics/duty/curve/time/setting applicability, Type 1/2 motor/drive
  coordination and separate backup/cascading still require applicable reviewed
  manufacturer data and methods. Generic curves/ratios remain preliminary.
- Busbar/thermal limits, supports, ventilation and assembled IP need applicable
  method/manufacturer/assembly evidence and independent numerical review.
- Zero authenticated independent reference cases or signed assembly approvals
  are available. The reference tool cannot create those facts.
- Real Windows clean-install/DPI/browser/process-tree checks and actual EPLAN
  2024 field acceptance remain unavailable in this Linux workspace. P1/P2/P3 UX,
  project persistence, editable import preview and packaging are outside this P0
  software pass and remain deferred by the original gate.

The input/output protections above are software delivery. P0 remains **OPEN**;
no construction, beta, release or EPLAN-import-ready acceptance is asserted.

## Executed checks

| Check | Actual result |
| --- | --- |
| `.venv/bin/python -m pytest -q --tb=short` | **1874 passed, 1 skipped** in 201.73 s; zero failures. The retained skip requires Windows `csc.exe`. The former PDF roundtrip failure now passes. |
| New coverage | 63 new cases: 41 snapshot/import/numeric/PDF/checklist cases, 14 reference-ingestion cases, eight IEC preview/injection cases. Existing browser-failure tests explicitly select the browser backend and retain their rejection/byte-preservation assertions. |
| `scripts/run_regression_scenarios.py` | 30 PASS across ten synthetic cases × EN/FA/DE; NOT_VERIFIED and zero independent reference cases. |
| `DISPLAY=:131 .venv/bin/python scripts/gui_smoke.py` with isolated Xvfb | Real window rendered and recalculated four feeders / 71 validation rows. |
| `scripts/validate_catalog.py` | 102 devices structurally valid; engineering NOT_VERIFIED. |
| `scripts/run_reference_acceptance.py` | BLOCKED / exit 2; all ten required references still absent. This is the expected readiness result, not a numerical acceptance pass. |
| New modules/scripts/tests Ruff; changed legacy application F checks | Passed. No global lint/type-clean claim. |
| Compileall, pip dependency check, Git diff check | Passed. |
| Actual Persian sample | Ten-page PDF, 101381 bytes; first page rendered and visually inspected after correcting manifest overflow. Native text/page/preliminary/identity assertions pass for all three locale bundles. Full visual acceptance of every page is not claimed. |

The pure C# generator and file writer were kept identical after a full-suite
parity failure exposed a notice added only to the writer. The generator now owns
the notice; the existing exact-content assertion remains unchanged and passes.
The printed report preserves a compact identity while the full manifest remains
available in HTML. No inherited test is disabled to obtain these results.

Raw logs are under `/workspace/audit-evidence/p0-completion-*`. The sample is
`/workspace/audit-evidence/p0-completion-sample/report-fa.pdf` and remains a
preliminary document with INSUFFICIENT_DATA. The packaged database remains
byte-identical, SHA256
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No reference values, source approvals or user project data are created or
overwritten by the audit tools. The branch follows `5a6fd17`; main is not merged.
