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


def validate_rating_inventory(ampacity_rows, derating_rows, device_ids, standard_ids):
    """Validate every rating combination, including rows unused by a project."""
    standards = set()
    for value in standard_ids:
        identity(value, 'standards_registry', 'standard_id')
        if value in standards:
            invalid('standards_registry', 'duplicate standard_id')
        standards.add(value)
    ampacity_groups = {}
    ampacity_count = 0
    for row in ampacity_rows:
        table = 'cable_ampacity_reference'
        identity(row['standard_id'], table, 'standard_id')
        identity(row['table_ref'], table, 'table_ref')
        if row['standard_id'] not in standards:
            invalid(table, 'unknown standard_id')
        material = identity(row['material'], table, 'material')
        insulation = identity(row['insulation'], table, 'insulation')
        method = identity(row['installation_method'], table, 'installation_method')
        if material not in ('CU', 'AL') or insulation not in ('PVC', 'XLPE'):
            invalid(table, 'material/insulation')
        count = row['loaded_conductors']
        if not isinstance(count, int) or isinstance(count, bool) or not 0 < count <= 2**63 - 1:
            invalid(table, 'loaded_conductors')
        ampacity_groups.setdefault((material, insulation, method, count), []).append(row)
        ampacity_count += 1
    for rows in ampacity_groups.values():
        ampacity_table(rows)
    derating_groups = {}
    derating_count = 0
    for row in derating_rows:
        identity(row['device_id'], 'device_thermal_derating', 'device_id')
        if row['device_id'] not in device_ids:
            invalid('device_thermal_derating', 'unknown device_id')
        derating_groups.setdefault(row['device_id'], []).append(row)
        derating_count += 1
    for rows in derating_groups.values():
        derating_table(rows)
    return {'ampacity_rows': ampacity_count, 'derating_rows': derating_count,
            'ampacity_combinations': len(ampacity_groups), 'derating_devices': len(derating_groups)}
