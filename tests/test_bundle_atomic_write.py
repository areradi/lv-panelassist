"""Bundle generation/publication failure tests, without real PDF printing."""

from types import SimpleNamespace
from zipfile import BadZipFile, ZipFile

import pytest

from lv_assist.bundle_export import build_bundle_atomic
from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec


def results():
    project = ProjectSpec(project_name='Bundle publication test')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


def fail(*args, **kwargs):
    raise OSError('synthetic disk/permission error')


@pytest.mark.parametrize('stage', ['ExcelExporter.export_to_excel', 'FunctionalConnections.export_csv'])
def test_actual_generation_failure_preserves_previous_bundle(tmp_path, monkeypatch, stage):
    project, (feeders, summary, checks) = results()
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    monkeypatch.setattr('lv_assist.gui.' + stage, fail)
    with pytest.raises(OSError):
        LVAssistApp.build_document_bundle(str(path), project, feeders, summary, checks, include_pdf=False)
    assert path.read_bytes() == b'previous bundle'
    assert list(tmp_path.iterdir()) == [path]


def test_actual_success_replaces_bundle_and_retains_expected_assets(tmp_path):
    project, (feeders, summary, checks) = results()
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    count = LVAssistApp.build_document_bundle(str(path), project, feeders, summary, checks, include_pdf=False)
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        assert count == len(archive.namelist()) == 13
        assert archive.read('00_CSV_README.txt').decode() == tr('csv_bundle_note')
        assert '01_Design_Output.xlsx' in archive.namelist()
        assert '02_Engineering_Report.html' in archive.namelist()
        assert not any(name.endswith('.pdf') for name in archive.namelist())
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('stage', ['create', 'sync', 'publish'])
def test_publication_boundary_failure_preserves_previous_bundle(tmp_path, monkeypatch, stage):
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    def build(filename):
        with ZipFile(filename, 'w') as archive:
            archive.writestr('one.txt', 'completed')
        return 1
    target = {'create': 'tempfile.NamedTemporaryFile', 'sync': 'os.fsync', 'publish': 'os.replace'}[stage]
    monkeypatch.setattr('lv_assist.bundle_export.' + target, fail)
    with pytest.raises(OSError):
        build_bundle_atomic(path, build)
    assert path.read_bytes() == b'previous bundle'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('bad', ['notzip', 'count', 'empty'])
def test_invalid_or_incomplete_archive_is_not_published(tmp_path, bad):
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    def build(filename):
        if bad == 'notzip':
            from pathlib import Path
            Path(filename).write_bytes(b'partial zip')
            return 1
        with ZipFile(filename, 'w') as archive:
            if bad != 'empty':
                archive.writestr('one.txt', 'completed')
        return 0 if bad == 'empty' else 2
    with pytest.raises(BadZipFile):
        build_bundle_atomic(path, build)
    assert path.read_bytes() == b'previous bundle'
    assert list(tmp_path.iterdir()) == [path]


def test_failed_first_bundle_leaves_no_destination(tmp_path):
    path = tmp_path / 'new.zip'
    with pytest.raises(OSError):
        build_bundle_atomic(path, fail)
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_gui_late_generation_failure_has_localized_message_no_success(tmp_path, monkeypatch, locale):
    project, result = results()
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    previous = i18n.get_language()
    errors, successes = [], []
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: errors.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    monkeypatch.setattr('lv_assist.gui.FunctionalConnections.export_csv', fail)
    app = SimpleNamespace(_results_are_current=lambda: True, last_results=result, current_project=project)
    try:
        i18n.set_language(locale)
        LVAssistApp.action_export_all(app)
        assert errors == [tr('bundle_write_failed')]
        assert not successes
        assert path.read_bytes() == b'previous bundle'
        assert list(tmp_path.iterdir()) == [path]
    finally:
        i18n.set_language(previous)
