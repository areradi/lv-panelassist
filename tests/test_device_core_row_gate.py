"""Core SQL/JSON consistency; synthetic values never establish suitability."""

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
from lv_assist.models import CatalogDevice, FeederInput, LoadType, ProjectSpec

ROOT = Path(__file__).resolve().parents[1]
BASE = CatalogDevice(part_number='TEST', manufacturer='SYNTHETIC', series='SERIES', device_type='MCB',
                     rated_current_in_a=100, icu_ka_400v=10, power_loss_w=5,
                     width_mm=100, height_mm=200, depth_mm=50).model_dump(mode='json')
NUMBERS = [('in_a', 'rated_current_in_a'), ('icu_ka_400v', 'icu_ka_400v'),
           ('power_loss_w', 'power_loss_w'), ('derating_40c', 'derating_40c'),
           ('derating_50c', 'derating_50c'), ('width_mm', 'width_mm'),
           ('height_mm', 'height_mm'), ('depth_mm', 'depth_mm')]


def row(payload=None, **changes):
    return {'device_id': 'TEST', 'category': 'MCB', 'manufacturer': 'SYNTHETIC', 'series': 'SERIES',
            'model': 'TEST', 'in_a': 100, 'icu_ka_400v': 10, 'power_loss_w': 5,
            'derating_40c': 1, 'derating_50c': 1, 'width_mm': 100, 'height_mm': 200, 'depth_mm': 50,
            'data_quality': 'ESTIMATED', 'raw_json': json.dumps(BASE if payload is None else payload), **changes}


@pytest.mark.parametrize('field,value', [
    ('category', 'OTHER'), ('manufacturer', 'OTHER'), ('series', 'OTHER'), ('model', 'OTHER'),
    ('manufacturer', ' '), ('category', None), ('model', True), ('series', 'bad\x00text'),
    ('in_a', 101), ('in_a', None), ('in_a', True), ('in_a', '100'), ('in_a', -1),
    ('icu_ka_400v', 11), ('icu_ka_400v', None), ('power_loss_w', 6), ('power_loss_w', None),
    ('power_loss_w', float('inf')), ('derating_40c', 0.9), ('derating_50c', 0.8),
    ('derating_40c', None), ('width_mm', 101), ('height_mm', None), ('depth_mm', float('nan')),
    ('data_quality', 'REAL_VERIFIED'), ('data_quality', 'UNKNOWN'),
])
def test_sql_core_domains_or_mismatches_fail_before_use(field, value):
    with pytest.raises(ValueError):
        device_rows([row(**{field: value})])


@pytest.mark.parametrize('sql_field,json_field', NUMBERS)
@pytest.mark.parametrize('value', [True, '7'])
def test_raw_json_numbers_cannot_be_coerced_to_match_sql(sql_field, json_field, value):
    with pytest.raises(CatalogValidationError, match=json_field):
        device_rows([row({**BASE, json_field: value}, **{sql_field: 1 if value is True else 7})])


@pytest.mark.parametrize('sql_field,json_field', [NUMBERS[0], NUMBERS[1], *NUMBERS[5:]])
def test_nullable_sql_and_missing_json_keep_legacy_unknown_zero_without_invented_rating(sql_field, json_field):
    payload = {key: value for key, value in BASE.items() if key != json_field}
    device = device_rows([row(payload, **{sql_field: None})])[0]
    assert getattr(device, json_field) == 0 and device.data_quality.value == 'ESTIMATED'
    payload[json_field] = 0
    assert getattr(device_rows([row(payload, **{sql_field: None})])[0], json_field) == 0


def test_missing_model_defaults_still_agree_with_required_sql_defaults():
    payload = {key: value for key, value in BASE.items() if key not in ('power_loss_w', 'derating_40c', 'derating_50c')}
    device = device_rows([row(payload, power_loss_w=0)])[0]
    assert device.power_loss_w == 0 and device.derating_40c == device.derating_50c == 1


def test_explicit_model_metadata_is_preserved_as_linkage_without_replacing_part_number():
    device = device_rows([row({**BASE, 'model': 'Synthetic model label'}, model='Synthetic model label')])[0]
    assert device.part_number == 'TEST'
    with pytest.raises(CatalogValidationError, match='model'):
        device_rows([row({**BASE, 'model': {}})])


def test_consistent_verified_label_never_promotes_whole_device_and_missing_label_stays_estimated():
    device = device_rows([row({**BASE, 'data_quality': 'REAL_VERIFIED'}, data_quality='REAL_VERIFIED')])[0]
    assert device.data_quality.value == 'ESTIMATED'
    payload = {key: value for key, value in BASE.items() if key != 'data_quality'}
    assert device_rows([row(payload)])[0].data_quality.value == 'ESTIMATED'


def test_unexportable_text_in_ignored_extra_payload_is_not_silently_discarded():
    with pytest.raises(ValueError):
        device_rows([row({**BASE, 'unused_source_note': 'bad\x00text'})])


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def edit(repo, sql, params=()):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute(sql, params)


@pytest.mark.parametrize('field,value', [('manufacturer', 'OTHER'), ('in_a', -1),
                                      ('width_mm', 123456), ('data_quality', 'ESTIMATED')])
def test_bad_copied_sql_rows_fail_runtime_rules_and_inventory_without_cached_fallback(repo, field, value):
    old = repo.devices
    if field == 'data_quality':
        where = "data_quality='REAL_VERIFIED'"
    else:
        where = '1=1'
    edit(repo, f'UPDATE catalog_devices SET {field}=? WHERE {where}', (value,))
    before = repo.db_path.read_bytes()
    for read in (lambda: repo.devices, repo.load_selectivity_rules, lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(CatalogValidationError):
            read()
    assert old and repo._devices_cache is None and repo.db_path.read_bytes() == before


def test_coherent_current_edit_reloads_both_representations(repo):
    old = repo.devices
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        part, raw = connection.execute('SELECT device_id, raw_json FROM catalog_devices LIMIT 1').fetchone()
        payload = json.loads(raw)
        payload['rated_current_in_a'] = payload.get('rated_current_in_a', 0) + 1
        connection.execute('UPDATE catalog_devices SET in_a=?, raw_json=? WHERE device_id=?',
                           (payload['rated_current_in_a'], json.dumps(payload), part))
    changed = next(device for device in repo.devices if device.part_number == part)
    assert changed.rated_current_in_a == payload['rated_current_in_a'] and repo.devices is not old
    assert changed.data_quality.value == 'ESTIMATED'
    assert validate_catalog_database(repo.db_path)['devices'] == 102


def test_actual_cli_reports_core_scope_and_rejects_mismatch_without_repair(repo):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and result['devices'] == 102
    assert 'device core SQL/JSON' in result['structural_scope']
    assert result['engineering_verification'] == 'NOT_VERIFIED' and repo.db_path.read_bytes() == before
    edit(repo, "UPDATE catalog_devices SET manufacturer='OTHER'")
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 1 and result['status'] == 'INVALID'
    assert 'manufacturer' in result['error'] and repo.db_path.read_bytes() == before


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_actual_engine_source_precheck_and_gui_preserve_previous_run_on_bad_core(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        devices = repo.load_devices()
        project = ProjectSpec(project_name='Device core gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(devices).process_project(project, inputs)
        edit(repo, "UPDATE catalog_devices SET manufacturer='OTHER'")
        # A fresh engine can receive an existing valid selection snapshot; its
        # source precheck must still reject inconsistent SQL source records.
        engine = engine_module.EngineeringEngine(devices)
        with pytest.raises(CatalogValidationError, match='manufacturer'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'manufacturer' in messages[0]
    finally:
        i18n.set_language(previous)
