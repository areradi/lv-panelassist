"""Render standalone reports from one accepted run and publish only after recheck."""

import os
import tempfile
from pathlib import Path

from lv_assist.export_context import ExportContext
from lv_assist.output_notice import annotate_svg


def export_current_report(filename, project, outputs, summary, checks, render):
    context = ExportContext.capture(project, outputs, summary, checks)
    snapshot = context.materialize()
    target = Path(filename)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.lvassist-report-', suffix=target.suffix,
                                         dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
        with context.render_session():
            render(str(temporary), *snapshot)
            context.require_unchanged(snapshot)
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
        text = render_text(p, f, s)
        if Path(filename).suffix.lower() == '.svg':
            text = annotate_svg(text, s)
        Path(path).write_text(text, encoding=encoding, errors=errors)
    return export_current_report(filename, project, outputs, summary, checks, render)
