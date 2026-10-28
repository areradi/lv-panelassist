# Catalog input gates — structural scope only

## Observed / Expected

At `9e044b9`, negative catalog numbers, empty identities, duplicate in-memory
parts and mismatched SQL/JSON identities could enter device selection. Mutable
models were not revalidated as catalog snapshots. A missing database could also
trigger an implicit migration into the packaged data path.

Invalid catalog data must be rejected before project results, without silently
repairing data or interpreting structural validity as engineering approval.

## Implementation

- Nonempty normalized identities, finite nonnegative numeric attributes, and
  consistent stated setting ranges are required. Existing zero sentinels remain
  unknown/not applicable, not evidence of a physical zero rating.
- Engine construction and processing revalidate and detach catalog models.
  Duplicate part numbers cannot enter the engine. Later caller mutation cannot
  alter the retained snapshot; invalid internal mutation is rejected on process.
- Runtime and the read-only validator share SQL/JSON identity, duplicate JSON
  key, device schema and duplicate/conflicting selectivity-condition checks.
  Conflicting limits cannot be resolved by taking the largest favorable value.
- Missing catalogs fail with a recovery error; no database is generated or
  migrated automatically. Explicit migration tooling remains separate work.
- Invalid operating voltages and negative/nonfinite Icu table values are rejected;
  missing/legacy zero Icu is unknown, never an accepted positive capacity.
- `python scripts/validate_catalog.py [--db PATH]` reads only and returns nonzero
  on invalid input. Its successful structural result explicitly states
  `engineering_verification: NOT_VERIFIED`.

## Tests / Evidence

`test_catalog_input_gate.py` exercises invalid numbers, empty/duplicate identity,
mutation, missing files, wrong SQL identities, invalid JSON shapes/duplicate
keys, conflicting limits reaching process_project, and actual CLI exit status
with before/after file bytes. Previously synthetic invalid-range cases now
assert rejection before any result instead of an ERROR result after processing.

Current packaged catalog: 102 device records and 12 selectivity records pass the
specified structural checks. Full suite: 450 passed, 1 inherited PDF failure,
1 Windows compiler skip. Raw evidence is in `docs/audit/evidence/*catalog*`.
The original database hash is unchanged.

## Remaining risks

The CLI scope does not claim validation of every curve, standard, normalized
auxiliary table, property source or manufacturer reference. It is not a database
repair/migration tool or engineering sign-off. Source applicability matching and
broader schema coverage remain separate checks; P0 remains open.
