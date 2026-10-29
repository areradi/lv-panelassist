"""Fail-closed catalog identity/shape checks; no engineering certification."""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from lv_assist.models import CatalogDevice, SelectivityRuleRecord
from lv_assist.trip_curve_validation import validated_curve
from lv_assist.i18n import tr


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
        if key in result:
            raise CatalogValidationError(f"Duplicate JSON catalog key: {key}")
        result[key] = value
    return result


def catalog_object(raw: str) -> dict[str, Any]:
    payload = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(payload, dict):
        raise CatalogValidationError("Catalog record must be a JSON object")
    return payload


def device_rows(rows: Iterable[Any]) -> list[CatalogDevice]:
    devices = []
    for row in rows:
        payload = catalog_object(row["raw_json"])
        payload["data_quality"] = row["data_quality"]
        device = CatalogDevice.model_validate(payload)
        if device.part_number != row["device_id"]:
            raise CatalogValidationError("Catalog row device_id does not match its part_number")
        devices.append(device)
    return validated_devices(devices)


def validated_rules(rules: Iterable[SelectivityRuleRecord]) -> list[SelectivityRuleRecord]:
    result = []
    seen = set()
    for source in rules:
        rule = SelectivityRuleRecord.model_validate(source.model_dump())
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


def curve_rows(rows):
    curves = {}
    for row in rows:
        name = row["curve_id"]
        if name in curves:
            raise CatalogValidationError("Duplicate trip curve identity")
        curves[name] = validated_curve(name, catalog_object(row["raw_json"]), CatalogValidationError)
    return curves


def validated_curves(curves):
    if not isinstance(curves, dict):
        raise CatalogValidationError(tr("audit_curve_invalid", name="?", field="curve_map"))
    return {name: validated_curve(name, curve, CatalogValidationError) for name, curve in curves.items()}


def validate_catalog_database(path: Path) -> dict[str, Any]:
    """Read-only structural scope: device identities/numbers and selectivity rows."""
    if not path.is_file():
        raise FileNotFoundError(f"Catalog database is missing: {path}")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise CatalogValidationError("Catalog integrity_check failed")
        devices = device_rows(connection.execute("SELECT device_id, raw_json, data_quality FROM catalog_devices"))
        rules = validated_rules(SelectivityRuleRecord.model_validate(catalog_object(row[0]))
                                for row in connection.execute("SELECT raw_json FROM selectivity_rules"))
        curves = curve_rows(connection.execute("SELECT curve_id, raw_json FROM trip_curves"))
    return {"devices": len(devices), "selectivity_rules": len(rules), "trip_curves": len(curves),
            "structural_scope": "device identity/numbers, selectivity conditions and trip curve structure",
            "engineering_verification": "NOT_VERIFIED"}
