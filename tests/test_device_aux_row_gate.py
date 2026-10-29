"""Auxiliary consistency on synthetic/copied data, not manufacturer approval."""

import json
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

import lv_assist.catalog as catalog_module
import lv_assist.engine as engine_module
from lv_assist.catalog import CatalogRepository
from lv_assist.catalog_validation import (
    CatalogValidationError,
    device_rows,
    validate_catalog_database,
)
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.ip_rating import ip_meets
from lv_assist.models import CatalogDevice, FeederInput, LoadType, ProjectSpec

ROOT = Path(__file__).resolve().parents[1]
BASE = CatalogDevice(part_number='TEST', manufacturer='SYNTHETIC', series='TEST', device_type='SYNTHETIC',
                     airflow_m3h=105, cap_kvar_400v=25, ip_rating='IP54').model_dump(mode='json')
BASE['poles'] = 4


def row(payload=None, **changes):
    return {'device_id': 'TEST', 'category': 'SYNTHETIC', 'manufacturer': 'SYNTHETIC', 'series': 'TEST',
            'model': 'TEST', 'in_a': None, 'icu_ka_400v': None, 'power_loss_w': 0,
            'derating_40c': 1, 'derating_50c': 1, 'width_mm': None, 'height_mm': None, 'depth_mm': None,
            'airflow_m3h': 105, 'kvar_rating': 25, 'ip_rating': 'IP54', 'ip_numeric': 54, 'poles': 4,
            'source_id': None,
            'data_quality': 'ESTIMATED', 'raw_json': json.dumps(BASE if payload is None else payload), **changes}


@pytest.mark.parametrize('field', ['airflow_m3h', 'kvar_rating'])
@pytest.mark.parametrize('value', [None, True, -1, float('inf'), '25', 1])
def test_consumed_auxiliary_sql_numbers_reject_invalid_or_conflicting_values(field, value):
    with pytest.raises(CatalogValidationError, match=field):
        device_rows([row(**{field: value})])


@pytest.mark.parametrize('sql_field,json_field', [('airflow_m3h', 'airflow_m3h'), ('kvar_rating', 'cap_kvar_400v')])
@pytest.mark.parametrize('value', [True, '7'])
def test_raw_json_auxiliary_numbers_cannot_be_coerced(sql_field, json_field, value):
    with pytest.raises(CatalogValidationError, match=json_field):
        device_rows([row({**BASE, json_field: value}, **{sql_field: 1 if value is True else 7})])


@pytest.mark.parametrize('sql_field,json_field', [('airflow_m3h', 'airflow_m3h'), ('kvar_rating', 'cap_kvar_400v')])
def test_legacy_nullable_auxiliary_zero_remains_unknown_without_fabricated_capacity(sql_field, json_field):
    payload = {key: value for key, value in BASE.items() if key != json_field}
    device = device_rows([row(payload, **{sql_field: None})])[0]
    assert getattr(device, json_field) == 0 and device.data_quality.value == 'ESTIMATED'


@pytest.mark.parametrize('value', [-1, True, '4', 4.0, 2**63])
@pytest.mark.parametrize('side', ['sql', 'json'])
def test_pole_counts_require_native_nonnegative_int64_metadata(side, value):
    source = row(poles=value) if side == 'sql' else row({**BASE, 'poles': value})
    with pytest.raises(CatalogValidationError, match='poles'):
        device_rows([source])


@pytest.mark.parametrize('json_value,sql_value', [(None, None), (0, None), (None, 0), (0, 0), (8, 8)])
def test_null_zero_poles_and_matching_positive_counts_do_not_imply_device_verification(json_value, sql_value):
    device = device_rows([row({**BASE, 'poles': json_value}, poles=sql_value)])[0]
    assert device.data_quality.value == 'ESTIMATED'


def test_positive_poles_must_match_and_missing_json_cannot_hide_a_stored_count():
    with pytest.raises(CatalogValidationError, match='poles SQL/JSON mismatch'):
        device_rows([row(poles=3)])
    payload = {key: value for key, value in BASE.items() if key != 'poles'}
    with pytest.raises(CatalogValidationError, match='poles SQL/JSON mismatch'):
        device_rows([row(payload)])


@pytest.mark.parametrize('rating', ['IPX4', 'IP65/IP67', 'IP69K', 'ip54', ' IP54', 'IP97', 'IP5٤'])
def test_unsupported_or_malformed_ip_is_not_repaired_by_digit_extraction(rating):
    with pytest.raises(CatalogValidationError, match='ip_rating'):
        device_rows([row({**BASE, 'ip_rating': rating}, ip_rating=rating)])


@pytest.mark.parametrize('field,value', [('ip_rating', 'IP55'), ('ip_numeric', 55), ('ip_numeric', None),
                                      ('ip_numeric', 54.0), ('ip_numeric', True), ('ip_numeric', '54')])
def test_sql_ip_metadata_must_match_literal_declared_code(field, value):
    with pytest.raises(CatalogValidationError, match='ip_'):
        device_rows([row(**{field: value})])


@pytest.mark.parametrize('value', [55, None, True, '54'])
def test_optional_raw_ip_numeric_cannot_contradict_declared_code(value):
    with pytest.raises(CatalogValidationError, match='ip_numeric'):
        device_rows([row({**BASE, 'ip_numeric': value})])


@pytest.mark.parametrize('rating,numeric', [('IP54', 54), ('IP68', 68), ('IP00', 0)])
def test_known_codes_load_as_metadata_without_promoting_unsupported_compatibility(rating, numeric):
    device = device_rows([row({**BASE, 'ip_rating': rating}, ip_rating=rating, ip_numeric=numeric)])[0]
    assert device.ip_rating == rating and device.data_quality.value == 'ESTIMATED'
    if rating == 'IP68':
        assert not ip_meets(device.ip_rating, 'IP65')


@pytest.mark.parametrize('empty', [False, True])
def test_missing_or_empty_ip_stays_unknown_instead_of_inheriting_model_ip20(empty):
    payload = {key: value for key, value in BASE.items() if key != 'ip_rating'}
    if empty:
        payload['ip_rating'] = ''
    device = device_rows([row(payload, ip_rating=None, ip_numeric=None)])[0]
    assert device.ip_rating == ''
    with pytest.raises(CatalogValidationError, match='ip_rating'):
        device_rows([row(payload, ip_rating='IP20', ip_numeric=20)])
    with pytest.raises(CatalogValidationError, match='ip_numeric'):
        device_rows([row(payload, ip_rating=None, ip_numeric=20)])


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def edit(repo, sql, params=()):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute(sql, params)


@pytest.mark.parametrize('sql', [
    'UPDATE catalog_devices SET airflow_m3h=-1 WHERE airflow_m3h IS NOT NULL',
    'UPDATE catalog_devices SET kvar_rating=kvar_rating+1 WHERE kvar_rating IS NOT NULL',
    'UPDATE catalog_devices SET poles=poles+1 WHERE poles IS NOT NULL',
    'UPDATE catalog_devices SET ip_numeric=ip_numeric+1 WHERE ip_numeric IS NOT NULL',
])
def test_actual_sql_reader_rules_and_cli_inventory_reject_unused_bad_fields_without_fallback(repo, sql):
    old = repo.devices
    edit(repo, sql)
    before = repo.db_path.read_bytes()
    for read in (lambda: repo.devices, repo.load_selectivity_rules, lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(CatalogValidationError):
            read()
    assert old and repo._devices_cache is None and repo.db_path.read_bytes() == before


def test_packaged_missing_ip_is_unknown_and_coherent_fan_change_reloads(repo):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        missing = {part for part, raw in connection.execute('SELECT device_id,raw_json FROM catalog_devices')
                   if 'ip_rating' not in json.loads(raw)}
        assert missing
        assert all(device.ip_rating == '' for device in repo.devices if device.part_number in missing)
        old = repo.devices
        part, raw = connection.execute('SELECT device_id, raw_json FROM catalog_devices WHERE airflow_m3h>0 LIMIT 1').fetchone()
        payload = json.loads(raw)
        payload['airflow_m3h'] += 1
        connection.execute('UPDATE catalog_devices SET airflow_m3h=?, raw_json=? WHERE device_id=?',
                           (payload['airflow_m3h'], json.dumps(payload), part))
    changed = next(device for device in repo.devices if device.part_number == part)
    assert changed.airflow_m3h == payload['airflow_m3h'] and repo.devices is not old
    assert validate_catalog_database(repo.db_path)['engineering_verification'] == 'NOT_VERIFIED'


def test_actual_cli_reports_scope_and_invalid_ip_without_writing(repo):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and 'airflow/kvar/IP/poles' in result['structural_scope']
    assert result['engineering_verification'] == 'NOT_VERIFIED' and repo.db_path.read_bytes() == before
    edit(repo, 'UPDATE catalog_devices SET ip_numeric=55 WHERE ip_rating IS NOT NULL')
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1 and json.loads(completed.stdout)['status'] == 'INVALID'
    assert repo.db_path.read_bytes() == before


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_bad_auxiliary_source_metadata_fails_engine_and_gui_keeps_last_results(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        devices = repo.load_devices()
        project = ProjectSpec(project_name='Device auxiliary gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(devices).process_project(project, inputs)
        edit(repo, 'UPDATE catalog_devices SET ip_numeric=55 WHERE ip_rating IS NOT NULL')
        engine = engine_module.EngineeringEngine(devices)
        with pytest.raises(CatalogValidationError, match='ip_numeric'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'ip_numeric' in messages[0]
    finally:
        i18n.set_language(previous)
