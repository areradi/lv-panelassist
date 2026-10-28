"""Render standalone reports from one accepted run and publish only after recheck."""

import copy
import os
import tempfile
from pathlib import Path

from lv_assist.catalog import catalog_repo
from lv_assist.export_preflight import require_current_result


def export_current_report(filename, project, outputs, summary, checks, render):
    snapshot = copy.deepcopy((project, outputs, summary, checks))
    require_current_result(*snapshot, catalog_repo.db_path)
    target = Path(filename)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.lvassist-report-', suffix=target.suffix,
                                         dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
        render(str(temporary), *snapshot)
        require_current_result(*snapshot, catalog_repo.db_path)
        with temporary.open('r+b') as stream:
            if not temporary.stat().st_size:
                raise OSError('Report renderer produced an empty file')
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def export_current_text(filename, project, outputs, summary, checks, render_text,
                        *, encoding='utf-8', errors='strict'):
    def render(path, p, f, s, validations):
        Path(path).write_text(render_text(p, f, s), encoding=encoding, errors=errors)
    return export_current_report(filename, project, outputs, summary, checks, render)
