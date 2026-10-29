"""Synthetic structural cases; SQL labels never supply engineering evidence."""

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
from lv_assist.catalog import CatalogRepository, SiemensSelectivityRepository
from lv_assist.catalog_validation import (
    CatalogValidationError,
    selectivity_rows,
    validate_catalog_database,
)
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import (
    CatalogDevice,
    FeederInput,
    LoadType,
    ProjectSpec,
    SelectivityEvalState,
    SelectivityRuleRecord,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = {'upstream_series': 'UP', 'upstream_min_in_a': 100,
        'downstream_series': 'DOWN', 'downstream_max_in_a': 50,
        'selectivity_limit_is_ka': 10, 'catalog_reference': 'SYNTHETIC',
        'is_total_up_to_icu': False}
DEVICES = [CatalogDevice(part_number=part, manufacturer='TEST', series=series, device_type='MCCB', rated_current_in_a=current)
           for part, series, current in [('U', 'UP', 100), ('D', 'DOWN', 50)]]


def sql_row(**changes):
    return {'rule_id': 1, 'upstream_series': 'UP', 'downstream_series': 'DOWN',
            'upstream_in_min_a': 100, 'upstream_in_max_a': None, 'downstream_in_max_a': 50,
            'min_ratio': None, 'limit_ka': 10, 'selectivity_type': 'VERIFIED_PARTIAL',
            'voltage_v': 400, 'is_verified_manufacturer_rule': 1,
            'raw_json': json.dumps(BASE), **changes}


@pytest.mark.parametrize('field,value', [
    ('upstream_series', ''), ('downstream_series', ' '), ('catalog_reference', '\t'),
    ('upstream_part_number', ''), ('downstream_part_number', ' '),
    ('upstream_min_in_a', True), ('upstream_min_in_a', '100'),
    ('downstream_max_in_a', False), ('selectivity_limit_is_ka', '10'),
    ('operating_voltage_v', True), ('upstream_setting_a', '100'), ('downstream_setting_a', True),
    ('is_total_up_to_icu', 'false'), ('is_total_up_to_icu', 1), ('unknown_condition', 7),
])
def test_model_rejects_blank_coerced_or_unrepresented_rule_conditions(field, value):
    with pytest.raises(ValueError):
        SelectivityRuleRecord.model_validate({**BASE, field: value})


@pytest.mark.parametrize('field,value', [
    ('rule_id', 0), ('rule_id', True), ('rule_id', '1'), ('rule_id', 2**63),
    ('is_verified_manufacturer_rule', True), ('is_verified_manufacturer_rule', '1'),
    ('is_verified_manufacturer_rule', 2), ('is_verified_manufacturer_rule', None),
    ('upstream_series', 'OTHER'), ('downstream_series', 'OTHER'),
    ('upstream_in_min_a', -1), ('upstream_in_min_a', 101), ('upstream_in_min_a', '100'),
    ('downstream_in_max_a', 0), ('downstream_in_max_a', 51), ('limit_ka', 11),
    ('limit_ka', float('inf')), ('voltage_v', 0), ('voltage_v', True),
    ('upstream_in_max_a', 99), ('upstream_in_max_a', 200), ('min_ratio', 0), ('min_ratio', 1.6),
    ('selectivity_type', 'VERIFIED_TOTAL'), ('selectivity_type', 'OTHER'),
    ('raw_json', None), ('raw_json', '[]'), ('raw_json', '{"a":1,"a":2}'),
])
def test_sql_domains_and_json_mismatches_rejected(field, value):
    with pytest.raises(CatalogValidationError):
        selectivity_rows([sql_row(**{field: value})], DEVICES)


def test_exact_voltage_and_optional_part_references_must_match():
    for payload in [{**BASE, 'operating_voltage_v': 415},
                    {**BASE, 'upstream_part_number': 'MISSING'},
                    {**BASE, 'upstream_part_number': 'D'},
                    {**BASE, 'downstream_part_number': 'MISSING'}]:
        with pytest.raises(CatalogValidationError):
            selectivity_rows([sql_row(raw_json=json.dumps(payload))], DEVICES)
    payload = {**BASE, 'operating_voltage_v': 400, 'upstream_part_number': 'U', 'downstream_part_number': 'D'}
    all_rules, enabled = selectivity_rows([sql_row(raw_json=json.dumps(payload))], DEVICES)
    assert all_rules == enabled and enabled[0].source is None


def test_series_reference_and_duplicate_rule_id_fail_without_repair():
    with pytest.raises(CatalogValidationError, match='Unknown selectivity series'):
        selectivity_rows([sql_row()], DEVICES[:1])
    with pytest.raises(CatalogValidationError, match='rule_id'):
        selectivity_rows([sql_row(), sql_row()], DEVICES)
    with pytest.raises(CatalogValidationError, match='conflicting'):
        selectivity_rows([sql_row(), sql_row(rule_id=2)], DEVICES)


def test_disabled_rules_are_validated_before_filter_and_sql_flags_cannot_verify(monkeypatch):
    all_rules, enabled = selectivity_rows([sql_row(is_verified_manufacturer_rule=0)], DEVICES)
    assert len(all_rules) == 1 and enabled == []
    with pytest.raises(CatalogValidationError):
        selectivity_rows([sql_row(is_verified_manufacturer_rule=0, limit_ka=-1)], DEVICES)
    _, enabled = selectivity_rows([sql_row()], DEVICES)
    monkeypatch.setattr(SiemensSelectivityRepository, 'get_selectivity_rules', classmethod(lambda cls: enabled))
    state, _, _ = SiemensSelectivityRepository.evaluate_pair(DEVICES[0], DEVICES[1], 1, 400, 100, 50)
    assert state not in (SelectivityEvalState.VERIFIED_TOTAL, SelectivityEvalState.VERIFIED_PARTIAL)


def test_legacy_total_type_and_zero_minimum_are_preserved_without_filling_json_voltage():
    payload = {**BASE, 'upstream_min_in_a': 0, 'is_total_up_to_icu': True}
    _, rules = selectivity_rows([sql_row(upstream_in_min_a=0, selectivity_type='TOTAL', raw_json=json.dumps(payload))], DEVICES)
    assert rules[0].upstream_min_in_a == 0 and rules[0].operating_voltage_v is None


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'catalog.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def edit(repo, sql, params=()):
    with closing(sqlite3.connect(repo.db_path)) as connection, connection:
        connection.execute('PRAGMA ignore_check_constraints=ON')
        connection.execute(sql, params)


@pytest.mark.parametrize('sql,params', [
    ('UPDATE selectivity_rules SET limit_ka=limit_ka+1', ()),
    ("UPDATE selectivity_rules SET is_verified_manufacturer_rule=0, raw_json='[]'", ()),
    ('UPDATE selectivity_rules SET is_verified_manufacturer_rule=2', ()),
    ("UPDATE selectivity_rules SET upstream_series='OTHER'", ()),
])
def test_actual_runtime_and_inventory_reject_copied_bad_rows_without_cached_fallback(repo, sql, params):
    old = repo.selectivity_rules
    edit(repo, sql, params)
    before = repo.db_path.read_bytes()
    for read in (lambda: repo.selectivity_rules, lambda: validate_catalog_database(repo.db_path)):
        with pytest.raises(CatalogValidationError):
            read()
    assert old and repo._rules_cache is None and repo.db_path.read_bytes() == before


def test_actual_cli_counts_disabled_rules_checks_all_rows_and_preserves_bytes(repo):
    edit(repo, 'UPDATE selectivity_rules SET is_verified_manufacturer_rule=0')
    assert repo.selectivity_rules == []
    command = [sys.executable, 'scripts/validate_catalog.py', '--db', str(repo.db_path)]
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = json.loads(completed.stdout)
    assert completed.returncode == 0 and result['selectivity_rules'] == 12
    assert result['enabled_selectivity_rules'] == 0 and result['engineering_verification'] == 'NOT_VERIFIED'
    assert repo.db_path.read_bytes() == before
    edit(repo, "UPDATE selectivity_rules SET raw_json=?", ('{"\\ud800":1,"\\ud800":2}',))
    before = repo.db_path.read_bytes()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.returncode == 1 and json.loads(completed.stdout)['status'] == 'INVALID'
    assert repo.db_path.read_bytes() == before


def test_real_payload_part_reference_mismatch_fails_inventory(repo):
    with closing(sqlite3.connect(repo.db_path)) as connection:
        rule_id, raw = connection.execute('SELECT rule_id, raw_json FROM selectivity_rules LIMIT 1').fetchone()
    payload = {**json.loads(raw), 'upstream_part_number': 'MISSING'}
    edit(repo, 'UPDATE selectivity_rules SET raw_json=? WHERE rule_id=?', (json.dumps(payload), rule_id))
    with pytest.raises(CatalogValidationError, match='reference mismatch'):
        validate_catalog_database(repo.db_path)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_disabled_bad_rule_fails_engine_precheck_and_gui_keeps_previous_run(repo, monkeypatch, locale):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Rule row gate')
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(repo.devices).process_project(project, inputs)
        edit(repo, 'UPDATE selectivity_rules SET is_verified_manufacturer_rule=0, limit_ka=limit_ka+1')
        engine = engine_module.EngineeringEngine(repo.devices)
        with pytest.raises(CatalogValidationError, match='limit_ka'):
            engine.process_project(project, inputs)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and 'limit_ka' in messages[0]
    finally:
        i18n.set_language(previous)


def test_custom_device_selection_does_not_make_other_database_series_dangling(repo, monkeypatch):
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    project = ProjectSpec(project_name='Subset catalog')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    subset = [device for device in repo.devices if device.device_type != 'CONTACTOR']
    outputs, _, _ = engine_module.EngineeringEngine(subset).process_project(project, inputs)
    assert len(outputs) == 1


def test_caller_changed_cached_device_series_does_not_rewrite_database_rule_references(repo, monkeypatch):
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    # Cached caller objects can describe a separate preliminary selection. They
    # are not the SQL inventory against which stored rule references are checked.
    for device in repo.devices:
        if device.series == 'SENTRON 3VA2':
            device.series = 'UNKNOWN SYNTHETIC SERIES'
    project = ProjectSpec(project_name='Separate source references')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    outputs, _, _ = engine_module.EngineeringEngine(repo.devices).process_project(project, inputs)
    assert len(outputs) == 1
    assert validate_catalog_database(repo.db_path)['selectivity_rules'] == 12
