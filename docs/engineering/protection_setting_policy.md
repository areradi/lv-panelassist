# Actual settings and cable coordination — software policy

## Observed

At `72315be`, a synthetic adjustable breaker with frame In=100 A, actual
Ir=50 A, stated range 40..100 A and cable Iz=57 A produced contradictory
results: RULE-CABLE-OVERLOAD WARNING and RULE-CABLE-009 ERROR. The legacy rule
still compared frame In to Iz. This was a software-policy reproducer, not a
manufacturer reference case or a newly approved ampacity value.

## Expected / Implementation

- The actual setting, rather than the frame rating, is used for the specified
  adjustable-device inequalities `Ib <= Ir <= Iz` and `I2 <= 1.45 Iz`.
- RULE-CABLE-009 and the structured overload check use the same CheckResult.
  The report/UI evidence exposes Ib, actual and requested Ir, Iz, I2, frame and
  stated setting range in A. Unknown bounds are None/`?`, not zero-amp settings.
- Missing Ir, I2, applicable Iz, an adjustable range, or the device itself cannot
  produce a completed verdict. A fully supplied numerical candidate remains
  WARNING because manufacturer evidence/applicability is still unreviewed.
- A known inequality violation remains ERROR even if other data are missing.
  Specifically Ib > Iz is impossible for every Ir and must not be hidden by
  unknown settings. Negative/reversed known ranges, settings outside stated
  bounds/frame and an attempted override of a fixed device are flagged.
- Cable geometry proposals use a stated adjustable Ir. If unknown, the known
  frame may be used conservatively for the proposal, with an explicit assumption;
  it does not become an inferred setting or a successful overload check.
- This does not introduce a reviewed device-selection method. The requested
  setting is checked against the proposed device; it is not silently presumed
  applicable to every device or manufacturer. No catalog data is rewritten.

## Tests / Evidence

`tests/test_protection_setting_coordination.py` uses explicitly synthetic device
and setting cases, including the original contradiction, missing data, bounds,
fixed MCB, no protection, actual setting above Iz, Ib above Iz, I2 violation,
geometry proposals and invalid direct settings. Actual engine checks and
HTML/XLSX rows are compared; standalone helper tests alone are not acceptance.

Full pytest and GUI results are retained under
`docs/audit/evidence/*settings*`. These tests assert supplied inequalities and
data-handling policy, not independent numerical engineering references. The
existing PDF failure/Windows-only skip remain recorded.

## Remaining risks

The factor 1.45 and protection/cable applicability still require the appropriate
device/standard evidence and engineering review. Exact property provenance,
settings tied to an installed device, independent references and the UI/import
workflow for expert settings are not certified by these policy tests. No
construction or engineering acceptance is claimed; P0 remains open.
