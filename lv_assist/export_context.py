"""Immutable accepted run and source bytes shared by every public file exporter."""

import hashlib
import json
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from lv_assist.catalog import catalog_repo
from lv_assist.export_preflight import ExportSnapshotError, require_current_result
from lv_assist.i18n import SUPPORTED_LANGUAGES, i18n
from lv_assist.models import (
    FeederCalcOutput,
    PanelSummaryOutput,
    ProjectSpec,
    ValidationResult,
)
from lv_assist.run_metadata import catalog_file_hash


@dataclass(frozen=True)
class ExportContext:
    payload: str
    catalog_path: Path
    catalog_bytes: bytes
    language: str
    translations: str

    @classmethod
    def capture(cls, project, outputs, summary, checks):
        try:
            require_current_result(project, outputs, summary, checks, catalog_repo.db_path)
            payload = json.dumps([project.model_dump(mode='json'),
                                  [row.model_dump(mode='json') for row in outputs],
                                  summary.model_dump(mode='json'),
                                  [row.model_dump(mode='json') for row in checks]],
                                 ensure_ascii=False, allow_nan=False)
            path = catalog_repo.db_path.resolve()
            before = catalog_file_hash(path)
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != before or catalog_file_hash(path) != before:
                raise ExportSnapshotError('Catalog changed while capturing export')
            context = cls(payload, path, data, i18n.get_language(), json.dumps(
                {lang: dict(i18n._table(lang)) for lang in SUPPORTED_LANGUAGES}, ensure_ascii=False))
            context.require_current()
            return context
        except (TypeError, ValueError, OSError) as error:
            raise ExportSnapshotError('Recalculate before exporting this report') from error

    def materialize(self):
        project, outputs, summary, checks = json.loads(self.payload)
        return (ProjectSpec.model_validate(project),
                [FeederCalcOutput.model_validate(row) for row in outputs],
                PanelSummaryOutput.model_validate(summary),
                [ValidationResult.model_validate(row) for row in checks])

    def require_current(self):
        require_current_result(*self.materialize(), self.catalog_path)

    def require_unchanged(self, run):
        # Also detect mutation of a renderer's local materialization.
        require_current_result(*run, self.catalog_path)
        self.require_current()

    @contextmanager
    def render_session(self):
        self.require_current()
        tables = MappingProxyType({lang: MappingProxyType(values)
                                   for lang, values in json.loads(self.translations).items()})
        with tempfile.TemporaryDirectory(prefix='lvassist-export-context-') as folder:
            database = Path(folder) / 'catalog.db'
            database.write_bytes(self.catalog_bytes)
            with catalog_repo.read_snapshot(database), i18n.export_language(self.language, tables):
                yield
                self.require_current()
