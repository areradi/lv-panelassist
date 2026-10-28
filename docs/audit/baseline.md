# Audit baseline — 2026-10-28

Base: `f4261938e1ddeba2430fa0886648792625a2ed16`, branch
`fix/audit-and-product-hardening`. The initial working tree was clean. No
application source, tests, or catalog data changed before these checks.

## Observed

Debian 13 x86_64, Python 3.12.14, Tk 9.0, virtualenv `.venv`.
The existing HTTPS Git proxy can read the repository. No new credentials were
requested. Current main is compared with the base before publication.

| Command (repository root) | Actual result |
| --- | --- |
| `.venv/bin/python -m pip install -r requirements-dev.txt` | exit 0 |
| `.venv/bin/python -m pytest -q -rs --tb=short` | exit 1: 272 passed, 1 failed, 1 skipped |
| `.venv/bin/python -m pytest --collect-only -q` | 274 tests collected; names retained |
| `.venv/bin/ruff check . --output-format concise` | exit 1: 882 findings, no autofix applied |
| `.venv/bin/mypy lv_assist --ignore-missing-imports` | exit 1: 23 errors in 8 files; partial checking, not strict typing |
| `bash /workspace/.cloud-setup/start.sh --smoke` | exit 0: GUI rendered and recalculated four demo feeders, 39 validation rows |
| `python -m compileall -q lv_assist main.py wizard_app.py tcc_analyzer.py` (venv Python) | exit 0 |
| SQLite `PRAGMA integrity_check` (read-only connection) | `ok` |

Raw output, installed versions, collection names, and a screenshot of the running
GUI are in [evidence](evidence/). GUI execution uses a local Xvfb display; this is
not a Windows, DPI, accessibility, or human usability acceptance test.

## Expected

Calculations must distinguish missing evidence from a successful check. All
existing tests must actually execute; changed safety expectations need explicit
regression tests. A passing software test is not independent engineering sign-off.

## Implementation

No computational changes in the baseline commit. Before editing, created a Git
bundle and source archive under `/workspace/audit-backups` (outside the checkout).
The archive excludes installed dependencies, Git metadata, and generated caches;
the bundle retains Git history. No user files were present as untracked changes.
Shipped catalog SHA-256:
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.

## Tests / Evidence

Failure: `TestPhase3Pdf::test_html_to_pdf_roundtrip`. Chromium is installed, but
printing fails in the command sandbox and times out after 120 s with broader
process permissions. Direct printing of `about:blank` also fails, independently
of repository HTML. System font configuration, session D-Bus, and an isolated
diagnostic run without Chromium's internal sandbox did not restore printing.
The root cause is unresolved; PDF readiness is not claimed.

Skip: C# macro compilation requires Windows `csc.exe`, absent here. No assertion
was disabled or replaced. Ruff and mypy findings are baseline debt, not successes.

## Remaining risks

No independent numerical reference cases, manufacturer evidence, electrical
engineer approval, Windows 11 clean installation, or actual EPLAN 2024 import has
been performed. GUI and engineering outputs may contain false verification
claims in the baseline. P0 must be addressed before UX/commercial work.

Backups and the installed environment are local artifacts, not remote releases.
Changes will be kept in separate reviewable commits; GitHub PR publication must
be reported separately from local implementation.
