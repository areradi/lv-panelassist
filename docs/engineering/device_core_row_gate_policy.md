# Device core SQL/JSON consistency gate

## Observed / expected

Device loading selected only device_id/raw_json/data_quality. It checked the part
identity but ignored duplicate core fields in SQL. A changed manufacturer, category,
series, current, loss or dimension could therefore disagree with the selected
JSON device. A SQL quality label also silently overwrote contradictory raw quality.

The shared row loader now reads and checks the following bounded core scope:

| SQL field | JSON/model field |
| --- | --- |
| device_id | part_number (existing exact identity check) |
| category | device_type |
| manufacturer / series | manufacturer / series |
| model | explicit JSON model, otherwise part_number |
| in_a | rated_current_in_a |
| icu_ka_400v | icu_ka_400v (legacy metadata, not a runtime voltage lookup fallback) |
| power_loss_w | power_loss_w |
| derating_40c / derating_50c | matching model fields |
| width_mm / height_mm / depth_mm | matching model fields |
| data_quality | explicit raw data_quality, if present |

Text identities must be nonblank/exportable and agree exactly. Explicit raw
numeric values and SQL numbers must be native finite non-boolean numbers; text
coercion through Pydantic cannot conceal invalid raw numeric input. SQL values
must be nonnegative and equal model values. No numerical tolerance is invented.
The existing model's nonnegative/default conventions remain; these domains alone
cannot establish applicability or physical correctness of a positive value.

SQL nullable current/Icu/dimension fields may remain null only when the model value
is the legacy unknown/not-applicable zero (including absent JSON with default zero).
A positive JSON/model value cannot match a null SQL value. Required SQL losses and
40/50 C factors remain non-null and must agree with existing model defaults if
omitted in JSON. No unknown is filled with a fabricated physical rating.

An explicit raw quality label must agree with SQL before model validation. Missing
raw quality retains existing SQL-label handling; all effective whole-device quality
still becomes ESTIMATED because no aggregate reviewed-device contract exists.
Consistent REAL_VERIFIED labels do not certify a device or its properties. Exact
per-property evidence matching remains separate. Text anywhere in the raw payload,
including ignored extra source notes, must be exportable.

Runtime device reads, selectivity source-inventory reads and the catalog CLI use
the same query/parser. Runtime device connections now close explicitly. Existing
cache content epochs invalidate old lists and reject a failed reload without
fallback. The engine's existing source precheck also catches bad source rows when
given a previously valid/custom in-memory device selection. CLI scope describes
the core consistency checks and still reports NOT_VERIFIED.

Prior minimal CLI fixtures gain matching core columns/values for their existing
synthetic device, with no new engineering rating/evidence or removed assertions.
The valid device cache-refresh fixture now updates SQL and JSON series together;
its reload assertion remains. New cases separately reject incoherent versions.
No SQL repair, migration, package database or user-data write is performed.

## Evidence / limits

60 new cases cover text/numeric/quality mismatches, invalid native domains and raw
JSON bool/text coercion, nullable/default-zero conventions, explicit model metadata,
non-promotion of consistent quality labels, ignored-extra text, actual copied SQL
device/rule/CLI failure and cache invalidation, coherent current updates, byte
preservation, and actual engine plus GUI stale-result handling in FA/EN/DE.
234 targeted regressions pass, including scenario-runner and earlier catalog gates.
Raw logs: `/workspace/audit-evidence/device-core-*` outside the checkout.

This is a bounded duplicate-field gate. Other normalized columns (airflow/kvar/IP,
poles and source_id/FK/source metadata), remaining raw attributes and the direct
in-memory model's broader coercion behavior require separate review. Source
authenticity, voltage/duty/temperature applicability, thermal/physical accuracy,
immutable transactions and independent engineering cases remain open. Structural
agreement is not manufacturer verification or electrical approval. P0 remains OPEN;
no merge or release is implied.

## Stable checkpoint validation

Full suite: **1532 passed, 1 failed, 1 skipped** in 74.35 s. The inherited
`TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and Windows compiler skip remain.
New-test Ruff, changed legacy-file F checks, compilation and diff checks pass;
global lint/types are not claimed clean. All 30 standalone synthetic scenario
runs pass (ten cases x three locales), still NOT_VERIFIED/zero independent cases.
Actual GUI smoke recalculates four feeders and 71 validation rows. Packaged CLI
checks 102 devices and prior inventories; DB SHA256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `91ee432`; prior audit units required.
Main remains untouched.
