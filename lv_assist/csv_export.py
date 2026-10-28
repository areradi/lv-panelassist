"""Separate literal machine interchange from spreadsheet-oriented CSV text."""

import csv
from enum import Enum


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
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        for row in (headers, *rows):
            writer.writerow([spreadsheet_text(value) for value in row]
                            if mode == CsvMode.SPREADSHEET else row)
