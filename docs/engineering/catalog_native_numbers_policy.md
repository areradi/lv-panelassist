# Native device numeric inputs

## Observed / expected

CatalogDevice accepted boolean/numeric-text input through Pydantic conversion.
For example, True could become a current/loss of 1 and "7" could become 7.0.
Earlier SQL/JSON gates checked selected duplicate fields, but direct model/API
construction and raw-only coil/SPD attributes could still accept these conversions.

All 24 current float-valued device attributes now use a before-validation native
number gate. Values must be finite Python int/float values, excluding bool. Numeric
text, bytes, Decimal, null and nonfinite/overflowing values fail with a named field
error. The gate is applied according to declared float fields, without imposing
strict handling on unrelated strings, enums or nested evidence models.

Existing integer/float inputs remain accepted and normalized by the model. Zero
unknown/not-applicable sentinels and defaults remain intact. Existing nonnegative
and min/max setting checks still apply; no new physical range, ratio, tolerance or
manufacturer-specific numerical limit is invented. This does not make every
finite nonnegative value applicable to every device or duty.

The same model boundary covers dictionary/JSON construction, SQL row loading and
the existing detached snapshot revalidation in validated_devices/EngineeringEngine.
CatalogDevice model_copy/update and later assignment remain mutable/bypass paths;
revalidation rejects their invalid numeric values before engine construction or
recalculation. It does not claim frozen device objects or assignment-time validation.
GUI keeps prior results as stale and displays the field error after failed recalculation.

SQL model-validation errors are wrapped as CatalogValidationError (a ValueError)
while preserving the original cause and diagnostic. Existing row/API assertions
therefore retain the catalog error contract when malformed raw numeric fields are
rejected earlier at the model boundary. Raw scalar strings/metadata and exact
property evidence matching retain their established behavior. No packaged source
record, migration, calculation formula or project/feeder input parser is changed.

## Evidence / limits

66 new cases cover all 24 numeric attributes for bool/text rejection, additional
null/bytes/Decimal/nonfinite/overflow domains, supported native values and zero
sentinels, JSON/enum/text compatibility, unvalidated model copies, actual copied
SQL/CLI rejection for raw-only coil/SPD attributes with byte preservation, and
actual pre-arithmetic engine/GUI rejection in FA/EN/DE. Expected serializer warnings
from string-mutated snapshots are explicitly captured; validation assertions remain
active. A new warning-expectation fixture was corrected for bool serialization,
which does not emit that string warning; the rejection checks were retained.
392 targeted regressions pass. Raw logs: `/workspace/audit-evidence/native-catalog-*`.

These are software boundary tests, not independent engineering numerical cases.
Physical/device-specific bounds, authenticated source values, settings and duty,
broader project/import input domains, unknown extra attributes, mutable retained
objects/transactions and electrical review remain separate work. Effective whole
device quality stays ESTIMATED and engineering verification remains NOT_VERIFIED.
P0 remains OPEN; no dependency, merge or release is introduced.

## Stable checkpoint validation

Full suite: **1707 passed, 1 failed, 1 skipped** in 161.33 s. The inherited
`TestPhase3Pdf.test_html_to_pdf_roundtrip` failure and Windows compiler skip remain.
New-test Ruff, changed legacy-file F checks, compilation and diff checks pass;
global lint/types are not claimed clean. All 30 standalone synthetic scenario
runs pass, still NOT_VERIFIED/zero independent cases. Actual GUI smoke recalculates
four feeders and 71 validation rows. Packaged CLI checks 102 devices and previous
inventories; DB SHA256 remains
`d0582b46e6a216fc6206a97baa7fcaaaaeb38e0faeacc99cf9931981a09acfa7`.
No dependencies/user data changed. Based on `c70624c`; prior audit units required.
Main remains untouched.
