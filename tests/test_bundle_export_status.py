"""Export status is inventory evidence, not a rendering/engineering approval."""

import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.outputs import PdfExporter, PdfExportResult


def results():
    project = ProjectSpec(project_name='Bundle status test')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('state', ['GENERATED', 'FAILED', 'NOT_REQUESTED'])
def test_actual_bundle_inventory_pdf_state_and_run_identity(tmp_path, monkeypatch, locale, state):
    project, (feeders, summary, checks) = results()
    previous = i18n.get_language()
    calls = []
    def pdf(html, target):
        calls.append(html)
        if state == 'GENERATED':
            Path(target).write_bytes(b'%PDF-1.4\nsynthetic fixture\n%%EOF')
            return PdfExportResult(True, 'ok')
        return PdfExportResult(False, 'timeout')
    monkeypatch.setattr(PdfExporter, 'export_html_to_pdf_result', pdf)
    path = tmp_path / 'bundle.zip'
    try:
        i18n.set_language(locale)
        result = LVAssistApp.build_document_bundle_result(str(path), project, feeders, summary, checks,
                                                         include_pdf=state != 'NOT_REQUESTED')
        assert result.pdf_status == state
        assert result.pdf_reason == ('timeout' if state == 'FAILED' else None)
        assert len(calls) == (state != 'NOT_REQUESTED')
        with ZipFile(path) as archive:
            names = set(archive.namelist())
            manifest = json.loads(archive.read('00_Export_Manifest.json'))
            assert result.file_count == len(names)
            assert manifest['locale'] == locale and manifest['preliminary'] is True
            assert manifest['run_metadata'] == summary.run_metadata.model_dump(mode='json')
            assert manifest['pdf']['status'] == state
            inventory = {row['path']: row for row in manifest['files']}
            assert {name for name, row in inventory.items() if row['status'] == 'GENERATED'} == names - set(manifest['inventory_excludes'])
            pdf_name = '02_Engineering_Report.pdf'
            assert (pdf_name in names) == (state == 'GENERATED')
            assert inventory[pdf_name]['status'] == state
            note = archive.read('00_Export_Status.txt').decode()
            assert tr('bundle_status_scope') in note
            if state == 'FAILED':
                assert tr('msg_pdf_timeout') in note
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('success', [True, False])
def test_gui_warns_for_missing_pdf_instead_of_complete_success(tmp_path, monkeypatch, locale, success):
    project, result = results()
    previous = i18n.get_language()
    infos, warnings = [], []
    path = tmp_path / 'bundle.zip'
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: infos.append(args))
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda *args: warnings.append(args))
    def pdf(html, target):
        if success:
            Path(target).write_bytes(b'%PDF-1.4\nsynthetic fixture\n%%EOF')
        return PdfExportResult(success, 'ok' if success else 'missing_browser')
    monkeypatch.setattr(PdfExporter, 'export_html_to_pdf_result', pdf)
    app = SimpleNamespace(_results_are_current=lambda: True, current_project=project, last_results=result)
    try:
        i18n.set_language(locale)
        LVAssistApp.action_export_all(app)
        assert path.is_file()
        assert bool(infos) == success and bool(warnings) != success
        if not success:
            assert tr('msg_pdf_missing_browser') in warnings[0][1]
            assert not infos
    finally:
        i18n.set_language(previous)
