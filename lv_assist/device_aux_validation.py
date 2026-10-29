"""Auxiliary duplicate-field structure, never installed-device applicability."""

import re

from lv_assist.rating_table_validation import invalid

TABLE = 'catalog_devices'


def validate_device_aux(row, payload):
    poles = payload.get('poles')
    stored = row['poles']
    for value in (poles, stored):
        if value is not None and (type(value) is not int or not 0 <= value <= 2**63 - 1):
            invalid(TABLE, 'poles')
    # Preserve null/zero as existing unknown metadata; no pole count is inferred.
    if (poles or 0) != (stored or 0):
        invalid(TABLE, 'poles SQL/JSON mismatch')

    rating = payload.get('ip_rating')
    if rating is None or rating == '':
        if row['ip_rating'] not in (None, ''):
            invalid(TABLE, 'ip_rating SQL/JSON mismatch')
        numeric = None
    else:
        if not isinstance(rating, str) or re.fullmatch(r'IP[0-6][0-9]', rating) is None:
            invalid(TABLE, 'ip_rating unsupported syntax')
        if row['ip_rating'] != rating:
            invalid(TABLE, 'ip_rating SQL/JSON mismatch')
        numeric = int(rating[2:])
    for value in (row['ip_numeric'], payload.get('ip_numeric', numeric)):
        if numeric is None:
            if value is not None:
                invalid(TABLE, 'ip_numeric without declared ip_rating')
        elif type(value) is not int or value != numeric:
            invalid(TABLE, 'ip_numeric mismatch')
