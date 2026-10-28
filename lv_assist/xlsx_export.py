"""Publish a main engineering workbook without truncating an older report."""

import os
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def save_workbook_atomic(workbook, filename):
    target = Path(filename)
    temporary = None
    try:
        # Open binary and keep the handle private; openpyxl accepts file objects.
        with tempfile.NamedTemporaryFile(mode='w+b', prefix='.lvassist-xlsx-',
                                         suffix='.tmp', dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            workbook.save(stream)
            stream.flush()
            # Basic ZIP integrity check, not workbook/Excel semantic validation.
            stream.seek(0)
            with ZipFile(stream) as archive:
                if not {'[Content_Types].xml', 'xl/workbook.xml'} <= set(archive.namelist()):
                    raise BadZipFile('Required XLSX entries missing')
                if archive.testzip() is not None:
                    raise BadZipFile('Workbook ZIP integrity failure')
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
