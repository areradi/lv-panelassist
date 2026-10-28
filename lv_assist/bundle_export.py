"""Publish a complete closed ZIP while preserving a previous bundle on failure."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True)
class BundleExportResult:
    file_count: int
    pdf_status: str
    pdf_reason: str | None


def export_manifest(names, metadata, locale, pdf_status, pdf_reason):
    files = [{"path": name, "status": "GENERATED"} for name in names]
    if pdf_status != "GENERATED":
        files.append({"path": "02_Engineering_Report.pdf", "status": pdf_status,
                      "reason": pdf_reason})
    return {"schema_version": 1, "locale": locale, "preliminary": True,
            "run_metadata": metadata.model_dump(mode="json") if metadata else None,
            "pdf": {"status": pdf_status, "reason": pdf_reason}, "files": files,
            "inventory_excludes": ["00_Export_Manifest.json", "00_Export_Status.txt"]}


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
