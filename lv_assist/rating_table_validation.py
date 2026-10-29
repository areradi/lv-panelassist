"""Consumed auxiliary rating domains; no engineering/source approval implied."""

import math

from lv_assist.i18n import tr
from lv_assist.text_validation import require_exportable_text


def invalid(table, field):
    # Keep identifiers literal when FA translation normalizes digits.
    template = tr('audit_rating_invalid', table='__TABLE__', field='__FIELD__')
    raise ValueError(template.replace('__TABLE__', table).replace('__FIELD__', field))


def number(value, table, field, *, positive=False, maximum=None):
    try:
        good = (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and (not positive or value > 0)
                and (maximum is None or value <= maximum))
    except OverflowError:
        good = False
    if not good:
        invalid(table, field)
    return float(value)


def identity(value, table, field):
    require_exportable_text(value)
    if not isinstance(value, str) or not value.strip():
        invalid(table, field)
    return value.upper()


def ampacity_table(rows):
    result = {}
    for row in rows:
        section = number(row['section_mm2'], 'cable_ampacity_reference', 'section_mm2', positive=True)
        current = number(row['iz0_a'], 'cable_ampacity_reference', 'iz0_a', positive=True)
        if section in result:
            invalid('cable_ampacity_reference', 'duplicate section_mm2')
        result[section] = current
    return result


def derating_table(rows):
    result = {}
    for row in rows:
        temperature = number(row['temp_c'], 'device_thermal_derating', 'temp_c')
        if not 20 <= temperature <= 80:
            invalid('device_thermal_derating', 'temp_c')
        factor = number(row['derating_factor'], 'device_thermal_derating', 'derating_factor',
                        positive=True, maximum=1.2)
        if temperature in result:
            invalid('device_thermal_derating', 'duplicate temp_c')
        result[temperature] = factor
    return result
