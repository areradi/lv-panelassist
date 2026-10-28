"""Publish a complete closed ZIP while preserving a previous bundle on failure."""

import os
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def build_bundle_atomic(filename, build):
    target = Path(filename)
    temporary = None
    try:
        # Close the named file before the builder reopens it (Windows support).
        with tempfile.NamedTemporaryFile(prefix='.lvassist-bundle-', suffix='.zip',
                                         dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
        count = build(str(temporary))
        with temporary.open('r+b') as stream:
            with ZipFile(stream) as archive:
                names = archive.namelist()
                if count <= 0 or len(names) != count or len(set(names)) != count:
                    raise BadZipFile('Bundle entry count mismatch or duplicate member')
                if archive.testzip() is not None:
                    raise BadZipFile('Bundle ZIP integrity failure')
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        return count
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
