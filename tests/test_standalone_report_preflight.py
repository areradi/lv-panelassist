"""Public standalone report APIs reject stale or changed run payloads."""

from types import SimpleNamespace

import pytest

import lv_assist.run_metadata as metadata_module
from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec

EXPORTERS = [('xlsx', ExcelExporter.export_to_excel), ('html', PrintableReportExporter.generate_html_report)]


def results():
    project = ProjectSpec(project_name='Standalone accepted snapshot')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


@pytest.mark.parametrize('extension,exporter', EXPORTERS)
@pytest.mark.parametrize('change', ['project', 'payload', 'checks', 'missing', 'engine'])
def test_public_api_rejects_stale_result_before_replacing_report(tmp_path, monkeypatch, extension, exporter, change):
    project, result = results()
    outputs, summary, checks = result
    path = tmp_path / ('old.' + extension)
    path.write_bytes(b'previous report')
    if change == 'project':
        project.project_name = 'Changed project'
    elif change == 'payload':
        summary.design_main_current_a += 10
    elif change == 'checks':
        checks.clear()
    elif change == 'missing':
        summary.run_metadata = None
    else:
        monkeypatch.setattr(metadata_module, 'ENGINE_VERSION', 'changed')
    with pytest.raises(ExportSnapshotError):
        exporter(str(path), project, outputs, summary, checks)
    assert path.read_bytes() == b'previous report'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('extension,exporter', EXPORTERS)
def test_renderer_mutation_cannot_publish_mixed_report(tmp_path, monkeypatch, extension, exporter):
    project, result = results()
    path = tmp_path / ('old.' + extension)
    path.write_bytes(b'previous report')
    cls, method = (ExcelExporter, '_render_to_excel') if extension == 'xlsx' else (PrintableReportExporter, '_render_html_report')
    original = getattr(cls, method)
    def render(filename, project, outputs, summary, checks):
        original(filename, project, outputs, summary, checks)
        summary.design_main_current_a += 10
    monkeypatch.setattr(cls, method, render)
    with pytest.raises(ExportSnapshotError):
        exporter(str(path), project, *result)
    assert path.read_bytes() == b'previous report'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('extension,exporter', EXPORTERS)
def test_caller_changes_do_not_mutate_private_report_snapshot(tmp_path, monkeypatch, extension, exporter):
    project, result = results()
    cls, method = (ExcelExporter, '_render_to_excel') if extension == 'xlsx' else (PrintableReportExporter, '_render_html_report')
    original = getattr(cls, method)
    def render(*args):
        project.project_name = 'Caller changed project'
        result[0][0].description = 'Caller changed feeder'
        return original(*args)
    monkeypatch.setattr(cls, method, render)
    path = tmp_path / ('new.' + extension)
    exporter(str(path), project, *result)
    if extension == 'html':
        text = path.read_text(encoding='utf-8')
        assert 'Caller changed' not in text
        assert 'Standalone accepted snapshot' in text
    else:
        import openpyxl
        book = openpyxl.load_workbook(path)
        values = [cell.value for sheet in book for row in sheet for cell in row]
        assert 'Standalone accepted snapshot' in values
        assert 'Caller changed feeder' not in values
        book.close()
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('action', ['action_export_report', 'action_open_printable_report'])
def test_gui_reports_stale_api_failure_without_opening_or_success(tmp_path, monkeypatch, locale, action):
    project, result = results()
    project.project_name = 'Changed before export'
    previous = i18n.get_language()
    warnings, opened, successes = [], [], []
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(tmp_path / 'report.xlsx'))
    monkeypatch.setattr('lv_assist.gui.get_app_working_dir', lambda: str(tmp_path))
    monkeypatch.setattr('lv_assist.gui.webbrowser.open', lambda *args: opened.append(args))
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda title, message: warnings.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    app = SimpleNamespace(_results_are_current=lambda: True, current_project=project, last_results=result)
    try:
        i18n.set_language(locale)
        getattr(LVAssistApp, action)(app)
        assert warnings == [tr('lbl_stale')]
        assert not opened and not successes
        assert list(tmp_path.iterdir()) == []
    finally:
        i18n.set_language(previous)
