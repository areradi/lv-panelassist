# P0 verification matrix — preliminary

No row below constitutes an independently validated engineering formula or
approval. On 2026-10-28 the user confirmed that independent sources/reviewer are
not currently available and requested that unverified status be retained.

| P0 topic | Software behavior delivered | Evidence / open acceptance |
| --- | --- | --- |
| Real engine integration | Typed trip, fault-profile and check results returned by actual feeder processing | `test_p0_engine_path.py`; legacy checks not all migrated |
| Trip time / adiabatic domain | No clipping to 5 s, no unknown-time substitution; >5 s outside method | Boundary policy tests; k and curve applicability remain unreviewed |
| L-PE / hidden fault assumptions | No 10 kA or half-bus current; PE None / INSUFFICIENT_DATA | All four earth systems x three locales; physical model not implemented |
| Network fault scopes | Transformer diagnostic cannot supply missing panel bus; explicit bus preserved, end/earth-fault values stay unknown without complex impedance data; scoped checks reach GUI/HTML/XLSX | `test_network_fault_scopes.py`; [scope policy](fault_scope_policy.md); reviewed source/route solver and independent cases still needed |
| Icu/Ics | Exact voltage lookup; unknowns not passed, main and feeder checks; device remains proposed | Synthetic comparison cases; exact property/manufacturer and Ics policy incomplete |
| Clause 10 checklist | 13 evidence rows including continuity; source/document/reviewer/date displayed; no unevidenced assembly PASS; linked actual ERROR remains FAIL | Demo + HTML/XLSX integration and actual busbar overload regression; actual test evidence/reviewer absent |
| Cable ampacity | Exact combination lookup; unsupported Al/XLPE/method/1P table -> None | Synthetic scope tests; authenticated ampacity sources not supplied |
| Cable/protection coordination | Actual Ir/I2 required; one verdict replaces the contradictory frame-rating comparison; Ib > Iz remains ERROR with unknown Ir; missing range/device cannot pass | `test_protection_setting_coordination.py`; [setting policy](protection_setting_policy.md); manufacturer/applicability evidence and installed-setting verification still open |
| Earthing systems | Unsupported loop/ADS scope explicitly unverified for TN-S/TN-C-S/TT/IT | Validated TN/TT/IT modelling and independent references still required |
| Trip/motor coordination | Missing curve unknown; known approximate curve/20 ms explicitly estimated | Type 1/2, VFD/soft starter, exact settings/evidence remain open |
| Selectivity / cascading | Exact parts/voltage/settings/review required; ratio never definite proof/disproof | Synthetic matching tests; no real manufacturer tables reviewed; backup separate and unimplemented |
| Property provenance | Exact value/unit/subject/conditions matching used in engine Icu and selectivity; named buckets cannot promote whole device; invalid/duplicate catalog input rejected before results | `test_catalog_input_gate.py`, `test_property_evidence_binding.py`; [property policy](property_evidence_policy.md), [catalog policy](catalog_input_policy.md); real evidence, aggregate review and complete import/publish pipeline still absent |
| IP | Solid/water digits compared separately; assembly Clause 10 unverified | Dimension comparisons; fan/gland/assembly evidence still absent |
| Busbar/thermal | Existing calculations retained; not assembly proof in design checklist | Formula/conditions/manufacturer review and validation remain open |
| Input validity | Native finite project/feeder numbers and booleans, explicit spreadsheet conversion without count truncation, NaN/Inf clipboard rejection, whitespace IDs, 1P/3P, shared unique/nonempty input validation, helper overflow/type guards and atomic invalid-import GUI handling | Invalid/duplicate/mutated-input, actual workbook/state and helper tests; physical model/domain acceptance and later editable import preview remain separate |
| Independent references | No invented results or tolerances; read-only supplied-reference comparison with explicit metadata/tolerances and a ten-case pending inventory | All requested independent reference acceptance is BLOCKED; the comparison tool does not authenticate supplied claims |
| Reproducible software scenarios | Ten synthetic policy cases across EN/FA/DE, engine/HTML/XLSX validation parity and explicit difference/error JSON | [Runner policy](software_scenario_runner_policy.md); zero independent reference cases; does not change the blocked engineering acceptance above |
| UI/report status | Four counters, severity order, proposed BOM, preliminary HTML/XLSX/PDF, missing data preserved; exact-voltage Icu, scoped bus, frozen run/catalog/language context and current-run output guards including IEC preview paths; all-format status/run notices | Actual locale bundles/PDF extraction/GUI smoke and source-race tests; source authenticity, independent physical acceptance and real Windows/EPLAN rendering/import remain open |

Remaining work is grouped with explicit closure requirements in the
[P0 acceptance register](../audit/p0_remaining_acceptance.md). Review-unit counts
must not be read as a P0 completion percentage or as independent reference cases.
Current software evidence is in the [unit 43 delivery report](../audit/p0_software_delivery.md).

## Required independent reference pack (not executed)

| Case | Required independent evidence |
| --- | --- |
| 15 kW DOL | Motor/starting data, cable reference, actual protection curve/settings |
| 37 kW VFD | Drive input/overload/short-circuit manufacturer coordination |
| Distribution feeder | Network source/route, protection settings and cable reference |
| 1P lighting | Explicit L-N voltage, loaded conductor table, neutral/RCD applicability |
| TT/RCD | Earth electrodes/loop, RCD characteristics, permissible disconnection scope |
| 200 m feeder | Material/sections/temperature, source/return-path impedance and voltage-drop reference |
| Missing Ik | Policy case: no PE/short-circuit verification; not a numerical reference |
| Motor contribution | Actual connected motors, contribution assumptions, independent fault calculation |
| MCCB derating | Exact part number and manufacturer temperature/settings data |
| IP enclosure | Enclosure + fan/filter/gland arrangement and assembly test evidence |

For each numerical case the reviewer must provide formula, units, assumptions,
scope, source document/revision/page/table, independently obtained expected
values, allowed tolerance with rationale, name and approval date. Software
policy tests intentionally contain no invented numerical reference tolerances.
The existing tests with numerical constants remain regression checks, not a
signed IEC reference pack. No beta, construction, EPLAN import-ready, or release
acceptance gate has been closed.
