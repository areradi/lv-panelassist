"""Bundle freshness checks run through the public API, not only GUI helpers."""

import json
from types import SimpleNamespace

import pytest

import lv_assist.run_metadata as metadata_module
from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec


def results():
    project = ProjectSpec(project_name='Snapshot preflight')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


@pytest.mark.parametrize('change', ['project', 'revision', 'missing_summary', 'missing_feeder',
                                    'mixed_run', 'feeder_id', 'snapshot', 'engine', 'source', 'catalog', 'registry'])
def test_stale_bundle_rejected_before_rendering_and_old_file_preserved(tmp_path, monkeypatch, change):
    project, (feeders, summary, checks) = results()
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    if change == 'project':
        project.nominal_voltage_v = 415
    elif change == 'revision':
        project.project_revision += 1
    elif change == 'missing_summary':
        summary.run_metadata = None
    elif change == 'missing_feeder':
        feeders[0].run_metadata = None
    elif change == 'mixed_run':
        _, (_, other, _) = results()
        feeders[0].run_metadata = other.run_metadata
    elif change == 'feeder_id':
        feeders[0].feeder_id = 'OTHER'
    elif change == 'snapshot':
        summary.run_metadata = summary.run_metadata.model_copy(update={'input_snapshot_json': '{}'})
    else:
        name = {'engine': 'ENGINE_VERSION', 'source': 'engine_source_hash',
                'catalog': 'catalog_file_hash', 'registry': 'registry_hash'}[change]
        monkeypatch.setattr(metadata_module, name, 'changed' if change == 'engine' else lambda *args: 'changed')
    def render(*args):
        pytest.fail('A stale bundle must be rejected before rendering')
    monkeypatch.setattr(LVAssistApp, '_build_document_bundle', render)
    with pytest.raises(ExportSnapshotError):
        LVAssistApp.build_document_bundle(str(path), project, feeders, summary, checks, include_pdf=False)
    assert path.read_bytes() == b'previous bundle'
    assert list(tmp_path.iterdir()) == [path]


def test_source_change_during_rendering_aborts_publication(tmp_path, monkeypatch):
    project, (feeders, summary, checks) = results()
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    original = LVAssistApp._build_document_bundle
    def build(*args):
        result = original(*args)
        monkeypatch.setattr(metadata_module, 'ENGINE_VERSION', 'changed-during-rendering')
        return result
    monkeypatch.setattr(LVAssistApp, '_build_document_bundle', build)
    with pytest.raises(ExportSnapshotError):
        LVAssistApp.build_document_bundle(str(path), project, feeders, summary, checks, include_pdf=False)
    assert path.read_bytes() == b'previous bundle'
    assert list(tmp_path.iterdir()) == [path]


def test_private_bundle_copy_is_not_changed_by_caller_mutation(tmp_path, monkeypatch):
    from zipfile import ZipFile
    project, (feeders, summary, checks) = results()
    original = LVAssistApp._build_document_bundle
    def build(*args):
        project.project_name = 'Caller changed during export'
        feeders[0].description = 'Caller changed output'
        return original(*args)
    monkeypatch.setattr(LVAssistApp, '_build_document_bundle', build)
    path = tmp_path / 'bundle.zip'
    LVAssistApp.build_document_bundle(str(path), project, feeders, summary, checks, include_pdf=False)
    with ZipFile(path) as archive:
        report = archive.read('02_Engineering_Report.html').decode()
        assert 'Caller changed' not in report
        manifest = json.loads(archive.read('00_Export_Manifest.json'))
        assert 'Snapshot preflight' in manifest['run_metadata']['input_snapshot_json']


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_gui_rechecks_api_identity_even_if_initial_gui_check_passes(tmp_path, monkeypatch, locale):
    project, result = results()
    project.project_name = 'Changed after calculation'
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    messages, successes = [], []
    previous = i18n.get_language()
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda title, message: messages.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    app = SimpleNamespace(_results_are_current=lambda: True, last_results=result, current_project=project)
    try:
        i18n.set_language(locale)
        LVAssistApp.action_export_all(app)
        assert messages == [tr('lbl_stale')]
        assert not successes
        assert path.read_bytes() == b'previous bundle'
    finally:
        i18n.set_language(previous)
