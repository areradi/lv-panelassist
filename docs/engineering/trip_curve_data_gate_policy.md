# Auxiliary trip-curve structural gate

## Observed

Trip curves were loaded with unrestricted json.loads into a mutable dictionary.
Malformed numbers/shapes/points could reach arithmetic, duplicate JSON keys or SQL
identities could silently replace data, and selected cached curves were returned
by reference. Selectivity rule free text did not inherit the new text policy.

## Expected / implementation

Curve loading now uses the duplicate-key/object JSON parser and rejects duplicate
curve identities. The structural validator requires positive finite non-boolean
numeric instantaneous multipliers with min <= max; parametric k/alpha when needed;
and, when points are supplied, at least two positive finite current/time pairs
with strictly increasing current multiples at the precision used by interpolation. Supplied optional parametric values
are checked even for point curves. DATASHEET_POINTS requires points and a nonblank
reference, but neither the flag nor bibliography establishes actual source review.
Free text uses the XML/UTF-8 policy. Error messages are localized while curve IDs
and field paths remain literal ASCII where supplied.

The engine revalidates the loaded curve map before arithmetic, including a mutated
cache. Non-dictionary map shapes also produce a named validation error at engine
and standalone lookup boundaries, rather than an AttributeError or silent fallback. Selected TripCurveRepository lookups also revalidate and return detached
copies. The read-only catalog CLI now checks/counts trip curves alongside devices
and selectivity rules, still declaring engineering_verification NOT_VERIFIED.
SelectivityRuleRecord inherits the shared text policy and existing rule snapshot
revalidation applies it before matching.

## Tests / evidence

62 new cases cover missing/invalid finite domains, bool/numeric-string rejection,
point shape/order/duplicates/ranges, required source shape, invalid text, JSON/
identity duplicates, cache detachment/mutation, actual pre-arithmetic rejection,
read-only CLI success/failure against a copied database, rule text mutation and
GUI prior-result/stale/localized error handling. 138 targeted cases include prior
catalog checks and the 20 ms regression. The latter now supplies explicit valid
curve parameters instead of relying on hidden field defaults; its missing-curve/
estimate assertions are unchanged. The old minimal CLI fixture adds the newly
required trip_curves table, without inventing engineering data in it.
Raw logs: `/workspace/audit-evidence/curve-gate-*` outside the checkout.

## Remaining risks

This is a consumed-field/domain gate, not a full auxiliary catalog migration or
manufacturer schema/certification. It does not authenticate datasheets/reviewers,
validate time tolerance/monotonicity, prove protection coordination or change
existing interpolation/clamping/default behavior. Standalone unknown-series
fallbacks, runtime argument ranges and complete auxiliary-cache invalidation after
external file changes still require separate treatment. Engine file hashes remain
in use; no catalog database was modified or repaired. Other raw auxiliary tables
and independent reference/reviewer remain open. P0 stays OPEN; no merge/release.

## Stable checkpoint validation

Completed the pending review unit on branch fix/audit-27-trip-curve-data-gate,
based on f363e13; previously committed standalone export guards were retained.
Full suite: **1027 passed, 1 failed, 1 skipped** in 41.04 s. The inherited PDF
roundtrip failure and Windows compiler skip remain. After isolating the malformed
map-cache fixture from device-cache initialization, 138 targeted cases passed again.
New validator/test Ruff, changed catalog/engine/model F checks, compilation and
`git diff --check` pass. Global lint/type cleanliness is not claimed. Real GUI smoke
recalculates four feeders and 71 validation rows. CLI validates devices/rules/curves
read-only. Packaged DB SHA-256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependency or user-data change; main untouched. P0 remains OPEN.
