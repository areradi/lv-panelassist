"""Synthetic structural domains; no independent curve/reference approval."""

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from lv_assist.catalog import CatalogRepository, TripCurveRepository, catalog_repo
from lv_assist.catalog_validation import (
    CatalogValidationError,
    curve_rows,
    validated_curves,
    validated_rules,
)
from lv_assist.engine import EngineeringEngine
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import FeederInput, LoadType, ProjectSpec, SelectivityRuleRecord

ROOT = Path(__file__).resolve().parents[1]
BASE = {'thermal_k': 90.0, 'alpha': 2.0, 'im_min_mult': 8.0, 'im_max_mult': 12.0}


@pytest.mark.parametrize('field', list(BASE))
@pytest.mark.parametrize('value', [None, True, 0, -1, float('nan'), float('inf'), '8'])
def test_bad_numeric_curve_fields_never_enter_lookup(field, value):
    with pytest.raises(CatalogValidationError):
        validated_curves({'TEST': {**BASE, field: value}})


@pytest.mark.parametrize('changes', [
    {'im_min_mult': 15}, {'points': []}, {'points': [[1, 2]]},
    {'points': [[1, 2], [1, 1]]}, {'points': [[2**53, 2], [2**53 + 1, 1]]}, {'points': [[2, 2], [1, 1]]},
    {'points': [[1, 2], [2, 0]]}, {'points': [[1, 2], [2, float('inf')]]},
    {'points': [[1, 2], [2]]}, {'points': [[1, 2], [True, 1]]},
    {'curve_source': 'DATASHEET_POINTS'}, {'ref': 'Bad\x00text'},
])
def test_invalid_points_ranges_or_source_shape_are_not_repaired(changes):
    with pytest.raises(CatalogValidationError):
        validated_curves({'TEST': {**BASE, **changes}})


@pytest.mark.parametrize('raw', ['[]', '{"alpha":2,"alpha":3}', '{bad json'])
def test_invalid_json_shape_or_duplicate_keys_are_rejected(raw):
    with pytest.raises(ValueError):
        curve_rows([{'curve_id': 'TEST', 'raw_json': raw}])


def test_duplicate_curve_ids_cannot_silently_replace_a_record():
    row = {'curve_id': 'TEST', 'raw_json': json.dumps(BASE)}
    with pytest.raises(CatalogValidationError):
        curve_rows([row, row])


def test_returned_curve_is_detached_and_mutated_cache_is_revalidated(monkeypatch):
    cache = {'TEST': dict(BASE)}
    monkeypatch.setattr(catalog_repo, '_curves_cache', cache)
    curve = TripCurveRepository.get_curve('TEST')
    curve['thermal_k'] = -1
    assert TripCurveRepository.get_curve('TEST')['thermal_k'] == 90
    cache['TEST']['thermal_k'] = -1
    with pytest.raises(CatalogValidationError):
        TripCurveRepository.get_curve('TEST')


def test_actual_engine_refuses_corrupt_auxiliary_data_before_arithmetic(monkeypatch):
    engine = EngineeringEngine(CatalogRepository.get_default_catalog())
    monkeypatch.setattr(catalog_repo, '_curves_cache', {'DEFAULT': {**BASE, 'alpha': 0}})
    def arithmetic(*args):
        pytest.fail('Invalid auxiliary curves must fail before arithmetic')
    monkeypatch.setattr(engine, '_resolve_ik', arithmetic)
    with pytest.raises(CatalogValidationError):
        engine.process_project(ProjectSpec(project_name='Curve test'), [FeederInput(
            feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)])


def test_packaged_curves_unchanged_by_validation_and_cli_is_read_only(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_repo.db_path, path)
    repo = CatalogRepository(path)
    original = repo.trip_curves
    assert len(original) == 16
    assert validated_curves(original) == original
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(path)]
    result = subprocess.run(command, check=False, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload['trip_curves'] == 16 and payload['engineering_verification'] == 'NOT_VERIFIED'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with sqlite3.connect(path) as connection:
        connection.execute('UPDATE trip_curves SET raw_json=? WHERE curve_id=?',
                           (json.dumps({**BASE, 'alpha': -1}), 'DEFAULT'))
    before = path.read_bytes()
    with pytest.raises(CatalogValidationError):
        _ = CatalogRepository(path).trip_curves
    result = subprocess.run(command, check=False, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1 and json.loads(result.stdout)['status'] == 'INVALID'
    assert path.read_bytes() == before


def test_selectivity_reference_text_is_revalidated_after_mutation():
    rule = SelectivityRuleRecord(upstream_series='UP', upstream_min_in_a=1,
        downstream_series='DOWN', downstream_max_in_a=1, selectivity_limit_is_ka=1,
        catalog_reference='Synthetic reference')
    rule.catalog_reference = 'Bad\x00reference'
    with pytest.raises(ValidationError):
        validated_rules([rule])


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_gui_curve_failure_keeps_prior_results_stale(monkeypatch, locale):
    previous = i18n.get_language()
    messages = []
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Curve UI test')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        engine = EngineeringEngine(CatalogRepository.get_default_catalog())
        old = engine.process_project(project, inputs)
        monkeypatch.setattr(catalog_repo, '_curves_cache', {'DEFAULT': {**BASE, 'alpha': -1}})
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs, last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'DEFAULT' in messages[0] and 'alpha' in messages[0]
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_curve_identifiers_and_field_paths_stay_ascii_in_localized_errors(locale):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        with pytest.raises(CatalogValidationError) as error:
            validated_curves({'TEST-123': {**BASE, 'points': [[1, 0], [2, 1]]}})
        assert 'TEST-123' in str(error.value)
        assert 'points[0].time_s' in str(error.value)
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('curves', [None, [], 'invalid', 42])
def test_curve_map_itself_requires_dictionary_shape(curves):
    with pytest.raises(CatalogValidationError):
        validated_curves(curves)


@pytest.mark.parametrize('cache', [[], 'invalid'])
@pytest.mark.parametrize('entry', ['engine', 'lookup'])
def test_invalid_map_cache_has_named_error_before_arithmetic(monkeypatch, cache, entry):
    engine = EngineeringEngine(CatalogRepository.get_default_catalog())
    monkeypatch.setattr(catalog_repo, '_curves_cache', cache)
    with pytest.raises(CatalogValidationError):
        if entry == 'lookup':
            TripCurveRepository.get_curve('TEST')
        else:
            project = ProjectSpec(project_name='Invalid curve map')
            inputs = [FeederInput(feeder_id='F1', description='Test',
                                  load_type=LoadType.SUB_FEEDER, power_kw=1)]
            engine.process_project(project, inputs)
