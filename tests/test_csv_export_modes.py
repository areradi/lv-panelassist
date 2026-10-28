"""CSV mode contracts: persisted fields only, no spreadsheet formula execution."""

import csv
from types import SimpleNamespace

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.control_circuits import ControlCircuitGenerator
from lv_assist.csv_export import CsvMode, spreadsheet_text, write_csv
from lv_assist.engine import EngineeringEngine
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.outputs import EplanExporter, EplanPartsExporter


@pytest.mark.parametrize('value', ['=1+1', '+SUM(1,2)', '-cmd', '@SUM(1)', '\t=1+1', '\r=1+1', '  =1+1', '\ufeff=1+1'])
def test_text_is_protected_without_modifying_numeric_values(tmp_path, value):
    path = tmp_path / 'test.csv'
    write_csv(path, ['text', 'number'], [[value, -3.5]], mode=CsvMode.SPREADSHEET)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream))
    assert rows[1] == ["'" + value, '-3.5']
    assert spreadsheet_text(-3.5) == -3.5


@pytest.mark.parametrize('exporter', [EplanExporter.export_csv, EplanPartsExporter.export_csv,
                                     ControlCircuitGenerator.export_connections_csv])
def test_real_exporters_default_machine_and_explicit_spreadsheet_mode(tmp_path, exporter):
    project = ProjectSpec(project_name='CSV contract')
    inputs = [FeederInput(feeder_id='F1', description='CSV test', load_type=LoadType.MOTOR_DOL, power_kw=15)]
    devices = CatalogRepository.get_default_catalog()
    for device in devices:
        if device.device_type == 'ENCLOSURE':
            device.series = '=1+1'
    feeders, summary, checks = EngineeringEngine(devices).process_project(project, inputs)
    paths = [tmp_path / name for name in ('default.csv', 'machine.csv', 'spreadsheet.csv')]
    exporter(str(paths[0]), project, feeders, summary, validations=checks)
    exporter(str(paths[1]), project, feeders, summary, mode=CsvMode.MACHINE, validations=checks)
    exporter(str(paths[2]), project, feeders, summary, mode=CsvMode.SPREADSHEET, validations=checks)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    assert paths[0].read_bytes().startswith(b'\xef\xbb\xbf')
    def rows(path):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.reader(stream))
    raw, protected = rows(paths[1]), rows(paths[2])
    assert protected == [[spreadsheet_text(value) for value in row] for row in raw]
    assert protected != raw  # Engineering tags / expression-like catalog strings.


def test_invalid_mode_does_not_truncate_old_file(tmp_path):
    path = tmp_path / 'old.csv'
    path.write_bytes(b'old data')
    with pytest.raises(ValueError):
        write_csv(path, ['text'], [['=1+1']], mode='typo')
    assert path.read_bytes() == b'old data'


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('choice', [True, False, None])
def test_gui_mode_and_cancel_reach_actual_csv_writer(monkeypatch, tmp_path, locale, choice):
    previous = i18n.get_language()
    path = tmp_path / 'ui.csv'
    messages = []
    monkeypatch.setattr('lv_assist.gui.messagebox.askyesnocancel', lambda *args: choice)
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda title, message: messages.append(message))
    def exporter(filename, *args, mode, validations):
        write_csv(filename, ['tag'], [['=INCOMING']], mode=mode)
    app = SimpleNamespace(_get_results=lambda: ([], None, []), current_project=None)
    try:
        i18n.set_language(locale)
        LVAssistApp._export_csv_for_target(app, exporter, 'Parts.csv')
        if choice is None:
            assert not path.exists() and not messages
        else:
            with path.open(encoding='utf-8-sig', newline='') as stream:
                rows = list(csv.reader(stream))
            assert rows[1][0] == ("'=INCOMING" if choice else '=INCOMING')
            assert messages == [tr('csv_saved_spreadsheet' if choice else 'csv_saved_machine')]
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('action', ['action_export_eplan', 'action_export_connections', 'action_export_parts'])
def test_each_csv_button_uses_target_choice(action):
    calls = []
    app = SimpleNamespace(_export_csv_for_target=lambda *args: calls.append(args))
    getattr(LVAssistApp, action)(app)
    assert len(calls) == 1
