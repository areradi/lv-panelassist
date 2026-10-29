"""Registry structure tests on synthetic/copy data, not engineering references."""

import hashlib
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
import lv_assist.run_metadata as metadata_module
from lv_assist.catalog import CatalogRepository, StandardsRegistry
from lv_assist.catalog_validation import validate_catalog_database
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.registry_validation import registry_entries, registry_rows
from lv_assist.run_metadata import registry_hash

ROOT = Path(__file__).resolve().parents[1]
ENTRY = {'title': {'en': 'Synthetic reference', 'fa': 'مرجع آزمایشی'}, 'scope': {'en': 'Synthetic scope'}}


@pytest.mark.parametrize('raw', [
    None, 4, b'{}', '{', '[]', 'null', '{}',
    '{"code":"A","code":"B"}', '{"code":null}', '{"code":" "}',
    '{"code":"STD","edition":2009}', '{"code":"STD","id":"OTHER"}',
    '{"title":"text"}', '{"title":{}}', '{"title":{"en":null}}',
    '{"title":{"en":" "}}', '{"title":{"en":"Test"},"scope":[]}',
    '{"REF":{"scope":{"en":"Missing title"}}}',
    '{"title":{"en":"Test","en":"Overwrite"}}',
    '{"title":{"en":"bad\\u0000text"}}',
    '{"code":"STD","extra":NaN}', '{"code":"STD","extra":1e999}',
    '{"code":"STD","extra":"\\ud800"}',
    '{"\\ud800":1,"\\ud800":2}',
])
def test_malformed_raw_payload_is_rejected_without_coercion_or_silent_skip(raw):
    with pytest.raises(ValueError):
        registry_rows([{'standard_id': 'STD', 'raw_json': raw}])


@pytest.mark.parametrize('standard_id', [None, True, '', ' ', ' STD', 'STD ', 'bad\x00id'])
def test_invalid_stored_identity(standard_id):
    with pytest.raises(ValueError):
        registry_rows([{'standard_id': standard_id, 'raw_json': '{"code":"STD"}'}])


def test_duplicate_row_ids_are_not_resolved_by_last_write():
    row = {'standard_id': 'STD', 'raw_json': '{"code":"STD"}'}
    with pytest.raises(ValueError, match='duplicate standard_id'):
        registry_rows([row, row])


@pytest.mark.parametrize('reverse', [False, True])
def test_localized_duplicate_across_collection_and_direct_rows_rejected(reverse):
    rows = [{'standard_id': 'REF', 'raw_json': json.dumps(ENTRY)},
            {'standard_id': 'collection', 'raw_json': json.dumps({'REF': ENTRY})}]
    with pytest.raises(ValueError, match='duplicate localized standard_id'):
        registry_rows(list(reversed(rows)) if reverse else rows)


def test_supported_shapes_keep_data_and_missing_edition_without_inventing_source():
    payloads = {'STD': {'code': 'Synthetic STD', 'edition': None, 'extra': {'notes': ['Test']}},
                'REF': ENTRY, 'collection': {'id': 'collection', 'ALT': {'title': {'de': 'Test'}}}}
    result = registry_rows({'standard_id': key, 'raw_json': json.dumps(value)} for key, value in payloads.items())
    assert result == payloads
    entries = registry_entries(result)
    assert set(entries) == {'REF', 'ALT'} and entries['REF'] == ENTRY
    assert result['STD']['edition'] is None
    assert registry_rows([]) == {} and registry_entries({}) == {}


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def edit_registry(repo, raw):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute("UPDATE standards_registry SET raw_json=? WHERE standard_id='IEC-60364-5-52'", (raw,))


@pytest.mark.parametrize('raw', ['[]', '{"code":"A","code":"B"}', '{"code":"A","extra":NaN}',
                                  '{"title":{"en":"bad\\u0000text"}}'])
def test_actual_cache_hash_and_inventory_reject_bad_unused_registry_row_without_writes(repo, raw):
    old = repo.standards
    edit_registry(repo, raw)
    before = repo.db_path.read_bytes()
    for read in (lambda: repo.standards, lambda: registry_hash(repo.db_path),
                 lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(ValueError):
            read()
    assert repo._standards_cache is None
    assert old and repo.db_path.read_bytes() == before


def test_display_uses_validated_cache_and_preserves_language_fallbacks(repo, monkeypatch):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    try:
        # Explicitly supplying cached synthetic rows also tests validation on read.
        repo.standards.clear()
        repo.standards.update(json.loads(json.dumps({'REF': ENTRY, 'ALT': {'title': {'de': 'Test'}}})))
        i18n.set_language('fa')
        assert StandardsRegistry.title('REF') == 'مرجع آزمایشی'
        assert StandardsRegistry.scope('REF') == 'Synthetic scope'
        i18n.set_language('de')
        assert StandardsRegistry.title('REF') == 'Synthetic reference'
        assert StandardsRegistry.title('ALT') == 'Test'
        assert StandardsRegistry.title('UNKNOWN') == 'UNKNOWN'
        assert StandardsRegistry.scope('UNKNOWN') == ''
        repo.standards['REF']['title'] = 'bad mutation'
        with pytest.raises(ValueError, match='title'):
            StandardsRegistry.title('REF')
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('standard_id', [None, True, '', ' ', 'bad\x00id'])
def test_display_request_identity_is_checked(standard_id):
    for lookup in [StandardsRegistry.title, StandardsRegistry.scope]:
        with pytest.raises(ValueError):
            lookup(standard_id)


def test_registry_hash_keeps_original_raw_row_identity_and_detects_version_changes(repo, monkeypatch):
    with closing(sqlite3.connect(repo.db_path)) as connection:
        rows = connection.execute('SELECT standard_id, raw_json FROM standards_registry ORDER BY standard_id').fetchall()
    expected = hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
    assert registry_hash(repo.db_path) == expected
    edit_registry(repo, rows[0][1] + ' ')
    assert registry_hash(repo.db_path) != expected
    hashes = iter(['before', 'after'])
    monkeypatch.setattr(metadata_module, 'catalog_file_hash', lambda path: next(hashes))
    with pytest.raises(ValueError):
        registry_hash(repo.db_path)


@pytest.mark.parametrize('raw', ['[]', '{"\\ud800":1,"\\ud800":2}'])
def test_actual_cli_reports_registry_scope_and_rejects_unused_bad_json(repo, raw):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and result['status'] == 'STRUCTURALLY_VALID'
    assert result['standards_registry_rows'] == 2 and result['localized_standard_entries'] == 16
    assert result['engineering_verification'] == 'NOT_VERIFIED' and repo.db_path.read_bytes() == before
    edit_registry(repo, raw)
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1 and json.loads(completed.stdout)['status'] == 'INVALID'
    assert repo.db_path.read_bytes() == before


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_invalid_registry_prevents_engine_result_and_gui_keeps_prior_run(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Registry gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(repo.devices).process_project(project, inputs)
        edit_registry(repo, '{"title":"bad title shape"}')
        engine = engine_module.EngineeringEngine(repo.devices)
        with pytest.raises(ValueError, match='title'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'title' in messages[0]
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('suffix', ['-wal', '-journal'])
def test_registry_display_and_hash_reject_untracked_sidecar_without_changes(repo, monkeypatch, suffix):
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    _ = repo.standards
    sidecar = Path(str(repo.db_path) + suffix)
    sidecar.write_bytes(b'synthetic indicator')
    before = repo.db_path.read_bytes()
    for read in (lambda: StandardsRegistry.title('IEC 60909-0'), lambda: registry_hash(repo.db_path)):
        with pytest.raises(ValueError):
            read()
    assert repo.db_path.read_bytes() == before and sidecar.read_bytes() == b'synthetic indicator'


def test_cyclic_or_nonfinite_cached_payload_cannot_reach_display():
    cyclic = {'REF': {'title': {'en': 'Test'}}}
    cyclic['REF']['extra'] = cyclic
    with pytest.raises(ValueError):
        registry_entries(cyclic)
    with pytest.raises(ValueError):
        registry_entries({'REF': {**ENTRY, 'extra': float('inf')}})
