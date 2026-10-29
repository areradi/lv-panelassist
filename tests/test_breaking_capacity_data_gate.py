"""Structural Icu/Ics checks on synthetic rows; no engineering certification."""

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
    breaking_capacity_rows,
    validate_catalog_database,
)
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import FeederInput, LoadType, ProjectSpec

ROOT = Path(__file__).resolve().parents[1]
PART = '5SY4206-7'
BAD = [True, False, 0, -1, float('nan'), float('inf'), '10', 2**10000]
BAD_IDS = ['true', 'false', 'zero', 'negative', 'nan', 'inf', 'text', 'overflow']


@pytest.mark.parametrize('field', ['voltage_v', 'icu_ka', 'ics_ka'])
@pytest.mark.parametrize('value', BAD, ids=BAD_IDS)
def test_native_rating_numbers_reject_bad_domains(field, value):
    row = {'device_id': PART, 'voltage_v': 400, 'icu_ka': 10, 'ics_ka': 5, field: value}
    with pytest.raises(CatalogValidationError, match=field):
        breaking_capacity_rows([row], {PART})


def test_only_ics_may_be_missing_and_it_is_never_filled_from_icu():
    row = {'device_id': PART, 'voltage_v': 400, 'icu_ka': 10, 'ics_ka': None}
    assert breaking_capacity_rows([row], {PART}) == {(PART, 400): (10, None)}
    for field in ['voltage_v', 'icu_ka']:
        with pytest.raises(CatalogValidationError, match=field):
            breaking_capacity_rows([{**row, field: None}], {PART})


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def replace_rows(repo, rows):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        # Weak copied schema exercises parser independently from SQL constraints.
        connection.execute('DROP TABLE device_breaking_capacities')
        connection.execute('CREATE TABLE device_breaking_capacities(device_id, voltage_v, icu_ka, ics_ka)')
        connection.executemany('INSERT INTO device_breaking_capacities VALUES (?,?,?,?)', rows)


@pytest.mark.parametrize('value', [None, *BAD], ids=['none', *BAD_IDS])
def test_runtime_voltage_domain(repo, value):
    with pytest.raises(ValueError, match='nominal_voltage_v'):
        repo.get_device_icu_at_voltage(PART, value)


@pytest.mark.parametrize('value', [None, True, False, float('nan'), float('inf'), '0', 2**10000],
                         ids=['none', 'true', 'false', 'nan', 'inf', 'text', 'overflow'])
def test_tolerance_must_be_native_finite_zero(repo, value):
    with pytest.raises(ValueError, match='tolerance_v'):
        repo.get_device_icu_at_voltage(PART, 400, value)


@pytest.mark.parametrize('value', [None, True, '', '  ', 'bad\x00id'])
def test_runtime_identity_is_valid_exportable_text(repo, value):
    with pytest.raises(ValueError):
        repo.get_device_icu_at_voltage(value, 400)


def test_exact_conditions_distinct_voltages_no_fallback_and_optional_ics(repo):
    replace_rows(repo, [(PART, 400, 10, None), (PART, 415, 6, 3)])
    assert repo.get_device_icu_at_voltage(PART, 400) == 10
    assert repo.get_device_icu_at_voltage(PART, 415) == 6
    assert repo.get_device_icu_at_voltage(PART, 401) is None
    assert repo.get_device_icu_at_voltage('UNKNOWN', 400) is None
    for tolerance in [-1, 1]:
        with pytest.raises(ValueError, match='applicability'):
            repo.get_device_icu_at_voltage(PART, 401, tolerance)
    result = validate_catalog_database(repo.db_path)
    assert result['breaking_capacity_rows'] == 2 and result['breaking_capacity_devices'] == 1
    assert result['engineering_verification'] == 'NOT_VERIFIED'
    replace_rows(repo, [])
    assert repo.get_device_icu_at_voltage(PART, 400) is None
    assert validate_catalog_database(repo.db_path)['breaking_capacity_rows'] == 0


@pytest.mark.parametrize('bad_row', [
    (PART, 415, 0, None), (PART, 415, None, None), (PART, -1, 10, None),
    (PART, 415, '10', None), (PART, 415, float('inf'), None),
    (PART, 415, 10, -1), (PART, 415, 10, '5'),
    (PART, 400.0, 10, None),
])
def test_all_rows_for_device_checked_before_exact_lookup_and_cli(repo, bad_row):
    replace_rows(repo, [(PART, 400, 10, None), bad_row])
    before = repo.db_path.read_bytes()
    for read in (lambda: repo.get_device_icu_at_voltage(PART, 400),
                 lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(CatalogValidationError):
            read()
    assert repo.db_path.read_bytes() == before


def test_dangling_reference_fails_runtime_and_inventory(repo):
    replace_rows(repo, [('MISSING', 400, 10, None)])
    for read in (lambda: repo.get_device_icu_at_voltage('MISSING', 400),
                 lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(CatalogValidationError, match='unknown device_id'):
            read()


def test_lookup_detects_file_version_change_and_sidecar(repo, monkeypatch):
    with monkeypatch.context() as changed:
        values = iter(['before', 'after'])
        changed.setattr(catalog_module, 'catalog_file_hash', lambda path: next(values))
        with pytest.raises(CatalogValidationError):
            repo.get_device_icu_at_voltage(PART, 400)
    sidecar = Path(str(repo.db_path) + '-wal')
    sidecar.write_bytes(b'synthetic sidecar')
    before = repo.db_path.read_bytes()
    with pytest.raises(ValueError):
        repo.get_device_icu_at_voltage(PART, 400)
    assert sidecar.read_bytes() == b'synthetic sidecar' and repo.db_path.read_bytes() == before


def test_actual_cli_inventory_invalid_unused_row_and_missing_table(repo):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and result['status'] == 'STRUCTURALLY_VALID'
    assert result['breaking_capacity_rows'] == 70 and result['engineering_verification'] == 'NOT_VERIFIED'
    assert repo.db_path.read_bytes() == before
    replace_rows(repo, [('MISSING', 999, 10, None)])
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 1 and result['status'] == 'INVALID'
    assert 'device_id' in result['error'] and repo.db_path.read_bytes() == before
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute('DROP TABLE device_breaking_capacities')
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1 and json.loads(completed.stdout)['status'] == 'INVALID'
    assert repo.db_path.read_bytes() == before


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_corrupted_rating_fails_engine_and_gui_retains_stale_previous_results(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Breaking capacity gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(repo.devices).process_project(project, inputs)
        with closing(sqlite3.connect(repo.db_path)) as connection, connection:
            connection.execute('PRAGMA ignore_check_constraints=ON')
            connection.execute('UPDATE device_breaking_capacities SET icu_ka=-1')
        engine = engine_module.EngineeringEngine(repo.devices)
        with pytest.raises(CatalogValidationError, match='icu_ka'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'icu_ka' in messages[0]
    finally:
        i18n.set_language(previous)
