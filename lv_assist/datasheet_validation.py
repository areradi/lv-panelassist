"""Structural source records and links; coarse labels never certify evidence."""

from lv_assist.rating_table_validation import identity, invalid
from lv_assist.text_validation import require_exportable_text

DATASHEET_COLUMNS = 'source_id, manufacturer, document_ref, revision, data_quality'


def source_identifier(value, table):
    identity(value, table, 'source_id')
    if value != value.strip():
        invalid(table, 'source_id')


def datasheet_rows(rows):
    sources = {}
    table = 'datasheet_sources'
    for row in rows:
        key = row['source_id']
        source_identifier(key, table)
        if key in sources:
            invalid(table, 'duplicate source_id')
        for field in ('manufacturer', 'document_ref'):
            identity(row[field], table, field)
        revision = row['revision']
        require_exportable_text(revision)
        if revision is not None and not isinstance(revision, str):
            invalid(table, 'revision')
        if row['data_quality'] not in ('REAL_VERIFIED', 'ESTIMATED', 'UNVERIFIED'):
            invalid(table, 'data_quality')
        sources[key] = {field: row[field] for field in
                        ('source_id', 'manufacturer', 'document_ref', 'revision', 'data_quality')}
    return sources


def validate_source_reference(row, payload, sources):
    key = row['source_id']
    if key is not None:
        source_identifier(key, 'catalog_devices')
        if key not in sources:
            invalid('catalog_devices', 'source_id unknown reference')
    if 'source_id' in payload:
        if payload['source_id'] is not None:
            source_identifier(payload['source_id'], 'catalog_devices')
        if payload['source_id'] != key:
            invalid('catalog_devices', 'source_id SQL/JSON mismatch')
