# Device airflow, capacitor, IP and pole metadata gate

## Observed / expected

Normalized fan airflow, capacitor ratings, IP metadata and pole counts were outside
the core SQL/JSON comparison. Raw JSON poles were ignored by the device model and
the IP numeric column could contradict the source declaration. Omitted source IP
also inherited the generic model default IP20 when reading the database.

The shared device query/parser now additionally checks:

| SQL field | Checked source |
| --- | --- |
| airflow_m3h | native finite nonnegative JSON/model airflow_m3h |
| kvar_rating | native finite nonnegative JSON/model cap_kvar_400v |
| poles | native nonnegative integer JSON poles, if provided |
| ip_rating | literal explicit JSON IP declaration |
| ip_numeric | exact native integer derived from the declared supported code |

Airflow/kvar use the core validator's existing null/zero conventions. A null SQL
value can match an omitted/default or explicit zero unknown, but cannot conceal a
positive model value. Raw JSON bool/numeric text cannot be accepted through model
coercion. No value, tolerance or manufacturer applicability is invented.

Poles remain metadata; their comparison does not add a pole-selection/arrangement
solver. Counts must be native integers within SQLite's int64 range, without an
invented engineering upper bound. Null/zero remain unknown equivalents; positive
counts must match exactly. Bool/text/fractional or overflowing representations fail.

IP codes supported by this stored-data gate are literal ASCII IP[0-6][0-9]. The
normalized number must agree, including IP00 -> integer zero. Optional raw
ip_numeric, if supplied, must also agree. Missing/empty IP requires absent numeric
metadata; the gate never extracts digits from malformed, dual, suffix or IPX codes
to make them usable. Unsupported syntax fails explicitly and needs separate source
and applicability support. Matching IP68 metadata remains permitted as data, while
the existing conservative ip_meets compatibility filter remains unchanged and
cannot automatically substitute immersion for jet protection.

When raw database JSON omits ip_rating, the loader now explicitly uses an empty
unknown value instead of inheriting IP20. The 96 packaged records without a source
declaration therefore retain unknown IP in their loaded models. Explicit source
ratings remain intact, and no SQL declaration or original database byte is added
or rewritten. The general in-memory CatalogDevice default remains unchanged for
compatibility; it is not proof of a manufacturer's IP declaration.

Runtime device loading, selectivity source inventory and read-only CLI share these
checks. Existing content epochs prevent fallback to old cached devices after a
bad file update. Effective whole-device quality remains ESTIMATED. The CLI scope
reports the added fields and still declares engineering_verification NOT_VERIFIED.

Prior minimal CLI fixtures add the required fields matching their existing model
defaults. Previous core-row fixtures add matching auxiliary metadata. Assertions
and scenarios remain active; no engineering reference is invented or test disabled.

## Evidence / limits

65 new cases cover SQL/native/JSON numeric domains and mismatches, nullable/zero
values, pole metadata domains/equivalence, malformed IP and derived values,
consistent codes without compatibility promotion, genuinely unknown loaded IP,
copied-database cache/rule/CLI rejection and byte preservation, coherent fan
updates and actual engine/GUI stale-result handling in FA/EN/DE. 292 targeted
regressions pass, including prior core/IP/catalog gates and the scenario runner.
Raw logs: `/workspace/audit-evidence/device-aux-*` outside the checkout.

Source_id/FK and datasheet metadata, remaining raw attributes, broader direct-model
coercion, physical fan/capacitor/pole applicability, installed assembly IP evidence,
thermal/coordination validation, immutable transactions and independent engineering
references remain open. Structural consistency cannot certify a device or assembly.
P0 remains OPEN; no migration, dependency change, merge or release is implied.

## Stable checkpoint validation

Full suite: **1597 passed, 1 failed, 1 skipped** in 80.73 s. The inherited
`TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and Windows compiler skip remain.
New helper/test Ruff, changed legacy-file F checks, compilation and diff checks
pass; global lint/types are not claimed clean. All 30 standalone synthetic
scenario runs pass, still NOT_VERIFIED/zero independent cases. Actual GUI smoke
recalculates four feeders and 71 validation rows. Packaged CLI validates 102 devices
and previous inventories. DB SHA256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `87b584c`; prior audit units required.
Main remains untouched.
