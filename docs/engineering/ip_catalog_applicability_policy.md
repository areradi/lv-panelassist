# Conservative catalog IP applicability

## Observed

The legacy catalog filter compared water digits 7–9 numerically with jet/splash
categories. For example, a sole IP68 declaration could satisfy an IP65 request.
That could select an unsupported enclosure even though review unit 9 correctly
left its calculated ceiling unknown. Integrated missing-candidate tests also
revealed that EST-PANEL inherited the generic device default IP20, creating a
numerical ceiling for an enclosure with no actual IP declaration.

## Expected / implementation

Automatic IP compatibility is restricted to supported water digits 0–6. Either
side using 7–9 returns false, including exact matches: compatibility is not
established by this software policy, rather than a claim that the product cannot
meet a requirement. A separately evidenced applicability mechanism is needed for
these classes. Existing independent solid/water dimension comparison stays intact
within the supported subset. Malformed declarations remain excluded.

If no candidate remains, the existing proposed EST-PANEL now explicitly has an
empty IP rating. RULE-ENC-IP-019 and RULE-ENC-IP-020 both retain INSUFFICIENT_DATA,
and the reported IP ceiling is `?`, never the generic device default IP20.
Supported candidates remain preliminary warnings, not assembly certification.

## Tests / evidence

`tests/test_ip_catalog_applicability.py` supplies synthetic declarations only:
special category comparisons, unchanged supported cases, actual repository filter,
engine selection/fallback, and HTML/XLSX missing statuses in FA/EN/DE. The synthetic
repository property is patched per test and restored; no packaged DB is modified.
Before changes: 17 failed, 7 passed. After changes: 24 passed. No original tests
or expectations disabled or altered. Raw logs: `/workspace/audit-evidence/ip-catalog-*`.

## Remaining risks

Exact manufacturer documentation, combined ratings, accessories, mounting and
assembly tests still need independent engineering review. IPX/suffix/dual markings
are outside this parser. Conservative exclusion may omit suitable real products;
manual evidence review is required. Thermal design, other catalog selection paths
and independent reference verification remain open. P0 stays OPEN; no release or
merge is performed.

## Stable checkpoint validation

Full suite: **554 passed, 1 failed, 1 skipped** in 28.97 s. The inherited
PDF roundtrip failure and Windows compiler skip remain. GUI renders/recalculates
four feeders and 71 validation rows. New test/helper Ruff checks, changed
engine/catalog F checks, compilation and `git diff --check` pass. Global lint/type
cleanliness is not claimed. Only test import formatting changed after this run.
No database/dependency/user data changed. Based on `8a573b9`; requires earlier
audit units. Main stays untouched.
