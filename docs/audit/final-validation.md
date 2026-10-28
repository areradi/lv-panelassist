# Validation of the initial audit hardening delivery

This delivery covers baseline capture and conservative P0 software guards. It is
not completion of the entire backlog, P0 engineering acceptance, or a release.
The user confirmed that independent engineering sources/reviewer are not
available and instructed that results remain unverified.

| Check | Actual outcome |
| --- | --- |
| Full pytest, `python -m pytest -q -rs --tb=short` in `.venv` | 362 passed, 1 failed, 1 skipped (364 collected) |
| Remaining failure | `TestPhase3Pdf::test_html_to_pdf_roundtrip`, same baseline browser printing limitation |
| Skip | C# macro compilation: Windows `csc.exe` absent |
| Repository Ruff | 868 findings, exit 1; baseline 882, no claim of clean lint |
| Repository mypy, `--ignore-missing-imports` | 22 errors in 8 files, exit 1; baseline 23; partial typing only |
| New modules/tests Ruff | Pass for result_contract, ip_rating, run_metadata and four new test modules |
| New modules mypy | result_contract, ip_rating and run_metadata pass with `--follow-imports=silent` |
| Compile check | `compileall` passed for package and entry points |
| GUI | Render/recalculate, four counters, no undocumented COMPLETED checks, stale input blocked; screenshot captured while running |
| Catalog preservation | Same SHA-256 as baseline; runtime write attempt rejected as readonly |
| Whitespace check | `git diff --check` passed |

Commands ran in `/workspace/lv-panelassist` with Python 3.12.14. Raw outputs and
the collected test names are in [evidence](evidence/). Baseline collection names
are retained separately. Some unsafe legacy test names/expectations were renamed
to assert the corrected behavior; none was deleted or newly disabled.

The GUI screenshot demonstrates the English Linux/Xvfb workflow. Locale key
parity and calculation/export integration were exercised for FA/EN/DE; this is
not acceptance of Persian glyph rendering, Windows RTL, 3 DPI settings or
accessibility. Initial Persian Linux screenshot rendering was incomplete and
requires separate font/RTL validation. No target Windows/EPLAN machine or
electrical reviewer was simulated.

The source archive and Git bundle in `/workspace/audit-backups` preserve the
initial state. Database hash remains:
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No catalog records, requirements, lockfiles or user project files were migrated.

The source comparison began at main SHA
`f4261938e1ddeba2430fa0886648792625a2ed16`; no completed upstream audit work was
present at baseline. Delivered/remaining topics are mapped individually in the
[verification matrix](../engineering/verification_matrix.md). Later changes to
main must be compared with this SHA before merging; no blind reset is authorized.

P1/P2/P3 and release gates remain deferred. Metadata/source hashes establish
traceability, never engineering correctness. In particular, no numerical
tolerance or manufacturer approval has been invented to make tests pass.
