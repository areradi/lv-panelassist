# Property evidence must match its actual subject and conditions

## Observed

At `f4c36a7`, nonempty bibliographic fields could be treated as reviewed evidence
without binding the value, unit or device/operating conditions. A set of named
source buckets could promote a whole-device quality label even when the values
did not describe its attributes. Selectivity proof could ignore the source's
own restrictions or use an unrelated catalog label as its document reference.

## Expected / Implementation

- Property metadata requires a value, unit, complete source/reviewer fields and
  parseable ISO review date. Boolean measurements cannot silently become 1/0.
  Missing/incomplete declarations remain estimated.
- `PropertySource.matches()` checks exact value, unit and the complete set of
  applicability conditions. Numeric notation such as 400/400.0 is compared
  exactly using Decimal; no numerical tolerance is invented. Unknown or extra
  restrictions are not ignored, and textual identities are not fuzzy matched.
- Icu evidence must match the exact device identity/manufacturer, SQL capacity
  value, voltage, frequency and temperature. This is evaluated by the actual
  engine check, including main protection. A numeric candidate without matched
  evidence is not completed. Source matching and the actual source reference
  survive into ValidationResult and human-readable HTML/XLSX evidence rows.
- Selectivity evidence must match the exact pair/manufacturers, settings,
  voltage, frequency and temperature as well as its reported limit/unit.
  The returned reference is the matched source's document/revision/page/reviewer,
  not an arbitrary label. Invalid operating inputs are rejected. Multiple
  matching reviewed rules require reconciliation instead of choosing max(limit).
- Duplicate-rule checks distinguish explicitly different source applicability
  conditions; the final matcher still rejects overlapping applicable proofs.
- Whole-device `data_quality` remains ESTIMATED: this schema has no aggregate
  approval of every critical property. Property evidence is retained, but named
  buckets alone do not certify the device. The legacy bibliography-only
  `is_production_verified()` compatibility method cannot grant production approval.

## Tests / Evidence

`test_property_evidence_binding.py` covers mismatched values/units/identities,
missing/extra operating restrictions, review metadata, exact numeric notation,
misleading group labels, actual engine Icu checks and HTML/XLSX rows, invalid
fault magnitudes, overlapping rules and legacy bibliography. Fixtures are
explicitly synthetic; their successful matching is not a real manufacturer or
engineer sign-off. Existing synthetic approved-rule fixtures now state the
complete matching context; undocumented numeric-only Icu no longer expects PASS.

Normalized SQL Icu tests also confirm rejection of invalid values without
modifying their input files. Current full suite: 491 passed, 1 inherited PDF
failure, 1 Windows skip. Targeted checks: 120 passed. Raw `*evidence*` validation
outputs are in `docs/audit/evidence/`. Both new matching/validation modules pass
their selected mypy checks and new test modules pass Ruff.

## Remaining risks

Matching recorded declarations does not authenticate a document or the identity/
competence of its claimed reviewer. Actual manufacturer evidence and independent
human review remain prerequisites. Unsupported ranges/restrictions are
conservatively unmatched, not automatically interpreted. No aggregate device or
assembly production-approval workflow is implemented. Existing catalog records
have not acquired new evidence or been rewritten. P0 remains OPEN.
