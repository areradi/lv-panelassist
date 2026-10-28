# PDF publication integrity and failure reasons

## Observed

The PDF exporter reused one browser profile and printed directly over the chosen
destination. Its success check only required a nonempty file: a previous PDF could
be accepted even if this browser attempt wrote nothing. Every GUI failure claimed
Edge/Chrome was missing, including timeouts and write errors. The GUI also reused
a fixed temporary HTML filename containing project data.

## Implementation

The bool API remains compatible. A frozen PdfExportResult exposes success/reason:
invalid_input, missing_browser, timeout, browser_failed, invalid_pdf, write_failed,
or ok. Each attempt uses a unique temporary folder on the destination filesystem,
an isolated browser profile and a private output path. Only a newly generated
file starting with %PDF- and containing a trailing %%EOF marker is published via
os.replace. A failed attempt leaves an existing destination unchanged. This is a
basic format/truncation guard, not full PDF parsing or visual validation.

GUI PDF export uses its own temporary HTML directory and translated reason-specific
messages in FA/EN/DE. It removes the directory after the attempt. The compatibility
API used by bundle export retains its bool behavior; bundle-level omission/error
manifests remain future work. No dependency or browser sandbox setting changed.

## Evidence / tests

A real Chromium invocation on a minimal local HTML, with a fresh profile and a
15-second diagnostic limit, timed out. stderr reported D-Bus/fontconfig/Mojo
messages; these messages do not establish a specific root cause. This reproduces
the browser-printing failure independently of the engineering HTML, but does not
prove that report layout is correct. Real rendering is still unaccepted here.

Fifteen new tests simulate browser outcomes and cover missing/empty/non-PDF/
truncated output, timeout, launch/nonzero-exit failures, missing/conflicting input,
missing browser, atomic-publication error, old-file preservation, temporary/profile
isolation, compatibility API, and actual GUI action message/HTML cleanup in three
languages. Synthetic PDF bytes are integrity fixtures, not rendering evidence.
Raw outputs: `/workspace/audit-evidence/pdf-stage/` outside the checkout.

## Remaining risks

The inherited real PDF roundtrip remains an acceptance requirement, not a skipped
test. Actual Windows Edge/Chrome printing, Persian glyph/RTL/layout, concurrent
browser processes and OS-specific file-lock/permission behavior need field tests.
Timeout kills the subprocess through Python's existing subprocess.run behavior;
complete descendant-process cleanup is not established on all platforms. Temporary
cleanup is best-effort where the browser locks files. P0 engineering verification
remains OPEN; this work supplies no independent numerical or assembly approval.

## Stable checkpoint validation

Full suite: **577 passed, 1 failed, 1 skipped** in 22.27 s. The existing real
PDF roundtrip failure and Windows compiler skip remain. New test module passes
Ruff; outputs.py F checks, compilation and `git diff --check` pass. Global lint/type
cleanliness is not claimed. Actual GUI smoke recalculates four feeders and
71 validation rows. No database/dependency/user-data changes. Based on `19f6cb9`;
requires previous audit units. Main stays untouched. Successful real PDF generation
is explicitly not claimed by this checkpoint.
