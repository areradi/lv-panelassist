# Datasheet source record and device-link gate

## Observed / expected

Device loading did not read the source table or check source_id links. Invalid
source metadata, duplicate source IDs on weak schemas and dangling links could
therefore accompany successful device/rule/CLI validation. A generic source label
could also be mistaken for reviewed evidence despite having no exact property proof.

The shared source parser now enumerates every record, including unused sources.
Source IDs must be nonblank exportable strings without surrounding whitespace,
and duplicates fail even when values agree. Manufacturer/document_ref must be
nonblank exportable text. Revision remains optional text/null (including existing
empty/unknown strings); it is neither synthesized nor treated as an authenticated
edition. Coarse quality labels follow the existing SQL domain: REAL_VERIFIED,
ESTIMATED or UNVERIFIED. No label alone supplies a document, reviewer or approval.

Device SQL source_id may be null, meaning no link is known. Any non-null ID must
be structurally valid and refer to an exact existing source ID. Optional raw JSON
source_id must agree with SQL, including explicit null. Other free-text references
such as datasheet_ref/source_ref are not guessed to be foreign-key identities.
Direct row checks default to an empty known-source set, so they cannot silently
accept non-null IDs without a supplied validated source inventory.

Runtime device reads, selectivity source-inventory reads and read-only CLI use
the same parser/link checks. They read sources and device rows through the same
connection, with explicit connection closure and existing cache content-epoch/
sidecar safeguards. Every source row is checked before returning devices, even
when it has no current-project link. A failed reload never returns old cached
devices as a substitute. No foreign-key enforcement setting is changed and no
record is repaired or migrated by validation.

CLI adds datasheet_sources and device_source_links counts and describes the
expanded structural scope. Empty source inventory is structurally allowed only
when device links are absent; this is not completeness or source approval.
Successful results continue to say engineering_verification NOT_VERIFIED.

The packaged table currently contains two legacy generic buckets linked by all
102 devices (73 unspecified JSON and 29 legacy "verified catalog" labels).
These records are preserved as metadata. Source manufacturer strings are not
assumed to identify an exact part's maker, and source/device coarse quality flags
are not promoted into per-property proof. Every effective whole-device quality
still becomes ESTIMATED under the existing model contract. Actual property-value/
unit/subject/condition/reviewer matching remains a separate requirement.

Minimal prior CLI fixtures add an empty required source table and nullable link
column; prior direct row fixtures explicitly supply an absent link. Their previous
assertions remain active and no synthetic source/evidence is inserted for them.

## Evidence / limits

44 new cases cover metadata domains/text/duplicates, optional multilingual revision
preservation, non-promotion of all three source quality labels, exact/null/JSON
links, whole-inventory unused corruption and copied-DB cache/rule rejection,
weak-schema duplicate IDs, missing tables, actual CLI counts/errors/byte preservation,
empty inventories and actual engine/GUI stale-result handling in FA/EN/DE.
285 targeted regressions pass. Raw logs: `/workspace/audit-evidence/datasheet-*`.

These are source-structure/software policy checks, not authenticated manufacturer
documents or independently reviewed engineering cases. Exact edition/page/part
applicability, physical values/tolerances, evidence ingestion/publishing, broader
raw attributes, immutable transactions and independent electrical review remain
open. Generic bucket membership cannot close P0 or certify a device/assembly.
No dependency, packaged database, user data, merge or release change is implied.

## Stable checkpoint validation

The cloud connection recovered before coding; the prior stable branch/clean
checkout was confirmed at `be2953c`. Full suite: **1641 passed, 1 failed, 1 skipped**
in 139.91 s. The inherited `TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and
Windows compiler skip remain. New helper/test Ruff, changed legacy-file F checks,
compilation and diff checks pass; global lint/types are not claimed clean. All
30 standalone synthetic scenario runs pass, still NOT_VERIFIED/zero independent
cases. Actual GUI smoke recalculates four feeders and 71 validation rows. Packaged
CLI reports two source records and 102 valid structural links; DB SHA256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
Prior audit units are required. Main remains untouched.
