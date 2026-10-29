"""Immutable run identity. Hashes establish traceability, not engineering validity."""

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from lv_assist.registry_validation import registry_rows

ENGINE_VERSION = "audit-p0.1"


class RunMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_revision: int
    calculation_timestamp: str
    engine_version: str
    engine_source_hash: str
    catalog_version: str
    catalog_selection_hash: str
    standards_registry_version: str
    input_fingerprint: str
    input_snapshot_json: str
    assumptions: tuple[str, ...]
    result_fingerprint: str | None = None


def canonical_inputs(project: BaseModel, feeders: Sequence[BaseModel]) -> str:
    return json.dumps({"project": project.model_dump(mode="json"),
                       "feeders": [feeder.model_dump(mode="json") for feeder in feeders]},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def input_fingerprint(project: BaseModel, feeders: Sequence[BaseModel]) -> str:
    return hashlib.sha256(canonical_inputs(project, feeders).encode()).hexdigest()


def result_fingerprint(outputs: Sequence[BaseModel], summary: BaseModel,
                       checks: Sequence[BaseModel]) -> str:
    """Bind derived data/checks to a run; this is not an authenticated signature."""
    payload = {"feeders": [row.model_dump(mode="json", exclude={"run_metadata"}) for row in outputs],
               "summary": summary.model_dump(mode="json", exclude={"run_metadata"}),
               "checks": [row.model_dump(mode="json") for row in checks]}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def catalog_file_hash(catalog_path: Path) -> str:
    # A main-file hash cannot identify uncheckpointed SQLite sidecar contents.
    from lv_assist.i18n import tr

    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(catalog_path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ValueError(tr("audit_catalog_unstable"))
    return hashlib.sha256(catalog_path.read_bytes()).hexdigest()


def selection_hash(catalog: Sequence[BaseModel]) -> str:
    data = json.dumps([device.model_dump(mode="json") for device in catalog], sort_keys=True,
                      separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def engine_source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


LOADED_SOURCE_HASH = engine_source_hash()


def registry_hash(catalog_path: Path) -> str:
    before_hash = catalog_file_hash(catalog_path)
    with closing(sqlite3.connect(catalog_path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT standard_id, raw_json FROM standards_registry ORDER BY standard_id").fetchall()
    registry_rows(rows)
    if catalog_file_hash(catalog_path) != before_hash:
        from lv_assist.i18n import tr

        raise ValueError(tr("audit_catalog_unstable"))
    raw_rows = [(row['standard_id'], row['raw_json']) for row in rows]
    return hashlib.sha256(json.dumps(raw_rows, separators=(",", ":")).encode()).hexdigest()


def create_run_metadata(project: BaseModel, feeders: Sequence[BaseModel], catalog_path: Path,
                        project_revision: int, assumptions: Sequence[str], catalog: Sequence[BaseModel]) -> RunMetadata:
    if engine_source_hash() != LOADED_SOURCE_HASH:
        raise ValueError("Calculation source changed since startup; restart the application before recalculating.")
    snapshot = canonical_inputs(project, feeders)
    return RunMetadata(
        project_revision=project_revision,
        calculation_timestamp=datetime.now(UTC).isoformat(),
        engine_version=ENGINE_VERSION, engine_source_hash=LOADED_SOURCE_HASH,
        catalog_version=catalog_file_hash(catalog_path), catalog_selection_hash=selection_hash(catalog),
        standards_registry_version=registry_hash(catalog_path),
        input_fingerprint=hashlib.sha256(snapshot.encode()).hexdigest(),
        input_snapshot_json=snapshot, assumptions=tuple(assumptions),
    )


def run_is_current(metadata: RunMetadata, project: BaseModel,
                   feeders: Sequence[BaseModel], catalog_path: Path,
                   catalog: Sequence[BaseModel] | None = None) -> bool:
    return (metadata.input_fingerprint == input_fingerprint(project, feeders)
            and metadata.engine_version == ENGINE_VERSION
            and metadata.engine_source_hash == engine_source_hash()
            and metadata.catalog_version == catalog_file_hash(catalog_path)
            and metadata.standards_registry_version == registry_hash(catalog_path)
            and (catalog is None or metadata.catalog_selection_hash == selection_hash(catalog)))
