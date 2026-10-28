# Fault locations and incomplete network data

This is a software safety policy, not a reviewed IEC 60909 calculation method.
The user has requested unverified status until independent evidence is available.

## Observed

At `96804be`, `_resolve_ik()` treated a transformer-terminal estimate as the
panel-bus input when `prospective_ik_ka` was blank. The diagnostic helper also
assumed source R/X=0.3, copper resistivity/reactance, hot-conductor factor 1.5,
and a PE return section equal to phase when absent. Those assumptions generated
apparent bus/end/earth-fault values from incomplete data. Warning labels alone
did not stop those values being used at the wrong installation location.

## Expected / Implementation

- The existing `prospective_ik_ka` input denotes the network-source 3P
  contribution **at the panel bus**, before the separate preliminary motor
  contribution. The input template explains this in FA/EN/DE. A known total
  including motors must not be entered as that network-only contribution;
  full source/topology modelling remains open.
- Transformer-terminal diagnostic, panel bus, feeder start, 3P feeder end and
  L-PE feeder end have separate values and structured checks. Panel/feeder
  installation checks consume the same motor-adjusted bus value already used by
  the engine, when that network-source bus input is known. The feeder protection
  is assumed to be connected directly at that same bus, not behind an unmodelled
  intervening impedance.
- Transformer data alone leave the bus unknown. Icu, bus withstand, starting
  voltage dip and motor-total checks cannot borrow the transformer diagnostic.
- Length/section alone do not determine complex network or earth-loop
  impedance. End-fault results remain None/INSUFFICIENT_DATA; there is no copper,
  R/X, return-path or temperature fallback. The legacy helper arguments remain
  accepted without fabricating an impedance model.
- Explicit invalid non-positive/non-finite inputs yield ERROR and no numerical
  results. Missing data yield INSUFFICIENT_DATA; supplied or diagnostic values
  remain WARNING, never COMPLETED.
- `ShortCircuitProfile.checks` are adapted into the actual ValidationResult
  stream used by the GUI log, HTML and XLSX. The summary also retains its typed
  profile. No independent GUI or exporter fault solver was introduced.

The inherited ideal transformer-terminal diagnostic is now implemented once:

`Ik_kA = c_max * S_kVA / (sqrt(3) * U_LL_V * (uk_percent / 100))`.

Its inputs, kA unit, assumptions and method are recorded in CheckResult. It
ignores upstream impedance and transformer tolerances. `c_max=1.05` is an
inherited default, not newly reviewed source evidence. The old scalar engine
shortcut used a different factor; that shortcut is no longer used for bus
checks. No reference value or numerical tolerance has been approved here.

## Tests / Evidence

`tests/test_network_fault_scopes.py` covers real engine processing for TN-S,
TN-C-S, TT, IT, Cu/Al, explicit bus vs transformer-only input, motor-adjusted
comparison consistency, missing complex impedances, invalid numbers and the
three output locales. The old tests expecting invented positive end-fault
numbers now assert explicit unknown values; no test was disabled.

The network delivery records targeted/full pytest output, core mypy output and
GUI smoke output under `docs/audit/evidence/*network*`. The pre-existing PDF
failure and absent Windows C# compiler remain separate limitations.

## Remaining risks

No complete source/incomer/cable/earth-loop solver or numerical reference pack
has been independently validated. Earth-fault disconnect time, material and
temperature applicability, motor coefficients, protective-device location and
source topology require engineering review. The transformer diagnostic must
not be used for device selection or construction. The P0 engineering gate
remains open.
