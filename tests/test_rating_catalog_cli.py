"""Whole-inventory checks on weak synthetic schemas and actual read-only CLI."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

import lv_assist.catalog_validation as validation
from lv_assist.models import CatalogDevice

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'catalog.db'
    connection = sqlite3.connect(path)
    try:
        with connection:
            for statement in (
                'CREATE TABLE catalog_devices(device_id TEXT, raw_json TEXT, data_quality TEXT, category TEXT, manufacturer TEXT, series TEXT, model TEXT, in_a REAL, icu_ka_400v REAL, power_loss_w REAL, derating_40c REAL, derating_50c REAL, width_mm REAL, height_mm REAL, depth_mm REAL, airflow_m3h REAL, kvar_rating REAL, ip_rating TEXT, ip_numeric INTEGER, poles INTEGER, source_id TEXT)',
                'CREATE TABLE datasheet_sources(source_id TEXT, manufacturer TEXT, document_ref TEXT, revision TEXT, data_quality TEXT)',
                'CREATE TABLE selectivity_rules(rule_id INTEGER, upstream_series TEXT, downstream_series TEXT, upstream_in_min_a REAL, upstream_in_max_a REAL, downstream_in_max_a REAL, min_ratio REAL, limit_ka REAL, selectivity_type TEXT, voltage_v REAL, is_verified_manufacturer_rule INTEGER, raw_json TEXT)',
                'CREATE TABLE trip_curves(curve_id TEXT, curve_name TEXT, device_category TEXT, inst_min_mult REAL, inst_max_mult REAL, is_approximate INTEGER, allow_for_verification INTEGER, raw_json TEXT)',
                'CREATE TABLE standards_registry(standard_id TEXT, raw_json TEXT)',
                'CREATE TABLE cable_ampacity_reference(standard_id TEXT, table_ref TEXT, material TEXT, insulation TEXT, installation_method TEXT, loaded_conductors INTEGER, section_mm2 REAL, iz0_a REAL)',
                'CREATE TABLE device_thermal_derating(device_id TEXT, temp_c REAL, derating_factor REAL)',
                'CREATE TABLE pe_standard_sections(section_mm2 REAL)',
                'CREATE TABLE device_breaking_capacities(device_id TEXT, voltage_v REAL, icu_ka REAL, ics_ka REAL)',
            ):
                connection.execute(statement)
            device = CatalogDevice(part_number='T', manufacturer='TEST', series='TEST', device_type='MCB')
            connection.execute("INSERT INTO catalog_devices VALUES ('T', ?, 'ESTIMATED', 'MCB', 'TEST', 'TEST', 'T', 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 'IP20', 20, NULL, NULL)", (device.model_dump_json(),))
            connection.execute("INSERT INTO standards_registry VALUES ('STD', ?)", (json.dumps({'code': 'STD'}),))
            connection.execute("INSERT INTO cable_ampacity_reference VALUES ('STD','synthetic table','CU','PVC','C',3,16,57)")
            connection.execute("INSERT INTO device_thermal_derating VALUES ('T',50,0.9)")
    finally:
        connection.close()
    return path


def edit(path, sql, params=()):
    connection = sqlite3.connect(path)
    try:
        with connection:
            connection.execute(sql, params)
    finally:
        connection.close()


@pytest.mark.parametrize('field,value', [
    ('iz0_a', -1), ('iz0_a', 0), ('iz0_a', 'bad'), ('iz0_a', None),
    ('section_mm2', -1), ('section_mm2', float('inf')),
    ('loaded_conductors', 0), ('loaded_conductors', 2.5),
    ('material', 'STEEL'), ('insulation', 'UNKNOWN'), ('installation_method', ''),
    ('standard_id', 'MISSING'), ('table_ref', 'bad\x00ref'),
])
def test_all_ampacity_rows_checked_even_without_running_project(database, field, value):
    edit(database, f'UPDATE cable_ampacity_reference SET {field}=?', (value,))
    before = database.read_bytes()
    with pytest.raises(ValueError):
        validation.validate_catalog_database(database)
    assert database.read_bytes() == before


@pytest.mark.parametrize('field,value', [
    ('temp_c', 19), ('temp_c', 81), ('temp_c', 'bad'), ('temp_c', None),
    ('derating_factor', 0), ('derating_factor', 1.3), ('derating_factor', 'bad'),
    ('derating_factor', float('inf')), ('device_id', 'MISSING'),
])
def test_all_derating_rows_checked_even_without_running_project(database, field, value):
    edit(database, f'UPDATE device_thermal_derating SET {field}=?', (value,))
    before = database.read_bytes()
    with pytest.raises(ValueError):
        validation.validate_catalog_database(database)
    assert database.read_bytes() == before


@pytest.mark.parametrize('table', ['cable_ampacity_reference', 'device_thermal_derating'])
def test_duplicate_conditions_not_hidden_by_dictionary_conversion(database, table):
    edit(database, f'INSERT INTO {table} SELECT * FROM {table}')
    with pytest.raises(ValueError):
        validation.validate_catalog_database(database)


def test_distinct_combinations_can_share_section_without_conflict(database):
    edit(database, "INSERT INTO cable_ampacity_reference VALUES ('STD','test','AL','XLPE','E',3,16,40)")
    result = validation.validate_catalog_database(database)
    assert result['ampacity_rows'] == result['ampacity_combinations'] == 2
    assert result['derating_rows'] == result['derating_devices'] == 1
    assert result['engineering_verification'] == 'NOT_VERIFIED'


def test_case_equivalent_combination_cannot_smuggle_a_duplicate(database):
    edit(database, "INSERT INTO cable_ampacity_reference VALUES ('STD','test','cu','pvc','c',3,16,57)")
    with pytest.raises(ValueError):
        validation.validate_catalog_database(database)


def test_actual_cli_reports_counts_hash_and_invalid_status_without_writing(database):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(database)]
    before = database.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result['status'] == 'STRUCTURALLY_VALID'
    assert result['ampacity_rows'] == result['derating_rows'] == 1
    assert result['catalog_hash'] == validation.catalog_file_hash(database)
    assert result['engineering_verification'] == 'NOT_VERIFIED'
    assert database.read_bytes() == before
    edit(database, 'UPDATE device_thermal_derating SET derating_factor=0')
    before = database.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result['status'] == 'INVALID' and 'derating_factor' in result['error']
    assert database.read_bytes() == before


def test_missing_rating_table_is_not_reported_as_valid_catalog(database):
    edit(database, 'DROP TABLE cable_ampacity_reference')
    with pytest.raises(sqlite3.DatabaseError):
        validation.validate_catalog_database(database)


@pytest.mark.parametrize('suffix', ['-wal', '-journal'])
def test_actual_cli_rejects_untracked_sidecar_without_modification(database, suffix):
    sidecar = Path(str(database) + suffix)
    sidecar.write_bytes(b'synthetic nonempty indicator')
    before = database.read_bytes()
    completed = subprocess.run([sys.executable, 'scripts/validate_catalog.py', '--db', str(database)],
                               cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1
    assert json.loads(completed.stdout)['status'] == 'INVALID'
    assert database.read_bytes() == before and sidecar.read_bytes() == b'synthetic nonempty indicator'


def test_catalog_change_during_validation_cannot_receive_success(database, monkeypatch):
    calls = iter(['initial', 'changed'])
    monkeypatch.setattr(validation, 'catalog_file_hash', lambda path: next(calls))
    with pytest.raises(ValueError):
        validation.validate_catalog_database(database)
