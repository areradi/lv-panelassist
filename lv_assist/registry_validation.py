"""Registry structure and display text; no reference authenticity is inferred."""

import json

from lv_assist.rating_table_validation import identity, invalid
from lv_assist.text_validation import require_exportable_text

TABLE = 'standards_registry'


def registry_identifier(value):
    identity(value, TABLE, 'standard_id')
    if value != value.strip():
        invalid(TABLE, 'standard_id')
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require_exportable_text(key)
        if key in result:
            invalid(TABLE, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def _constant(value):
    invalid(TABLE, 'nonfinite JSON number: ' + value)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        invalid(TABLE, field)


def _translations(value, field, *, required=False):
    if not isinstance(value, dict) or (required and not value):
        invalid(TABLE, field)
    for locale, text in value.items():
        _text(locale, field + '.locale')
        _text(text, field + '.' + locale)


def _entry(value, standard_id):
    if not isinstance(value, dict):
        invalid(TABLE, 'entry')
    if 'id' in value and value['id'] != standard_id:
        invalid(TABLE, 'id mismatch')
    if 'code' in value:
        _text(value['code'], 'code')
    if 'edition' in value and value['edition'] is not None and not isinstance(value['edition'], str):
        invalid(TABLE, 'edition')
    if 'title' in value:
        _translations(value['title'], 'title', required=True)
    if 'scope' in value:
        _translations(value['scope'], 'scope')


def registry_entries(standards):
    """Validate both stored shapes and flatten only explicit localized entries."""
    if not isinstance(standards, dict):
        invalid(TABLE, 'registry_map')
    try:
        # Reject nonfinite/unsupported values and cyclic caller mutations too.
        json.dumps(standards, allow_nan=False)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError('Invalid standards_registry JSON values') from error
    require_exportable_text(standards)
    result = {}

    def add(standard_id, entry):
        registry_identifier(standard_id)
        _entry(entry, standard_id)
        if 'title' not in entry:
            invalid(TABLE, 'title')
        if standard_id in result:
            invalid(TABLE, 'duplicate localized standard_id')
        result[standard_id] = entry

    for standard_id, payload in standards.items():
        registry_identifier(standard_id)
        _entry(payload, standard_id)
        if 'title' in payload:
            add(standard_id, payload)
        elif 'code' not in payload:
            entries = {key: value for key, value in payload.items() if key != 'id'}
            if not entries:
                invalid(TABLE, 'empty registry entry')
            for nested_id, entry in entries.items():
                add(nested_id, entry)
    return result


def registry_rows(rows):
    """Keep row IDs/payloads intact; never resolve duplicates by last write."""
    result = {}
    for row in rows:
        standard_id = registry_identifier(row['standard_id'])
        if standard_id in result:
            invalid(TABLE, 'duplicate standard_id')
        raw = row['raw_json']
        if not isinstance(raw, str):
            invalid(TABLE, 'raw_json')
        payload = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_constant)
        if not isinstance(payload, dict):
            invalid(TABLE, 'JSON object')
        result[standard_id] = payload
    registry_entries(result)
    return result
