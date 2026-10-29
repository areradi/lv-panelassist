"""Device numeric boundary checks; no numerical engineering reference values."""

import json
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from lv_assist.catalog import CatalogRepository, catalog_repo
from lv_assist.catalog_validation import (
    CatalogValidationError,
    validate_catalog_database,
    validated_devices,
)
from lv_assist.engine import EngineeringEngine
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import CatalogDevice, FeederInput, LoadType, ProjectSpec

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('rated_current_in_a', 'boost_current_peak_a', 'setting_min_a', 'setting_max_a',
          'motor_kw_400v', 'icu_ka_400v', 'power_loss_w', 'coil_holding_24v_w', 'coil_pull_in_24v_w',
          'derating_40c', 'derating_50c', 'cap_kvar_400v', 'detuned_pct', 'tuned_hz',
          'width_mm', 'height_mm', 'depth_mm', 'airflow_m3h', 'spd_uc_v', 'spd_up_kv',
          'spd_in_ka', 'spd_imax_ka', 'spd_iimp_ka', 'spd_backup_fuse_a')


def device(**changes):
    return CatalogDevice(part_number='TEST', manufacturer='TEST', series='TEST', device_type='MCB', **changes)


@pytest.mark.parametrize('field', FIELDS)
@pytest.mark.parametrize('value', [True, '7'])
def test_all_declared_numeric_attributes_reject_boolean_and_numeric_text(field, value):
    with pytest.raises(ValidationError, match=field):
        device(**{field: value})


@pytest.mark.parametrize('value', [None, False, b'7', Decimal(7), float('nan'), float('inf'), 2**10000],
                         ids=['null', 'false', 'bytes', 'decimal', 'nan', 'infinite', 'overflow'])
def test_other_non_native_or_nonfinite_values_cannot_become_device_numbers(value):
    with pytest.raises(ValidationError, match='coil_pull_in_24v_w'):
        device(coil_pull_in_24v_w=value)


@pytest.mark.parametrize('value', [0, 0.0, 7, 7.5])
def test_valid_native_numbers_and_existing_zero_sentinels_remain_supported(value):
    item = device(**dict.fromkeys(FIELDS, value), spd_poles='4P', data_quality='REAL_VERIFIED')
    assert all(getattr(item, field) == value for field in FIELDS)
    assert item.spd_poles == '4P' and item.data_quality.value == 'ESTIMATED'


def test_json_model_boundary_does_not_coerce_numbers_and_strings_stay_strings():
    payload = device().model_dump(mode='json')
    payload['spd_in_ka'] = '10'
    with pytest.raises(ValidationError, match='spd_in_ka'):
        CatalogDevice.model_validate_json(json.dumps(payload))
    payload['spd_in_ka'] = 10
    payload['part_number'] = '  =INCOMING  '
    result = CatalogDevice.model_validate_json(json.dumps(payload))
    assert result.spd_in_ka == 10 and result.part_number == '=INCOMING'


def test_model_copy_bypass_is_revalidated_before_engine_construction():
    invalid = device().model_copy(update={'spd_in_ka': True})
    with pytest.raises(ValidationError, match='spd_in_ka'):
        validated_devices([invalid])
    with pytest.raises(ValidationError, match='spd_in_ka'):
        EngineeringEngine([invalid])


@pytest.mark.parametrize('field,value', [('coil_holding_24v_w', True), ('spd_iimp_ka', '10')])
def test_actual_sql_and_cli_reject_numeric_coercion_in_fields_without_normalized_twins(tmp_path, field, value):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_repo.db_path, path)
    with closing(sqlite3.connect(path)) as connection, connection:
        part, raw = connection.execute('SELECT device_id,raw_json FROM catalog_devices LIMIT 1').fetchone()
        payload = json.loads(raw)
        payload[field] = value
        connection.execute('UPDATE catalog_devices SET raw_json=? WHERE device_id=?', (json.dumps(payload), part))
    before = path.read_bytes()
    for read in (lambda: CatalogRepository(path).devices, lambda: validate_catalog_database(path)):
        with pytest.raises(CatalogValidationError, match=field):
            read()
    completed = subprocess.run([sys.executable, 'scripts/validate_catalog.py', '--db', str(path)],
                               cwd=ROOT, capture_output=True, text=True, check=False)
    report = json.loads(completed.stdout)
    assert completed.returncode == 1 and report['status'] == 'INVALID' and field in report['error']
    assert path.read_bytes() == before


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_mutated_internal_number_fails_before_arithmetic_and_gui_keeps_previous_result(monkeypatch, locale):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Native catalog numbers')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        engine = EngineeringEngine(CatalogRepository.get_default_catalog())
        old = engine.process_project(project, inputs)
        engine._full_catalog[0].coil_holding_24v_w = '5'
        monkeypatch.setattr(engine, '_resolve_ik', lambda *args: pytest.fail('Invalid device must fail before arithmetic'))
        with pytest.warns(UserWarning, match='Pydantic serializer warnings'), pytest.raises(ValidationError, match='coil_holding_24v_w'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        with pytest.warns(UserWarning, match='Pydantic serializer warnings'):
            LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'coil_holding_24v_w' in messages[0]
    finally:
        i18n.set_language(previous)
