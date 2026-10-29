# Selectivity SQL/JSON row and reference gate

## Observed / expected

Runtime SQL loading filtered on is_verified_manufacturer_rule before validation;
disabled corrupt rows were invisible. SQL identity/numeric fields were not matched
to raw JSON, and explicit parts/series could reference missing or unrelated devices.
The CLI validated only JSON rule conditions. Rule models also coerced some numeric
strings/booleans and ignored extra conditions.

Rules now require native typed values, nonblank series/reference and supplied part
IDs, and explicitly represented fields. Unknown extra conditions fail instead of
being discarded. The existing upstream minimum of zero remains valid. Optional
part/voltage/setting/source fields remain optional; absent evidence is not filled.

The shared SQL parser checks every row before applying activation flags. It checks
positive unique integer row IDs, integer 0/1 flags, SQL/JSON series/current/limit
agreement, positive finite voltage, explicit JSON voltage agreement, and compatible
total/partial labels. Both TOTAL/PARTIAL and their VERIFIED_ prefixed legacy labels
are accepted without granting reviewed status. Existing SQL 400 V defaults do not
populate missing JSON operating conditions or authenticate voltage applicability.

Non-null upstream maxima/minimum ratios are rejected explicitly as unsupported
applicability conditions: current runtime matching does not represent/enforce them.
They cannot silently narrow a source's scope while a broader rule is evaluated.
No new engineering range, ratio or capacity is invented. Future support needs
explicit modeling, matching and reviewed evidence.

Referenced series must exist in the database device inventory. Any supplied part
must exist and belong to the stated series, using exact stored identities. The
reference gate uses the full database inventory, not a project-filtered selection.
This establishes structural linkage only, not suitability of that device/pair.
Existing duplicate/conflicting condition checks still cover all rows, including
disabled rules; rules cannot be reconciled by choosing a favorable limit.

Runtime cache loading and read-only CLI use the same parser and close their SQL
connections explicitly. Engine prechecks revalidate cached rules/references against
freshly read SQL devices before calculation. Caller-modified cached device series
and project selection subsets cannot rewrite those source references. Existing
content-epoch/sidecar checks apply to cached reads. CLI adds
enabled_selectivity_rules alongside the complete inventory count. Empty inventory
is structurally allowed and supplies no coordination evidence.

Minimum synthetic CLI fixtures add the required SQL columns with no inserted
ratings/rules or changed assertions. Shared JSON diagnostics additionally reject
nontext raw_json and unexportable duplicate keys without emitting invalid text.
No migration, repair, source record edit or database write is performed.

## Evidence / limits

58 new cases cover strict model domains/extra conditions, SQL identities/flags,
numeric/text domains and mismatches, voltage/part/series references, duplicate IDs
and conditions, unsupported restrictions, validated activation filtering and
non-promotion of SQL labels. Copied-database cache/CLI/engine/GUI cases cover bad
disabled rows, stale-result preservation in FA/EN/DE, structured invalid-key errors,
byte preservation and project/caller catalog changes without false dangling references.
358 targeted regressions pass, including previous exact-evidence/ambiguity,
unknown-curve and CSV cases. Full-suite validation caught and corrected a comparison
against mutable cached devices; source linkage now uses fresh SQL rows instead.
Raw logs: `/workspace/audit-evidence/selectivity-row-*` outside the checkout.

These are structural software tests, not independent engineering cases. Source
documents, edition/pages, source applicability, current/setting ranges, validated
coordination/backup limits, labels inherited from migration, immutable transactions
and electrical review remain open. A SQL manufacturer flag, total/partial label
or catalog_reference string cannot satisfy property-evidence matching. Synthetic
evidence tests never approve the packaged rules. engineering_verification remains
NOT_VERIFIED and P0 remains OPEN. No merge or release is implied.

## Stable checkpoint validation

Full suite after the source-inventory fix: **1394 passed, 1 failed, 1 skipped**
in 63.39 s. The inherited `TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and
Windows compiler skip remain. Initial failing-run evidence is retained separately
as `selectivity-row-full-before-source-inventory-fix.txt`. No tests were disabled
or weakened. New-test Ruff, changed legacy-file F checks, compilation and diff
checks pass; global lint/types are not claimed clean. Actual GUI smoke after the
fix recalculates four feeders and 71 validation rows. Packaged CLI reports 12
total/enabled rules and previous inventories, still NOT_VERIFIED. Packaged DB
SHA256 remains `d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `968e4ba`; prior audit units required.
Main remains untouched.
