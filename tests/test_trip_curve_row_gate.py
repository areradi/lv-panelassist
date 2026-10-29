"""SQL/JSON consistency and preliminary-only flags on synthetic/copied curves."""

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
from lv_assist.catalog import CatalogRepository, TripCurveRepository
from lv_assist.catalog_validation import (
    CatalogValidationError,
    curve_rows,
    validate_catalog_database,
    validated_curves,
)
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import FeederInput, LoadType, ProjectSpec

ROOT = Path(__file__).resolve().parents[1]
BASE = {'thermal_k': 90, 'alpha': 2, 'im_min_mult': 8, 'im_max_mult': 12}


def row(**changes):
    return {'curve_id': 'TEST', 'curve_name': 'Synthetic curve', 'device_category': None,
            'inst_min_mult': 8, 'inst_max_mult': 12, 'is_approximate': 1,
            'allow_for_verification': 0, 'raw_json': json.dumps(BASE), **changes}


@pytest.mark.parametrize('field,value', [
    ('curve_name', None), ('curve_name', ' '), ('curve_name', 'bad\x00text'),
    ('device_category', ''), ('device_category', 'bad\x00text'),
    ('inst_min_mult', True), ('inst_min_mult', 0), ('inst_min_mult', -1),
    ('inst_min_mult', '8'), ('inst_min_mult', None), ('inst_min_mult', float('inf')),
    ('inst_min_mult', float('nan')), ('inst_min_mult', 9), ('inst_max_mult', 11),
    ('is_approximate', 0), ('is_approximate', 2), ('is_approximate', True),
    ('is_approximate', '1'), ('is_approximate', None),
    ('allow_for_verification', 1), ('allow_for_verification', False), ('allow_for_verification', '0'),
])
def test_sql_domains_and_threshold_mismatches_rejected(field, value):
    with pytest.raises(CatalogValidationError):
        curve_rows([row(**{field: value})])


@pytest.mark.parametrize('field,value', [
    ('is_approximate', False), ('is_approximate', 0), ('is_approximate', 2),
    ('is_approximate', '1'), ('is_approximate', 1.0), ('is_approximate', None),
    ('allow_for_verification', True), ('allow_for_verification', 1),
    ('allow_for_verification', '0'), ('allow_for_verification', 0.0), ('allow_for_verification', None),
])
def test_json_policy_flags_cannot_promote_or_coerce_curve(field, value):
    with pytest.raises(CatalogValidationError, match=field):
        validated_curves({'TEST': {**BASE, field: value}})


@pytest.mark.parametrize('field,value', [('name', 'Different label'), ('category', 'MCB'), ('id', 'OTHER')])
def test_explicit_json_metadata_must_match_sql(field, value):
    with pytest.raises(CatalogValidationError):
        curve_rows([row(raw_json=json.dumps({**BASE, field: value}))])


@pytest.mark.parametrize('field', ['name', 'category', 'id'])
def test_supplied_metadata_cannot_be_blank(field):
    with pytest.raises(CatalogValidationError, match=field):
        validated_curves({'TEST': {**BASE, field: ' '}})


@pytest.mark.parametrize('name', [None, True, [], '', ' ', 'bad\x00id'])
def test_bad_curve_identity_has_validation_error_before_dictionary_access(name):
    with pytest.raises(CatalogValidationError):
        curve_rows([row(curve_id=name)])


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def replace_rows(repo, rows):
    # Weak copied schema isolates parser checks from original SQL CHECK clauses.
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute('DROP TABLE trip_curves')
        connection.execute('CREATE TABLE trip_curves(curve_id, curve_name, device_category, inst_min_mult, inst_max_mult, is_approximate, allow_for_verification, raw_json)')
        fields = list(row())
        connection.executemany('INSERT INTO trip_curves VALUES (?,?,?,?,?,?,?,?)',
                               [tuple(item[field] for field in fields) for item in rows])


@pytest.mark.parametrize('flags', [(True, False), (1, 0)])
def test_point_curves_and_explicit_metadata_preserved_without_source_approval(repo, monkeypatch, flags):
    payload = {**BASE, 'id': 'TEST', 'name': 'Synthetic curve', 'category': 'SYNTHETIC',
               'points': [[2, 10], [4, 2]], 'curve_source': 'DATASHEET_POINTS',
               'datasheet_ref': 'SYNTHETIC UNREVIEWED REFERENCE',
               'is_approximate': flags[0], 'allow_for_verification': flags[1]}
    replace_rows(repo, [row(device_category='SYNTHETIC', raw_json=json.dumps(payload))])
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    assert TripCurveRepository.get_curve('TEST') == payload
    assert TripCurveRepository.thermal_time_s('TEST', 2) == 10
    result = validate_catalog_database(repo.db_path)
    assert result['trip_curves'] == 1 and result['trip_curve_policy'] == 'APPROXIMATE_ONLY'
    assert result['engineering_verification'] == 'NOT_VERIFIED'


@pytest.mark.parametrize('changes', [
    {'inst_min_mult': 9}, {'allow_for_verification': 1}, {'is_approximate': 0},
    {'inst_max_mult': '12'}, {'curve_name': ''},
])
def test_unused_bad_row_rejects_complete_runtime_and_cli_inventory_without_cached_fallback(repo, changes):
    old = repo.trip_curves
    replace_rows(repo, [row(), row(curve_id='UNUSED', **changes)])
    before = repo.db_path.read_bytes()
    for read in (lambda: repo.trip_curves, lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(CatalogValidationError):
            read()
    assert old and repo._curves_cache is None and repo.db_path.read_bytes() == before


def test_actual_cli_reports_policy_and_errors_without_writing_or_repair(repo):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and result['status'] == 'STRUCTURALLY_VALID'
    assert result['trip_curves'] == 16 and result['trip_curve_policy'] == 'APPROXIMATE_ONLY'
    assert result['engineering_verification'] == 'NOT_VERIFIED' and repo.db_path.read_bytes() == before
    replace_rows(repo, [row(allow_for_verification=1)])
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 1 and result['status'] == 'INVALID'
    assert 'allow_for_verification' in result['error'] and repo.db_path.read_bytes() == before


def test_empty_table_and_missing_required_column_are_not_fabricated(repo):
    replace_rows(repo, [])
    assert repo.trip_curves == {}
    result = validate_catalog_database(repo.db_path)
    assert result['trip_curves'] == 0 and result['engineering_verification'] == 'NOT_VERIFIED'
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute('ALTER TABLE trip_curves RENAME COLUMN is_approximate TO missing_flag')
    before = repo.db_path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):
        _ = repo.trip_curves
    completed = subprocess.run([sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)],
                               cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1 and json.loads(completed.stdout)['status'] == 'INVALID'
    assert repo.db_path.read_bytes() == before


@pytest.mark.parametrize('entry', ['lookup', 'engine'])
def test_cached_json_policy_mutation_is_revalidated_before_arithmetic(repo, monkeypatch, entry):
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    repo.trip_curves['DEFAULT']['allow_for_verification'] = True
    if entry == 'lookup':
        with pytest.raises(CatalogValidationError, match='allow_for_verification'):
            TripCurveRepository.get_curve('DEFAULT')
    else:
        engine = engine_module.EngineeringEngine(repo.devices)
        monkeypatch.setattr(engine, '_resolve_ik', lambda *args: pytest.fail('Invalid curve must fail before arithmetic'))
        with pytest.raises(CatalogValidationError, match='allow_for_verification'):
            engine.process_project(ProjectSpec(project_name='Policy mutation'), [FeederInput(
                feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)])


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_bad_sql_policy_fails_engine_and_gui_keeps_stale_prior_run(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Curve row gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(repo.devices).process_project(project, inputs)
        replace_rows(repo, [row(allow_for_verification=1)])
        engine = engine_module.EngineeringEngine(repo.devices)
        with pytest.raises(CatalogValidationError, match='allow_for_verification'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'allow_for_verification' in messages[0]
    finally:
        i18n.set_language(previous)
