# Explicit trip-curve identity and runtime argument domains

## Observed

Unknown series inherited DEFAULT, and absent curve parameters were replaced with
90/2/8/12 constants. Invalid runtime values could be coerced/clamped into plausible
numbers. TCC could draw a fallback curve and approximate current selectivity could
report a numerical limit for series without a corresponding curve.

## Expected / implementation

get_curve now resolves only an exact supplied series. Unknown series returns an
empty record; thermal_time_s returns None and instantaneous_band_a returns
(None, None). Explicit DEFAULT remains available as an intentionally selected,
preliminary model. Missing/invalid series identities are rejected. Runtime current
multiple and rated current must be positive, finite, non-boolean native numeric
values; strings are not coerced. Parametric arithmetic overflow/underflow and
nonfinite resulting bands fail with named validation errors rather than plausible
clipped values.

Current selectivity cannot infer a curve-based limit from either missing curve;
the existing ratio-only preliminary state remains. Engine missing-band handling
preserves missing-data trip estimates. TCC omits missing curves/bands and labels
curve unavailable in FA/EN/DE, retaining the preliminary watermark. Missing curves
are not counted as drawn approximate curves in its generic approximation note.

## Tests / evidence

44 new cases cover argument domains for known/unknown series, exact lookup,
explicit DEFAULT, invalid identities, arithmetic overflow, missing upstream/downstream
selectivity and actual project -> guarded TCC SVG in three languages. Together
with 62 structural gate cases, 106 targeted tests pass. Three existing geometry/
parametric selectivity fixtures now select DEFAULT explicitly while retaining
numerical/geometry assertions. Old unknown-series time/limit expectations now
require None/ratio-only; no test is disabled and no VERIFIED assertion is added.
Raw logs: `/workspace/audit-evidence/curve-lookup-*` outside the checkout.

## Remaining risks

Explicit DEFAULT is not manufacturer applicability evidence. Known finite curve
methods retain their existing 0.01–1000 s clamp and point endpoint behavior; valid
numerical output is still preliminary and not an independently reviewed trip time.
Tolerance, source authentication, settings, current/time range applicability and
runtime interpolation robustness beyond these checked domains remain open. TCC
is not a protection study or field-approved drawing. No database/dependency/user
data change, engineering sign-off, merge or release is implied. P0 remains OPEN.

## Stable checkpoint validation

Full suite: **1071 passed, 1 failed, 1 skipped** in 38.62 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. Validator/new test module
Ruff, changed catalog/engine/output F checks, compilation and `git diff --check`
pass. Only an explanatory test comment changed after the full run. Global lint/type
cleanliness is not claimed. Actual GUI smoke recalculates four feeders and
71 validation rows. Based on `6b5e283`; requires earlier audit units. Main untouched.
