# Component IP ceilings remain unverified

## Observed

The panel path assigned IP54 whenever a selected filter fan accompanied a target
IP numerically >= 55. It ignored the selected fan's actual rating, invented IP54
for unknown ratings, and missed lower targets. Without a fan it copied the target
even if the proposed enclosure had no recorded IP. Report labels called this
an effective IP, implying more than component declarations can establish.

## Expected / implementation

The proposal now computes a component-wise ceiling from target, actual selected
enclosure, and actual selected fan (when installed). Missing or malformed ratings
produce `?` and INSUFFICIENT_DATA. A known ceiling produces WARNING, including
when it equals the target. Input ratings and method are in the validation stream.
No component ceiling certifies an assembly. The existing summary field is retained
for compatibility; HTML/XLSX label it as an unverified upper bound, including when
unchanged from target. FA/EN/DE labels and installation-review guidance are supplied.

This ceiling helper supports water digits 0–6 only. Digits 7–9 require distinct
applicability evidence and return unknown, rather than an ordinal comparison.
It does not change the older catalog `ip_meets` filter; that filter alone cannot
establish installed assembly IP. In particular, a catalog candidate with unsupported
water digits cannot produce a known ceiling through this calculation.

## Tests / evidence

`tests/test_enclosure_ip_bounds.py` uses synthetic declared component ratings:
independent dimensions, fan lower/higher than target, lower targets, missing fan
rating, malformed/unsupported water classes, natural ventilation, and missing
body rating. Actual engine -> HTML/XLSX runs in FA/EN/DE verify labels and statuses.
No assembly test, manufacturer document or independent reference is simulated.
Raw test outputs are under `/workspace/audit-evidence/ip-*` outside the checkout.

## Remaining risks

Recorded component IP does not validate openings, seals, mounting instructions,
accessories, certification or assembly tests. Those require exact manufacturer
sources, conditions and an electrical reviewer. Thermal/airflow and component
selection remain preliminary. P0 stays OPEN. No merge or release is performed.

## Stable checkpoint validation

- New cases: **27 passed**. Full suite: **530 passed, 1 failed, 1 skipped**
  in 21.08 s. The inherited PDF roundtrip failure and Windows compiler skip
  remain; no test disabled or existing expectations changed.
- Real GUI startup/recalculation: four feeders, 71 validation results. A new
  virtual display was used because the previous display had a stale lock.
- Ruff passes for the ceiling helper/new test module and F checks for changed
  engine/exporters. Compilation and `git diff --check` pass. Global lint/type
  debt remains outside this checkpoint.
- No database, dependencies or user data changes. Based on `a74398f`, requiring
  previous audit units. Main remains untouched.

The older catalog filter and the EST-PANEL default-IP limitation described above
are subsequently addressed by [review unit 10](ip_catalog_applicability_policy.md).
