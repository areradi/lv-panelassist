# P0 continuation — fault locations and protection settings

Starting head: `96804be`, with a clean working tree. Git read-only inspection
confirmed main still at `f4261938e1ddeba2430fa0886648792625a2ed16` and PR heads
1–4 at the expected review commits. No upstream changes needed reconciliation.
A pre-change Git bundle is retained under `/workspace/audit-backups`.

## Delivered review units

1. `fix/audit-04-network-scopes`, commit `72315be`, based on the existing fourth
   PR branch. Transformer-terminal diagnostics no longer provide a missing bus
   input. Fault locations are distinct and scoped checks reach the actual GUI,
   HTML and XLSX validation stream. [Policy and limitations](../engineering/fault_scope_policy.md).
2. `fix/audit-05-protection-settings`, based on the network branch. The cable and
   overload rules share one actual-Ir verdict; frame ratings cannot cause a
   contradictory failure. Unknown bounds/device remain missing; definite
   inequality/range violations remain errors. [Policy and limitations](../engineering/protection_setting_policy.md).

Each unit's Observed / Expected / Implementation / Tests / Evidence / Remaining
risks are recorded in the policy pages and [work register](work-items.md).
Existing PR branches and main are not modified by these new branches.

## Actual validation

- Starting targeted regressions: 12 passed.
- Network unit: 26 new cases; 388 passed, 1 existing PDF failure, 1 Windows skip
  in the full suite. Targeted network/audit checks: 38 passed. Core mypy passed.
- Setting unit: 21 new cases; latest full suite **409 passed, 1 existing PDF
  failure, 1 Windows skip**. Targeted settings/evidence checks: 59 passed.
- New test modules pass Ruff. Changed core/engine pass Ruff's F checks. Existing
  GUI unused-variable and global lint/type debt have not been labelled clean.
- Core type checking and package compile checks pass. Global Ruff/mypy outputs
  remain separate evidence files and do not establish a green CI run.
- Real GUI smoke startup/recalculation passes; a transformer-only GUI case
  confirms unknown panel Icu and visible scoped validation rows.
- No tests were newly disabled. Three unsafe network expectation tests were
  amended to require unknown bus/end values instead of fabricated values. The
  inherited PDF failure and absent `csc.exe` skip remain visible.

Raw outputs are under `evidence/*network*` and `evidence/*settings*`.
No catalog/database, requirements, lockfile or user project data was changed.
Catalog SHA-256 still equals
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.

## Gate status

P0 is still OPEN. The user has no independent engineering reference pack/reviewer
and requested explicitly unverified results. These are software-policy tests,
not independently approved IEC values, tolerances or manufacturer evidence.
Complete network/earth-loop/ADS modelling, source/topology/motor applicability,
reviewed settings/property data, thermal/busbar validation, Windows/EPLAN field
tests and all-format export acceptance remain open. No release or merge is
performed by this delivery.
