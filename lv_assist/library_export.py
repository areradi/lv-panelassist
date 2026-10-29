"""Publish a new library only; never overwrite a nonempty user directory."""

import os
import tempfile
from pathlib import Path

from lv_assist.export_context import ExportContext


def export_current_library(folder, project, outputs, summary, checks, render):
    context = ExportContext.capture(project, outputs, summary, checks)
    snapshot = context.materialize()
    target = Path(folder)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise FileExistsError('Choose a new or empty library destination')
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    with tempfile.TemporaryDirectory(prefix='.lvassist-library-', dir=target.parent) as temporary:
        staging = Path(temporary) / 'content'
        staging.mkdir()
        with context.render_session():
            written = [Path(path) for path in render(str(staging), *snapshot)]
            context.require_unchanged(snapshot)
        if not written or len(set(written)) != len(written):
            raise OSError('Empty or duplicate library output')
        names = []
        for path in written:
            if path.parent.resolve() != staging.resolve() or not path.is_file() or path.is_symlink():
                raise OSError('Invalid library output path')
            names.append(path.name)
            with path.open('r+b') as stream:
                if not path.stat().st_size:
                    raise OSError('Empty library output')
                os.fsync(stream.fileno())
        if set(staging.iterdir()) != set(written):
            raise OSError('Unlisted library output')
        context.require_current()
        if target.exists():
            # rmdir refuses a nonempty directory, including a late caller write.
            target.rmdir()
        try:
            os.replace(staging, target)
        except OSError:
            if existed and not target.exists():
                target.mkdir()
            raise
    return [str(target / name) for name in names]
