"""Auxiliary rating structural checks with synthetic copied DB records."""

import shutil
import sqlite3
from types import SimpleNamespace

import pytest

import lv_assist.catalog as catalog_module
import lv_assist.engine as engine_module
from lv_assist.catalog import CatalogRepository
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.rating_table_validation import ampacity_table, derating_table


@pytest.mark.parametrize('value', [None, True, False, 0, -1, float('nan'), float('inf'), '12'])
@pytest.mark.parametrize('field', ['section_mm2', 'iz0_a'])
def test_ampacity_rejects_invalid_consumed_numbers(field, value):
    row = {'section_mm2': 16, 'iz0_a': 57, field: value}
    with pytest.raises(ValueError):
        ampacity_table([row])


@pytest.mark.parametrize('value', [None, True, 0, -1, 1.3, float('nan'), float('inf'), '0.9'])
def test_derating_factor_respects_existing_schema_bound(value):
    with pytest.raises(ValueError):
        derating_table([{'temp_c': 50, 'derating_factor': value}])


def test_duplicate_rating_conditions_are_rejected_even_if_values_agree():
    with pytest.raises(ValueError):
        ampacity_table([{'section_mm2': 16, 'iz0_a': 57}] * 2)
    with pytest.raises(ValueError):
        derating_table([{'temp_c': 50, 'derating_factor': 0.9}] * 2)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'ratings.db'
    shutil.copyfile(catalog_module.DB_PATH, path)
    return CatalogRepository(path)


def edit(path, operation):
    connection = sqlite3.connect(path)
    try:
        # Corrupt copied fixtures deliberately; never disable constraints in app code.
        connection.execute('PRAGMA ignore_check_constraints=ON')
        with connection:
            operation(connection)
    finally:
        connection.close()


@pytest.mark.parametrize('method', ['table', 'legacy_table', 'single'])
def test_actual_ampacity_queries_reject_bad_row(repo, method):
    edit(repo.db_path, lambda connection: connection.execute(
        "UPDATE cable_ampacity_reference SET iz0_a=-1 WHERE material='CU' AND insulation='PVC' AND installation_method='C'"))
    with pytest.raises(ValueError):
        if method == 'table':
            repo.get_cable_iz0_table('CU', 'PVC', 'C', 3)
        elif method == 'legacy_table':
            repo.get_cable_iz0_table_cu_pvc_c(3)
        else:
            repo.get_base_cable_iz0(16)


def test_missing_and_valid_rating_queries_keep_exact_domains(repo):
    assert repo.get_cable_iz0_table('unknown', 'PVC', 'C', 3) == {}
    assert repo.get_base_cable_iz0(99999) is None
    assert repo.get_base_cable_iz0(16) > 0
    assert repo.get_device_derating_factor('UNKNOWN', 50) is None
    def records(connection):
        connection.execute("INSERT INTO device_thermal_derating(device_id,temp_c,derating_factor) VALUES ('SYNTHETIC',60,0.7)")
    edit(repo.db_path, records)
    assert repo.get_device_derating_factor('SYNTHETIC', 55) is None
    assert repo.get_device_derating_factor('SYNTHETIC', 60) == 0.7


@pytest.mark.parametrize('value', [None, True, float('nan'), float('inf'), '50'])
def test_runtime_temperature_cannot_be_coerced_to_valid_reference_bin(repo, value):
    with pytest.raises(ValueError):
        repo.get_device_derating_factor('TEST', value)


@pytest.mark.parametrize('value', [0, -1, True, '3', None, 2**1000])
def test_loaded_conductor_count_requires_positive_integer(repo, value):
    with pytest.raises(ValueError):
        repo.get_cable_iz0_table('CU', 'PVC', 'C', value)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('table', ['ampacity', 'derating'])
def test_bad_auxiliary_rows_fail_actual_engine_and_keep_gui_previous_result(repo, monkeypatch, locale, table):
    previous = i18n.get_language()
    monkeypatch.setattr(catalog_module, 'catalog_repo', repo)
    monkeypatch.setattr(engine_module, 'catalog_repo', repo)
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Auxiliary rating failure', max_internal_temp_c=50)
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        old = engine_module.EngineeringEngine(repo.devices).process_project(project, inputs)
        if table == 'ampacity':
            edit(repo.db_path, lambda connection: connection.execute("UPDATE cable_ampacity_reference SET iz0_a=-1"))
        else:
            edit(repo.db_path, lambda connection: connection.execute("UPDATE device_thermal_derating SET derating_factor=2"))
        engine = engine_module.EngineeringEngine(repo.devices)
        with pytest.raises(ValueError) as caught:
            engine.process_project(project, inputs)
        field = 'iz0_a' if table == 'ampacity' else 'derating_factor'
        assert field in str(caught.value)
        messages = []
        app = SimpleNamespace(engine=engine, current_project=project, current_feeders=inputs,
                              last_results=old, _stale=False)
        app._mark_stale = lambda: setattr(app, '_stale', True)
        monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: messages.append(message))
        LVAssistApp._run_calculations_and_refresh(app)
        assert app.last_results is old and app._stale
        assert len(messages) == 1 and field in messages[0]
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('temperature', [-1, 0, 19, 81, float('nan'), '50'])
def test_stored_temperature_respects_existing_schema_domain(temperature):
    with pytest.raises(ValueError):
        derating_table([{'temp_c': temperature, 'derating_factor': 0.9}])


@pytest.mark.parametrize('factor', [1.1, 1.2])
def test_existing_schema_upper_factor_is_not_replaced_by_arbitrary_new_limit(factor):
    assert derating_table([{'temp_c': 40, 'derating_factor': factor}])[40] == factor
