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
| Clause 10 checklist | 13 evidence rows including continuity; no unevidenced assembly PASS | Demo + HTML/XLSX integration; actual test evidence/reviewer absent |
| Cable ampacity | Exact combination lookup; unsupported Al/XLPE/method/1P table -> None | Synthetic scope tests; authenticated ampacity sources not supplied |
| Cable/protection coordination | Actual Ir/I2 required; one verdict replaces the contradictory frame-rating comparison; Ib > Iz remains ERROR with unknown Ir; missing range/device cannot pass | `test_protection_setting_coordination.py`; [setting policy](protection_setting_policy.md); manufacturer/applicability evidence and installed-setting verification still open |
| Earthing systems | Unsupported loop/ADS scope explicitly unverified for TN-S/TN-C-S/TT/IT | Validated TN/TT/IT modelling and independent references still required |
| Trip/motor coordination | Missing curve unknown; known approximate curve/20 ms explicitly estimated | Type 1/2, VFD/soft starter, exact settings/evidence remain open |
| Selectivity / cascading | Exact parts/voltage/settings/review required; ratio never definite proof/disproof | Synthetic matching tests; no real manufacturer tables reviewed; backup separate and unimplemented |
| Property provenance | Exact value/unit/subject/conditions matching used in engine Icu and selectivity; named buckets cannot promote whole device; invalid/duplicate catalog input rejected before results | `test_catalog_input_gate.py`, `test_property_evidence_binding.py`; [property policy](property_evidence_policy.md), [catalog policy](catalog_input_policy.md); real evidence, aggregate review and complete import/publish pipeline still absent |
| IP | Solid/water digits compared separately; assembly Clause 10 unverified | Dimension comparisons; fan/gland/assembly evidence still absent |
| Busbar/thermal | Existing calculations retained; not assembly proof in design checklist | Formula/conditions/manufacturer review and validation remain open |
| Input validity | Finite Pydantic data, whitespace IDs, 1P/3P, unique/nonempty feeder set, revalidation | Invalid/duplicate/mutated-input tests; full overflow and all importer validation still open |
| Independent references | No invented results or numerical tolerances | All requested independent reference acceptance is BLOCKED |
| UI/report status | Four counters, severity order, proposed BOM, preliminary HTML/XLSX, missing data preserved | GUI smoke + locale/export integration; immutable export context and all format parity remain open |

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
