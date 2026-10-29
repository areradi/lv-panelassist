"""Fail-closed catalog identity/shape checks; no engineering certification."""

import json
import sqlite3
from contextlib import closing
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from lv_assist.models import CatalogDevice, SelectivityRuleRecord
from lv_assist.trip_curve_validation import validated_curve
from lv_assist.i18n import tr
from lv_assist.rating_table_validation import identity, invalid, number, pe_sections, validate_rating_inventory
from lv_assist.run_metadata import catalog_file_hash
from lv_assist.registry_validation import registry_entries, registry_rows
from lv_assist.text_validation import require_exportable_text
from lv_assist.device_aux_validation import validate_device_aux
from lv_assist.datasheet_validation import DATASHEET_COLUMNS, datasheet_rows, validate_source_reference

SELECTIVITY_COLUMNS = ('rule_id, upstream_series, downstream_series, upstream_in_min_a, '
                       'upstream_in_max_a, downstream_in_max_a, min_ratio, limit_ka, '
                       'selectivity_type, voltage_v, is_verified_manufacturer_rule, raw_json')
TRIP_CURVE_COLUMNS = ('curve_id, curve_name, device_category, inst_min_mult, inst_max_mult, '
                      'is_approximate, allow_for_verification, raw_json')
DEVICE_COLUMNS = ('device_id, category, manufacturer, series, model, in_a, icu_ka_400v, '
                  'power_loss_w, derating_40c, derating_50c, width_mm, height_mm, depth_mm, '
                  'airflow_m3h, kvar_rating, ip_rating, ip_numeric, poles, data_quality, source_id, raw_json')


class CatalogValidationError(ValueError):
    """Catalog content is inconsistent; no automatic repair is performed."""


def validated_devices(devices: Iterable[CatalogDevice]) -> list[CatalogDevice]:
    result: list[CatalogDevice] = []
    seen: set[str] = set()
    for source in devices:
        # Revalidate model_copy/update and later mutation, and detach caller data.
        device = CatalogDevice.model_validate(source.model_dump())
        if device.part_number in seen:
            raise CatalogValidationError(f"Duplicate catalog part_number: {device.part_number}")
        seen.add(device.part_number)
        result.append(device)
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require_exportable_text(key)
        if key in result:
            raise CatalogValidationError(f"Duplicate JSON catalog key: {key}")
        result[key] = value
    return result


def catalog_object(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise CatalogValidationError('Catalog raw_json must be text')
    payload = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(payload, dict):
        raise CatalogValidationError("Catalog record must be a JSON object")
    return payload


def device_rows(rows: Iterable[Any], sources=()) -> list[CatalogDevice]:
    devices = []
    for row in rows:
        payload = catalog_object(row["raw_json"])
        require_exportable_text(payload)
        if 'data_quality' in payload and payload['data_quality'] != row['data_quality']:
            raise CatalogValidationError('catalog_devices data_quality SQL/JSON mismatch')
        payload["data_quality"] = row["data_quality"]
        # An omitted source declaration is unknown, not the generic model IP20.
        payload.setdefault('ip_rating', '')
        try:
            device = CatalogDevice.model_validate(payload)
        except ValidationError as error:
            raise CatalogValidationError(str(error)) from error
        if device.part_number != row["device_id"]:
            raise CatalogValidationError("Catalog row device_id does not match its part_number")
        try:
            validate_source_reference(row, payload, sources)
            for sql_field, expected in (('category', device.device_type),
                                        ('manufacturer', device.manufacturer), ('series', device.series),
                                        ('model', payload.get('model', device.part_number))):
                identity(row[sql_field], 'catalog_devices', sql_field)
                identity(expected, 'catalog_devices', sql_field)
                if row[sql_field] != expected:
                    invalid('catalog_devices', sql_field + ' SQL/JSON mismatch')
            for sql_field, field, nullable in (
                    ('in_a', 'rated_current_in_a', True), ('icu_ka_400v', 'icu_ka_400v', True),
                    ('power_loss_w', 'power_loss_w', False), ('derating_40c', 'derating_40c', False),
                    ('derating_50c', 'derating_50c', False), ('width_mm', 'width_mm', True),
                    ('height_mm', 'height_mm', True), ('depth_mm', 'depth_mm', True),
                    ('airflow_m3h', 'airflow_m3h', True), ('kvar_rating', 'cap_kvar_400v', True)):
                # Check original JSON values as well as the normalized model.
                if field in payload:
                    number(payload[field], 'catalog_devices', field)
                expected = getattr(device, field)
                if row[sql_field] is None and nullable and expected == 0:
                    continue  # Existing unknown/not-applicable representations.
                value = number(row[sql_field], 'catalog_devices', sql_field)
                if value < 0 or value != expected:
                    invalid('catalog_devices', sql_field + ' SQL/JSON mismatch')
            validate_device_aux(row, payload)
        except ValueError as error:
            raise CatalogValidationError(str(error)) from error
        devices.append(device)
    return validated_devices(devices)


def validated_rules(rules: Iterable[SelectivityRuleRecord], devices=None) -> list[SelectivityRuleRecord]:
    result = []
    seen = set()
    parts = {device.part_number: device for device in devices} if devices is not None else None
    series = {device.series for device in parts.values()} if parts is not None else None
    for source in rules:
        rule = SelectivityRuleRecord.model_validate(source.model_dump())
        if parts is not None:
            for side in ('upstream', 'downstream'):
                name = getattr(rule, side + '_series')
                part = getattr(rule, side + '_part_number')
                if name not in series:
                    raise CatalogValidationError('Unknown selectivity series: ' + name)
                if part is not None and (part not in parts or parts[part].series != name):
                    raise CatalogValidationError('Selectivity part/series reference mismatch: ' + side)
        # Two limits for the same conditions must not be resolved by taking max.
        key = (rule.upstream_series, rule.upstream_min_in_a, rule.downstream_series,
               rule.downstream_max_in_a, rule.upstream_part_number, rule.downstream_part_number,
               rule.operating_voltage_v, rule.upstream_setting_a, rule.downstream_setting_a,
               tuple(sorted(rule.source.applicability.items())) if rule.source is not None else ())
        if key in seen:
            raise CatalogValidationError("Duplicate/conflicting selectivity rule conditions")
        seen.add(key)
        result.append(rule)
    return result


def selectivity_rows(rows, devices):
    """Check complete SQL/JSON inventory before applying the activation flag."""
    rules, flags, seen = [], [], set()
    table = 'selectivity_rules'
    try:
        for row in rows:
            rule_id = row['rule_id']
            if type(rule_id) is not int or not 0 < rule_id <= 2**63 - 1 or rule_id in seen:
                invalid(table, 'rule_id')
            seen.add(rule_id)
            flag = row['is_verified_manufacturer_rule']
            if type(flag) is not int or flag not in (0, 1):
                invalid(table, 'is_verified_manufacturer_rule')
            payload = catalog_object(row['raw_json'])
            require_exportable_text(payload)
            rule = SelectivityRuleRecord.model_validate(payload)
            for sql_field, field in (('upstream_series', 'upstream_series'),
                                     ('downstream_series', 'downstream_series')):
                identity(row[sql_field], table, sql_field)
                if row[sql_field] != getattr(rule, field):
                    invalid(table, sql_field + ' SQL/JSON mismatch')
            for sql_field, field, positive in (
                    ('upstream_in_min_a', 'upstream_min_in_a', False),
                    ('downstream_in_max_a', 'downstream_max_in_a', True),
                    ('limit_ka', 'selectivity_limit_is_ka', True)):
                value = number(row[sql_field], table, sql_field, positive=positive)
                if value < 0 or value != getattr(rule, field):
                    invalid(table, sql_field + ' SQL/JSON mismatch')
            voltage = number(row['voltage_v'], table, 'voltage_v', positive=True)
            if rule.operating_voltage_v is not None and voltage != rule.operating_voltage_v:
                invalid(table, 'voltage_v SQL/JSON mismatch')
            upper = row['upstream_in_max_a']
            if upper is not None and number(upper, table, 'upstream_in_max_a', positive=True) < rule.upstream_min_in_a:
                invalid(table, 'upstream current range')
            if row['min_ratio'] is not None:
                number(row['min_ratio'], table, 'min_ratio', positive=True)
            if upper is not None or row['min_ratio'] is not None:
                invalid(table, 'unsupported upstream_in_max_a/min_ratio applicability')
            kinds = ('VERIFIED_TOTAL', 'TOTAL') if rule.is_total_up_to_icu else ('VERIFIED_PARTIAL', 'PARTIAL')
            if row['selectivity_type'] not in kinds:
                invalid(table, 'selectivity_type SQL/JSON mismatch')
            rules.append(rule)
            flags.append(flag)
        rules = validated_rules(rules, devices)
    except ValueError as error:
        raise CatalogValidationError(str(error)) from error
    return rules, [rule for rule, flag in zip(rules, flags) if flag == 1]


def curve_rows(rows):
    """SQL and JSON must agree; this table permits approximate curves only."""
    curves = {}
    for row in rows:
        name = row["curve_id"]
        curve = validated_curve(name, catalog_object(row["raw_json"]), CatalogValidationError)
        if name in curves:
            raise CatalogValidationError("Duplicate trip curve identity")
        try:
            for field, expected in (('is_approximate', 1), ('allow_for_verification', 0)):
                if type(row[field]) is not int or row[field] != expected:
                    invalid('trip_curves', field)
            identity(row['curve_name'], 'trip_curves', 'curve_name')
            if row['device_category'] is not None:
                identity(row['device_category'], 'trip_curves', 'device_category')
            for sql_field, field in (('curve_name', 'name'), ('device_category', 'category')):
                if field in curve and row[sql_field] != curve[field]:
                    invalid('trip_curves', sql_field + ' SQL/JSON mismatch')
            for sql_field, field in (('inst_min_mult', 'im_min_mult'), ('inst_max_mult', 'im_max_mult')):
                value = number(row[sql_field], 'trip_curves', sql_field, positive=True)
                if value != curve[field]:
                    invalid('trip_curves', sql_field + ' SQL/JSON mismatch')
        except ValueError as error:
            raise CatalogValidationError(str(error)) from error
        curves[name] = curve
    return curves


def validated_curves(curves):
    if not isinstance(curves, dict):
        raise CatalogValidationError(tr("audit_curve_invalid", name="?", field="curve_map"))
    return {name: validated_curve(name, curve, CatalogValidationError) for name, curve in curves.items()}


def breaking_capacity_rows(rows, device_ids):
    """Exact device/voltage ratings; optional Ics is never inferred from Icu."""
    result = {}
    table = 'device_breaking_capacities'
    try:
        for row in rows:
            device_id = row['device_id']
            identity(device_id, table, 'device_id')
            if device_id not in device_ids:
                invalid(table, 'unknown device_id')
            voltage = number(row['voltage_v'], table, 'voltage_v', positive=True)
            icu = number(row['icu_ka'], table, 'icu_ka', positive=True)
            ics = row['ics_ka']
            if ics is not None:
                ics = number(ics, table, 'ics_ka', positive=True)
            key = (device_id, voltage)
            if key in result:
                invalid(table, 'duplicate device_id/voltage_v')
            result[key] = (icu, ics)
    except ValueError as error:
        raise CatalogValidationError(str(error)) from error
    return result


def validate_catalog_database(path: Path) -> dict[str, Any]:
    """Read-only structural checks; scope and file identity accompany the result."""
    if not path.is_file():
        raise FileNotFoundError(f"Catalog database is missing: {path}")
    before_hash = catalog_file_hash(path)
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise CatalogValidationError("Catalog integrity_check failed: " + integrity)
        sources = datasheet_rows(connection.execute('SELECT ' + DATASHEET_COLUMNS + ' FROM datasheet_sources'))
        stored_devices = connection.execute('SELECT ' + DEVICE_COLUMNS + ' FROM catalog_devices').fetchall()
        devices = device_rows(stored_devices, sources)
        rules, enabled_rules = selectivity_rows(connection.execute('SELECT ' + SELECTIVITY_COLUMNS + ' FROM selectivity_rules'), devices)
        curves = curve_rows(connection.execute('SELECT ' + TRIP_CURVE_COLUMNS + ' FROM trip_curves'))
        standards = registry_rows(connection.execute("SELECT standard_id, raw_json FROM standards_registry"))
        ratings = validate_rating_inventory(
            connection.execute("SELECT * FROM cable_ampacity_reference"),
            connection.execute("SELECT * FROM device_thermal_derating"),
            {device.part_number for device in devices},
            standards)
        protective_sections = pe_sections(connection.execute("SELECT section_mm2 FROM pe_standard_sections"))
        breaking = breaking_capacity_rows(
            connection.execute("SELECT device_id, voltage_v, icu_ka, ics_ka FROM device_breaking_capacities"),
            {device.part_number for device in devices})
    if catalog_file_hash(path) != before_hash:
        raise CatalogValidationError(tr("audit_catalog_unstable"))
    return {"devices": len(devices), "selectivity_rules": len(rules),
            "datasheet_sources": len(sources),
            "device_source_links": sum(row['source_id'] is not None for row in stored_devices),
            "enabled_selectivity_rules": len(enabled_rules), "trip_curves": len(curves),
            **ratings, "pe_sections": len(protective_sections), "catalog_hash": before_hash,
            "breaking_capacity_rows": len(breaking),
            "breaking_capacity_devices": len({key[0] for key in breaking}),
            "standards_registry_rows": len(standards),
            "localized_standard_entries": len(registry_entries(standards)),
            "trip_curve_policy": "APPROXIMATE_ONLY",
            "structural_scope": "device core SQL/JSON identities/numbers/quality consistency plus airflow/kvar/IP/poles and datasheet source links/records, selectivity SQL/JSON conditions/references, trip curve SQL/JSON/approximation policy, ampacity/derating inventory, PE sections, breaking capacities and standards registry payloads",
            "engineering_verification": "NOT_VERIFIED"}
