"""Separate literal machine interchange from spreadsheet-oriented CSV text."""

import csv
import os
import tempfile
from enum import Enum
from itertools import chain
from pathlib import Path


class CsvMode(str, Enum):
    MACHINE = 'machine'
    SPREADSHEET = 'spreadsheet'


def spreadsheet_text(value):
    if isinstance(value, str):
        significant = value.lstrip()
        while significant.startswith('\ufeff'):
            significant = significant[1:].lstrip()
        if significant.startswith(('=', '+', '-', '@')):
            return "'" + value
    return value


def write_csv(filepath, headers, rows, *, mode=CsvMode.MACHINE):
    # Reject a bad mode before touching a user's existing destination.
    mode = CsvMode(mode)
    target = Path(filepath)
    temporary = None
    try:
        # Same directory guarantees the final replace stays on one filesystem.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8-sig', newline='',
                                         prefix='.lvassist-csv-', suffix='.tmp',
                                         dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream)
            for row in chain((headers,), rows):
                writer.writerow([spreadsheet_text(value) for value in row]
                                if mode == CsvMode.SPREADSHEET else row)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
