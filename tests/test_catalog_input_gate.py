"""Catalog data gates; structural validity never certifies engineering values."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from lv_assist.catalog import CatalogRepository, SiemensSelectivityRepository
from lv_assist.catalog_validation import (
    CatalogValidationError,
    validate_catalog_database,
)
from lv_assist.engine import EngineeringEngine
from lv_assist.gui import build_demo_project
from lv_assist.models import CatalogDevice, SelectivityRuleRecord

ROOT = Path(__file__).resolve().parents[1]


def device(**changes):
    values = {"part_number": "TEST-PART", "manufacturer": "TEST", "series": "TEST", "device_type": "MCB"}
    values.update(changes)
    return CatalogDevice(**values)


def database(tmp_path, *, identifier="TEST-PART", raw=None):
    path = tmp_path / "catalog.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE catalog_devices(device_id TEXT, raw_json TEXT, data_quality TEXT, category TEXT, manufacturer TEXT, series TEXT, model TEXT, in_a REAL, icu_ka_400v REAL, power_loss_w REAL, derating_40c REAL, derating_50c REAL, width_mm REAL, height_mm REAL, depth_mm REAL)")
        connection.execute("CREATE TABLE selectivity_rules(rule_id INTEGER, upstream_series TEXT, downstream_series TEXT, upstream_in_min_a REAL, upstream_in_max_a REAL, downstream_in_max_a REAL, min_ratio REAL, limit_ka REAL, selectivity_type TEXT, voltage_v REAL, is_verified_manufacturer_rule INTEGER, raw_json TEXT)")
        connection.execute("CREATE TABLE trip_curves(curve_id TEXT, curve_name TEXT, device_category TEXT, inst_min_mult REAL, inst_max_mult REAL, is_approximate INTEGER, allow_for_verification INTEGER, raw_json TEXT)")
        connection.execute("CREATE TABLE standards_registry(standard_id TEXT, raw_json TEXT)")
        connection.execute("CREATE TABLE cable_ampacity_reference(standard_id TEXT, table_ref TEXT, material TEXT, insulation TEXT, installation_method TEXT, loaded_conductors INTEGER, section_mm2 REAL, iz0_a REAL)")
        connection.execute("CREATE TABLE device_thermal_derating(device_id TEXT, temp_c REAL, derating_factor REAL)")
        connection.execute("CREATE TABLE pe_standard_sections(section_mm2 REAL)")
        connection.execute("CREATE TABLE device_breaking_capacities(device_id TEXT, voltage_v REAL, icu_ka REAL, ics_ka REAL)")
        payload = raw if raw is not None else device().model_dump_json()
        connection.execute("INSERT INTO catalog_devices VALUES (?, ?, 'ESTIMATED', 'MCB', 'TEST', 'TEST', 'TEST-PART', 0, 0, 0, 1, 1, 0, 0, 0)", (identifier, payload))
    return path


@pytest.mark.parametrize("name", [
    "rated_current_in_a", "icu_ka_400v", "setting_min_a", "setting_max_a",
    "power_loss_w", "coil_holding_24v_w", "width_mm", "derating_50c", "airflow_m3h",
])
@pytest.mark.parametrize("value", [-1, float("inf"), float("nan")])
def test_invalid_critical_numbers_are_rejected(name, value):
    with pytest.raises(ValueError):
        device(**{name: value})


@pytest.mark.parametrize("name", ["part_number", "manufacturer", "series", "device_type"])
def test_blank_catalog_identity_is_not_accepted(name):
    with pytest.raises(ValueError):
        device(**{name: "  "})


def test_duplicate_identity_cannot_enter_engine():
    with pytest.raises(CatalogValidationError, match="Duplicate"):
        EngineeringEngine([device(), device(part_number=" TEST-PART ")])


def test_mutated_internal_catalog_is_revalidated_before_processing():
    engine = EngineeringEngine(CatalogRepository.get_default_catalog())
    engine._full_catalog[0].power_loss_w = -1
    project, feeders = build_demo_project()
    with pytest.raises(ValueError):
        engine.process_project(project, feeders)


def test_caller_mutation_does_not_change_engine_catalog_snapshot():
    original = device(rated_current_in_a=16)
    engine = EngineeringEngine([original])
    original.rated_current_in_a = -1
    assert engine._full_catalog[0].rated_current_in_a == 16


def test_missing_catalog_is_not_implicitly_created_or_migrated(tmp_path):
    path = tmp_path / "absent.db"
    with pytest.raises(FileNotFoundError):
        CatalogRepository(path)
    assert not path.exists()


@pytest.mark.parametrize("bad_kind", ["identity", "negative", "duplicate_json_key", "not_object"])
def test_database_gate_and_runtime_loader_reject_same_bad_records(tmp_path, bad_kind):
    payload = device().model_dump()
    identifier = "WRONG-ID" if bad_kind == "identity" else "TEST-PART"
    if bad_kind == "negative":
        payload["icu_ka_400v"] = -1
    raw = json.dumps(payload)
    if bad_kind == "duplicate_json_key":
        raw = raw[:-1] + ', "part_number": "TEST-PART"}'
    if bad_kind == "not_object":
        raw = "[]"
    path = database(tmp_path, identifier=identifier, raw=raw)
    before = path.read_bytes()
    for read in (lambda: validate_catalog_database(path), lambda: CatalogRepository(path).devices):
        with pytest.raises(ValueError):
            read()
    assert path.read_bytes() == before


def test_conflicting_rule_limits_cannot_reach_project_results(monkeypatch):
    values = {"upstream_series": "U", "upstream_min_in_a": 100,
              "downstream_series": "D", "downstream_max_in_a": 25, "catalog_reference": "synthetic"}
    rules = [SelectivityRuleRecord(**values, selectivity_limit_is_ka=limit) for limit in (20, 36)]
    monkeypatch.setattr(SiemensSelectivityRepository, "get_selectivity_rules", classmethod(lambda cls: rules))
    project, feeders = build_demo_project()
    with pytest.raises(CatalogValidationError, match="conflicting"):
        EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, feeders)


def test_catalog_cli_reports_structural_scope_and_fails_without_writing(tmp_path):
    path = database(tmp_path)
    before = path.read_bytes()
    command = [sys.executable, "scripts/validate_catalog.py", "--db", str(path)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)["engineering_verification"] == "NOT_VERIFIED"
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE catalog_devices SET device_id='WRONG'")
    invalid_before = path.read_bytes()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 1 and json.loads(result.stdout)["status"] == "INVALID"
    assert path.read_bytes() == invalid_before


@pytest.mark.parametrize("value,expected", [(0, "ERROR"), (None, "ERROR"), (36, 36), (-1, "ERROR"),
                                          (float("inf"), "ERROR"), ("NaN", "ERROR")])
def test_normalized_icu_lookup_never_returns_an_invalid_positive_candidate(tmp_path, value, expected):
    path = database(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO device_breaking_capacities VALUES('TEST-PART', 400, ?, NULL)", (value,))
    before = path.read_bytes()
    repository = CatalogRepository(path)
    if expected == "ERROR":
        with pytest.raises(CatalogValidationError, match="icu_ka"):
            repository.get_device_icu_at_voltage("TEST-PART", 400)
    else:
        assert repository.get_device_icu_at_voltage("TEST-PART", 400) == expected
    assert path.read_bytes() == before
