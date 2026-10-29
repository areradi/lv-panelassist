"""PE structural policy checks; synthetic values are not engineering references."""

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
from lv_assist.catalog_validation import validate_catalog_database
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.rating_table_validation import pe_sections

ROOT = Path(__file__).resolve().parents[1]
INVALID = [None, True, False, 0, -1, float('nan'), float('inf'), -float('inf'), '16', 2**10000]


@pytest.mark.parametrize('value', INVALID, ids=['none', 'true', 'false', 'zero', 'negative', 'nan', 'inf', 'minus-inf', 'text', 'overflow'])
def test_section_helper_rejects_invalid_native_values(value):
    with pytest.raises(ValueError, match='section_mm2'):
        pe_sections([{'section_mm2': value}])


def test_sections_sorted_without_rounding_or_invented_ceiling():
    values = [1000, 16.00001, 1.5, 16]
    assert pe_sections({'section_mm2': value} for value in values) == sorted(values)
    with pytest.raises(ValueError, match='duplicate section_mm2'):
        pe_sections([{'section_mm2': 16}, {'section_mm2': 16.0}])


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def replace_sections(repo, values):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        # Deliberately weak copied schema: exercise parser, not SQL constraints.
        connection.execute('DROP TABLE pe_standard_sections')
        connection.execute('CREATE TABLE pe_standard_sections(section_mm2)')
        connection.executemany('INSERT INTO pe_standard_sections VALUES (?)', [(value,) for value in values])


@pytest.mark.parametrize('value', INVALID, ids=['none', 'true', 'false', 'zero', 'negative', 'nan', 'inf', 'minus-inf', 'text', 'overflow'])
def test_runtime_requirement_rejects_invalid_arguments(repo, value):
    with pytest.raises(ValueError, match='required_pe_mm2'):
        repo.get_standard_pe_section(value)


@pytest.mark.parametrize('value', [None, 0, -1, float('inf'), '16', 'bad'])
@pytest.mark.parametrize('access', ['list', 'selection', 'inventory'])
def test_bad_row_anywhere_rejects_lookup_and_whole_inventory_without_writes(repo, value, access):
    replace_sections(repo, [value, 16, 50])
    before = repo.db_path.read_bytes()
    with pytest.raises(ValueError, match='section_mm2'):
        if access == 'list':
            repo.get_pe_standard_sections()
        elif access == 'selection':
            repo.get_standard_pe_section(35)
        else:
            validate_catalog_database(repo.db_path)
    assert repo.db_path.read_bytes() == before


def test_lookup_boundaries_empty_table_and_no_extrapolation(repo):
    replace_sections(repo, [1000, 16.00001, 1.5, 16])
    for requirement, expected in [(0.01, 1.5), (1.5, 1.5), (1.50001, 16),
                                  (16, 16), (16.000001, 16.00001), (17, 1000), (1001, None)]:
        assert repo.get_standard_pe_section(requirement) == expected
    assert validate_catalog_database(repo.db_path)['pe_sections'] == 4
    replace_sections(repo, [])
    assert repo.get_pe_standard_sections() == []
    assert repo.get_standard_pe_section(1) is None
    result = validate_catalog_database(repo.db_path)
    assert result['pe_sections'] == 0 and result['engineering_verification'] == 'NOT_VERIFIED'


def test_duplicate_cannot_be_hidden_and_bad_replacement_cannot_reuse_cache(repo):
    good = repo.get_pe_standard_sections()
    before = repo.db_path.read_bytes()
    replace_sections(repo, [16, 16.0])
    for read in (repo.get_pe_standard_sections, lambda: repo.get_standard_pe_section(17),
                 lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(ValueError, match='duplicate section_mm2'):
            read()
    assert repo._pe_cache is None
    repo.db_path.write_bytes(before)
    assert repo.get_pe_standard_sections() == good


def test_mutated_cached_sections_are_rechecked_before_selection(repo):
    repo.get_pe_standard_sections().append(-1)
    with pytest.raises(ValueError, match='section_mm2'):
        repo.get_standard_pe_section(16)


def test_actual_cli_checks_unused_pe_rows_and_missing_table(repo):
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result['status'] == 'STRUCTURALLY_VALID' and result['pe_sections'] == 17
    assert result['engineering_verification'] == 'NOT_VERIFIED'
    assert repo.db_path.read_bytes() == before
    replace_sections(repo, [16, -1])
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result['status'] == 'INVALID' and 'pe_standard_sections' in result['error']
    assert repo.db_path.read_bytes() == before
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute('DROP TABLE pe_standard_sections')
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1 and json.loads(completed.stdout)['status'] == 'INVALID'
    assert repo.db_path.read_bytes() == before


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_bad_pe_table_fails_engine_and_gui_preserves_previous_results(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='PE gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(repo.devices).process_project(project, inputs)
        replace_sections(repo, [16, -1])
        engine = engine_module.EngineeringEngine(repo.devices)
        with pytest.raises(ValueError, match='pe_standard_sections'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'pe_standard_sections' in messages[0]
    finally:
        i18n.set_language(previous)
