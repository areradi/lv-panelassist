"""All engineering CSV modes require the complete accepted calculation context."""

from types import SimpleNamespace

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.functional_connections import FunctionalConnections
from lv_assist.csv_export import CsvMode
from lv_assist.engine import EngineeringEngine
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.outputs import EplanExporter, EplanPartsExporter

EXPORTERS = [EplanExporter.export_csv, EplanPartsExporter.export_csv, FunctionalConnections.export_csv]
RENDERERS = [(EplanExporter, '_render_csv'), (EplanPartsExporter, '_render_csv'),
             (FunctionalConnections, '_render_csv')]


def results():
    project = ProjectSpec(project_name='CSV accepted context')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.MOTOR_DOL, power_kw=15)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


@pytest.mark.parametrize('exporter', EXPORTERS)
@pytest.mark.parametrize('mode', list(CsvMode))
@pytest.mark.parametrize('change', ['project', 'device', 'checks', 'missing_identity'])
def test_public_csv_rejects_stale_data_and_preserves_old_file(tmp_path, exporter, mode, change):
    project, (outputs, summary, checks) = results()
    path = tmp_path / 'old.csv'
    path.write_bytes(b'previous export')
    if change == 'project':
        project.project_name = 'Changed project'
    elif change == 'device':
        summary.selected_enclosure.part_number = 'Changed part'
    elif change == 'checks':
        checks.clear()
    else:
        summary.run_metadata = None
    with pytest.raises(ExportSnapshotError):
        exporter(str(path), project, outputs, summary, validations=checks, mode=mode)
    assert path.read_bytes() == b'previous export'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('exporter', EXPORTERS)
@pytest.mark.parametrize('mode', list(CsvMode))
def test_legacy_call_without_check_context_is_explicitly_rejected(tmp_path, exporter, mode):
    project, (outputs, summary, _) = results()
    path = tmp_path / 'new.csv'
    with pytest.raises(ExportSnapshotError):
        exporter(str(path), project, outputs, summary, mode=mode)
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('exporter,renderer', list(zip(EXPORTERS, RENDERERS)))
@pytest.mark.parametrize('mode', list(CsvMode))
def test_csv_renderer_mutation_is_rejected_before_publication(tmp_path, monkeypatch, exporter, renderer, mode):
    project, (outputs, summary, checks) = results()
    cls, method = renderer
    original = getattr(cls, method)
    def render(filename, project, outputs, summary, **kwargs):
        original(filename, project, outputs, summary, **kwargs)
        summary.design_main_current_a += 10
    monkeypatch.setattr(cls, method, render)
    path = tmp_path / 'old.csv'
    path.write_bytes(b'previous export')
    with pytest.raises(ExportSnapshotError):
        exporter(str(path), project, outputs, summary, validations=checks, mode=mode)
    assert path.read_bytes() == b'previous export'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('exporter', EXPORTERS)
def test_gui_passes_checks_and_handles_stale_api_failure(tmp_path, monkeypatch, locale, exporter):
    project, result = results()
    project.project_name = 'Changed project'
    previous = i18n.get_language()
    warnings, successes = [], []
    path = tmp_path / 'old.csv'
    path.write_bytes(b'previous export')
    monkeypatch.setattr('lv_assist.gui.messagebox.askyesnocancel', lambda *args: True)
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda title, message: warnings.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    app = SimpleNamespace(_get_results=lambda: result, current_project=project)
    try:
        i18n.set_language(locale)
        LVAssistApp._export_csv_for_target(app, exporter, 'Parts.csv')
        assert warnings == [tr('lbl_stale')]
        assert not successes
        assert path.read_bytes() == b'previous export'
    finally:
        i18n.set_language(previous)
