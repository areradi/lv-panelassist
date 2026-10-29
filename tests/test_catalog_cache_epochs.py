"""External catalog edits use copied databases; packaged bytes are never changed."""

import copy
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

import lv_assist.catalog as catalog_module
import lv_assist.engine as engine_module
from lv_assist.catalog import CatalogRepository
from lv_assist.catalog_validation import CatalogValidationError
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.run_metadata import catalog_file_hash


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def edit(path, operation):
    connection = sqlite3.connect(path)
    try:
        with connection:
            operation(connection)
    finally:
        connection.close()


def read(repo, name):
    if name == 'pe':
        return repo.get_pe_standard_sections()
    return getattr(repo, name)


NAMES = ['devices', 'trip_curves', 'standards', 'selectivity_rules', 'pe']


@pytest.mark.parametrize('name', NAMES)
def test_each_cache_reloads_actual_changed_data_without_device_access(repo, name):
    before = copy.deepcopy(read(repo, name))
    def change(connection):
        if name == 'pe':
            connection.execute('UPDATE pe_standard_sections SET section_mm2=section_mm2 * 1.001')
            return
        table = {'devices': 'catalog_devices', 'trip_curves': 'trip_curves',
                 'standards': 'standards_registry', 'selectivity_rules': 'selectivity_rules'}[name]
        # rowid avoids assumptions about identity-column names in copied schemas.
        rowid, raw = connection.execute(f'SELECT rowid, raw_json FROM {table} LIMIT 1').fetchone()
        payload = json.loads(raw)
        if name == 'devices':
            payload['series'] += ' SYNTHETIC CACHE REVISION'
        elif name == 'trip_curves':
            payload['im_max_mult'] += 1
        elif name == 'standards':
            payload['synthetic_cache_revision'] = 1
        else:
            payload['catalog_reference'] += ' SYNTHETIC CACHE REVISION'
        connection.execute(f'UPDATE {table} SET raw_json=? WHERE rowid=?', (json.dumps(payload), rowid))
    edit(repo.db_path, change)
    assert read(repo, name) != before


@pytest.mark.parametrize('first', NAMES)
def test_any_accessor_invalidates_all_other_cached_tables(repo, first):
    old = {name: read(repo, name) for name in NAMES}
    edit(repo.db_path, lambda connection: connection.execute('PRAGMA user_version=987'))
    assert read(repo, first) is not old[first]
    assert all(read(repo, name) is not old[name] for name in NAMES)
    assert all(read(repo, name) is read(repo, name) for name in NAMES)


def test_invalid_replacement_never_falls_back_to_cached_good_curve(repo):
    before = repo.db_path.read_bytes()
    old = repo.trip_curves
    edit(repo.db_path, lambda connection: connection.execute("UPDATE trip_curves SET raw_json='{'"))
    for _ in range(2):
        with pytest.raises(ValueError):
            _ = repo.trip_curves
    assert repo._curves_cache is None and repo._cache_file_hash is None
    repo.db_path.write_bytes(before)
    assert repo.trip_curves == old and repo.trip_curves is not old


def test_change_during_loader_rejects_the_loaded_value(repo, monkeypatch):
    original = repo.load_devices
    def load():
        devices = original()
        edit(repo.db_path, lambda connection: connection.execute('PRAGMA user_version=988'))
        return devices
    monkeypatch.setattr(repo, 'load_devices', load)
    with pytest.raises(CatalogValidationError):
        _ = repo.devices
    assert repo._devices_cache is None and repo._cache_file_hash is None
    monkeypatch.setattr(repo, 'load_devices', original)
    assert repo.devices


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('suffix', ['-wal', '-journal'])
def test_nonempty_sidecar_is_rejected_without_repair_or_cached_fallback(repo, locale, suffix):
    previous = i18n.get_language()
    before = repo.db_path.read_bytes()
    _ = repo.trip_curves
    sidecar = Path(str(repo.db_path) + suffix)
    sidecar.write_bytes(b'synthetic sidecar indicator')
    try:
        i18n.set_language(locale)
        with pytest.raises(ValueError) as caught:
            _ = repo.trip_curves
        assert str(caught.value) == tr('audit_catalog_unstable')
        assert repo._curves_cache is None
        assert repo.db_path.read_bytes() == before
        assert sidecar.read_bytes() == b'synthetic sidecar indicator'
    finally:
        i18n.set_language(previous)


def test_old_engine_rejects_changed_file_new_engine_uses_fresh_epoch(repo, monkeypatch):
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    engine = engine_module.EngineeringEngine(repo.devices)
    project = ProjectSpec(project_name='Catalog version test')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    _, old_summary, _ = engine.process_project(project, inputs)
    old_hash = old_summary.run_metadata.catalog_version
    def change(connection):
        raw = connection.execute("SELECT raw_json FROM trip_curves WHERE curve_id='DEFAULT'").fetchone()[0]
        payload = json.loads(raw)
        payload['thermal_k'] = 180
        connection.execute("UPDATE trip_curves SET raw_json=? WHERE curve_id='DEFAULT'", (json.dumps(payload),))
    edit(repo.db_path, change)
    with pytest.raises(ValueError):
        engine.process_project(project, inputs)
    fresh_engine = engine_module.EngineeringEngine(repo.devices)
    _, summary, _ = fresh_engine.process_project(project, inputs)
    assert summary.run_metadata.catalog_version != old_hash
    assert summary.run_metadata.catalog_version == catalog_file_hash(repo.db_path)
    assert catalog_module.TripCurveRepository.thermal_time_s('DEFAULT', 2) == 45
