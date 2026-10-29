"""Source structure/linkage tests; generic source labels are not reviewed proof."""

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
from lv_assist.datasheet_validation import datasheet_rows
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import CatalogDevice, FeederInput, LoadType, ProjectSpec

ROOT = Path(__file__).resolve().parents[1]


def source(**changes):
    return {'source_id': 'S', 'manufacturer': 'SYNTHETIC', 'document_ref': 'SYNTHETIC UNREVIEWED LABEL',
            'revision': None, 'data_quality': 'ESTIMATED', **changes}


def device_row(payload_extra=None, **changes):
    payload = CatalogDevice(part_number='T', manufacturer='TEST', series='TEST', device_type='MCB').model_dump(mode='json')
    payload.update(payload_extra or {})
    return {'device_id': 'T', 'category': 'MCB', 'manufacturer': 'TEST', 'series': 'TEST', 'model': 'T',
            'in_a': None, 'icu_ka_400v': None, 'power_loss_w': 0, 'derating_40c': 1, 'derating_50c': 1,
            'width_mm': None, 'height_mm': None, 'depth_mm': None, 'airflow_m3h': None, 'kvar_rating': None,
            'ip_rating': 'IP20', 'ip_numeric': 20, 'poles': None, 'source_id': 'S',
            'data_quality': 'ESTIMATED', 'raw_json': json.dumps(payload), **changes}


@pytest.mark.parametrize('field,value', [
    ('source_id', None), ('source_id', True), ('source_id', ''), ('source_id', ' S'),
    ('source_id', 'S '), ('manufacturer', ' '), ('manufacturer', 1),
    ('manufacturer', 'bad\x00text'), ('document_ref', None), ('document_ref', ''),
    ('document_ref', 'bad\x00text'), ('revision', 2009), ('revision', []),
    ('revision', 'bad\x00text'), ('data_quality', 'UNKNOWN'), ('data_quality', None), ('data_quality', True),
])
def test_source_field_structure_is_checked_without_coercion(field, value):
    with pytest.raises(ValueError):
        datasheet_rows([source(**{field: value})])


def test_duplicate_source_identity_is_not_resolved_by_last_write():
    for second in (source(), source(document_ref='DIFFERENT SYNTHETIC LABEL')):
        with pytest.raises(ValueError, match='duplicate source_id'):
            datasheet_rows([source(), second])


@pytest.mark.parametrize('quality', ['REAL_VERIFIED', 'ESTIMATED', 'UNVERIFIED'])
def test_coarse_source_quality_and_generic_manufacturer_never_promote_device(quality):
    sources = datasheet_rows([source(manufacturer='Generic source bucket', data_quality=quality)])
    item = device_rows([device_row()], sources)[0]
    assert item.data_quality.value == 'ESTIMATED' and item.property_sources == {}
    assert sources['S']['revision'] is None


@pytest.mark.parametrize('revision', ['', 'N/A', 'ویرایش آزمایشی'])
def test_optional_revision_and_multilingual_metadata_are_preserved_without_invented_review(revision):
    record = source(manufacturer='سازنده / Hersteller', document_ref='سند آزمایشی', revision=revision)
    assert datasheet_rows([record]) == {'S': record}


@pytest.mark.parametrize('key', [True, '', ' S', 'MISSING', 's'])
def test_nonnull_sql_link_must_be_valid_and_reference_exact_existing_id(key):
    with pytest.raises(CatalogValidationError, match='source_id'):
        device_rows([device_row(source_id=key)], datasheet_rows([source()]))


@pytest.mark.parametrize('key', [None, 'OTHER', '', True])
def test_explicit_raw_source_id_cannot_disagree_with_sql(key):
    with pytest.raises(CatalogValidationError, match='source_id'):
        device_rows([device_row({'source_id': key})], datasheet_rows([source()]))


def test_absent_links_remain_unknown_and_matching_link_is_not_an_evidence_object():
    for extra in ({}, {'source_id': None}):
        item = device_rows([device_row(extra, source_id=None)])[0]
        assert item.data_quality.value == 'ESTIMATED' and item.property_sources == {}
    item = device_rows([device_row({'source_id': 'S'})], datasheet_rows([source()]))[0]
    assert item.data_quality.value == 'ESTIMATED' and item.property_sources == {}
    with pytest.raises(CatalogValidationError, match='source_id'):
        device_rows([device_row({'source_id': 'S'}, source_id=None)], datasheet_rows([source()]))


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def edit(repo, sql, params=()):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute(sql, params)


@pytest.mark.parametrize('sql', [
    "UPDATE catalog_devices SET source_id='MISSING'",
    "INSERT INTO datasheet_sources VALUES('UNUSED','TEST','',NULL,'ESTIMATED')",
    "UPDATE datasheet_sources SET revision='bad' || char(0)",
])
def test_runtime_rules_and_whole_inventory_fail_without_cached_fallback_or_writes(repo, sql):
    old = repo.devices
    edit(repo, sql)
    before = repo.db_path.read_bytes()
    for read in (lambda: repo.devices, repo.load_selectivity_rules, lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(ValueError):
            read()
    assert old and repo._devices_cache is None and repo.db_path.read_bytes() == before


def test_duplicate_ids_in_weak_actual_source_table_fail_instead_of_overwriting(repo):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        records = connection.execute('SELECT * FROM datasheet_sources').fetchall()
        connection.execute('DROP TABLE datasheet_sources')
        connection.execute('CREATE TABLE datasheet_sources(source_id,manufacturer,document_ref,revision,data_quality)')
        connection.executemany('INSERT INTO datasheet_sources VALUES(?,?,?,?,?)', records + records[:1])
    before = repo.db_path.read_bytes()
    with pytest.raises(ValueError, match='duplicate source_id'):
        validate_catalog_database(repo.db_path)
    assert repo.db_path.read_bytes() == before


def test_empty_source_inventory_with_explicitly_absent_links_is_not_certification(repo):
    edit(repo, 'UPDATE catalog_devices SET source_id=NULL')
    edit(repo, 'DELETE FROM datasheet_sources')
    result = validate_catalog_database(repo.db_path)
    assert result['datasheet_sources'] == result['device_source_links'] == 0
    assert result['engineering_verification'] == 'NOT_VERIFIED'
    assert all(item.data_quality.value == 'ESTIMATED' for item in repo.devices)


def test_actual_cli_counts_records_and_links_and_rejects_dangling_id_without_repair(repo):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and result['status'] == 'STRUCTURALLY_VALID'
    assert result['datasheet_sources'] == 2 and result['device_source_links'] == 102
    assert result['engineering_verification'] == 'NOT_VERIFIED' and repo.db_path.read_bytes() == before
    edit(repo, "UPDATE catalog_devices SET source_id='MISSING'")
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 1 and result['status'] == 'INVALID'
    assert 'source_id' in result['error'] and repo.db_path.read_bytes() == before


def test_missing_source_table_reports_invalid_cli_result_without_writing(repo):
    edit(repo, 'DROP TABLE datasheet_sources')
    before = repo.db_path.read_bytes()
    completed = subprocess.run([sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)],
                               cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1 and json.loads(completed.stdout)['status'] == 'INVALID'
    assert repo.db_path.read_bytes() == before


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_unused_bad_source_fails_engine_and_gui_keeps_previous_run_stale(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        devices = repo.load_devices()
        project = ProjectSpec(project_name='Source link gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(devices).process_project(project, inputs)
        edit(repo, "INSERT INTO datasheet_sources VALUES('UNUSED','TEST','',NULL,'ESTIMATED')")
        engine = engine_module.EngineeringEngine(devices)
        with pytest.raises(ValueError, match='document_ref'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'document_ref' in messages[0]
    finally:
        i18n.set_language(previous)
