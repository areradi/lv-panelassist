"""Bind the preliminary checklist to the run; never accept invented PASS/evidence."""

from types import SimpleNamespace

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine, build_design_verification
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.exporters import DesignVerificationExporter
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec, VerificationStatus


def results():
    project = ProjectSpec(project_name='Preliminary checklist context')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    outputs, summary, checks = EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)
    return project, outputs, summary, checks, build_design_verification(project, outputs, summary, checks)


@pytest.mark.parametrize('change', ['project', 'result', 'checks', 'metadata', 'item_status',
                                    'conclusion', 'evidence', 'reviewer', 'source', 'removed'])
def test_changed_run_or_checklist_cannot_replace_existing_report(tmp_path, change):
    project, outputs, summary, checks, report = results()
    if change == 'project':
        project.project_name = 'Changed project'
    elif change == 'result':
        summary.design_main_current_a += 10
    elif change == 'checks':
        checks.clear()
    elif change == 'metadata':
        summary.run_metadata = None
    elif change == 'item_status':
        report.items[0].status = VerificationStatus.PASS
    elif change == 'conclusion':
        report.conclusion_status = VerificationStatus.PASS
    elif change == 'evidence':
        report.items[0].evidence_document = 'invented evidence'
    elif change == 'reviewer':
        report.items[0].reviewer = 'synthetic claimed reviewer'
    elif change == 'source':
        report.items[0].source_ref = 'altered source'
    else:
        report.items.pop()
    path = tmp_path / 'old.html'
    path.write_bytes(b'previous checklist')
    with pytest.raises(ExportSnapshotError):
        DesignVerificationExporter.generate_html(str(path), project, summary, report, feeders=outputs, validations=checks)
    assert path.read_bytes() == b'previous checklist'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('missing', ['feeders', 'checks', 'both'])
def test_full_context_is_required_before_creating_report(tmp_path, missing):
    project, outputs, summary, checks, report = results()
    kwargs = {}
    if missing != 'feeders' and missing != 'both':
        kwargs['feeders'] = outputs
    if missing != 'checks' and missing != 'both':
        kwargs['validations'] = checks
    with pytest.raises(ExportSnapshotError):
        DesignVerificationExporter.generate_html(str(tmp_path / 'new.html'), project, summary, report, **kwargs)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_actual_preliminary_report_renders_without_assembly_pass(tmp_path, locale):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        project, outputs, summary, checks, report = results()
        path = tmp_path / 'report.html'
        DesignVerificationExporter.generate_html(str(path), project, summary, report, feeders=outputs, validations=checks)
        content = path.read_text(encoding='utf-8')
        assert project.project_name in content
        assert 'badge badge-verified' not in content
        assert len(report.items) == 13
        assert report.conclusion_status in (VerificationStatus.NOT_VERIFIED, VerificationStatus.FAIL)
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('failure', ['io', 'mutation'])
def test_checklist_renderer_failure_cannot_publish(tmp_path, monkeypatch, failure):
    project, outputs, summary, checks, report = results()
    original = DesignVerificationExporter._render_html
    def render(path, project, summary, report):
        if failure == 'io':
            raise OSError('synthetic rendering failure')
        original(path, project, summary, report)
        report.conclusion_status = VerificationStatus.PASS
    monkeypatch.setattr(DesignVerificationExporter, '_render_html', render)
    path = tmp_path / 'old.html'
    path.write_bytes(b'previous checklist')
    with pytest.raises(OSError if failure == 'io' else ExportSnapshotError):
        DesignVerificationExporter.generate_html(str(path), project, summary, report, feeders=outputs, validations=checks)
    assert path.read_bytes() == b'previous checklist'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('outcome', ['stale', 'io', 'success'])
def test_gui_context_messages_and_open_behavior(tmp_path, monkeypatch, locale, outcome):
    previous = i18n.get_language()
    warnings, errors, infos, opened = [], [], [], []
    path = tmp_path / 'report.html'
    path.write_bytes(b'previous checklist')
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda title, message: warnings.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: errors.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: infos.append(args))
    monkeypatch.setattr('lv_assist.gui.webbrowser.open', lambda *args: opened.append(args))
    try:
        i18n.set_language(locale)
        project, outputs, summary, checks, _ = results()
        if outcome == 'stale':
            project.project_name = 'Changed before export'
        if outcome == 'io':
            def render(*args):
                raise OSError('synthetic rendering failure')
            monkeypatch.setattr(DesignVerificationExporter, '_render_html', render)
        app = SimpleNamespace(_results_are_current=lambda: True, current_project=project,
                              last_results=(outputs, summary, checks))
        LVAssistApp.action_export_dv(app)
        if outcome == 'success':
            assert len(infos) == len(opened) == 1 and not errors and not warnings
        else:
            assert not infos and not opened
            assert path.read_bytes() == b'previous checklist'
            assert warnings == ([tr('lbl_stale')] if outcome == 'stale' else [])
            assert errors == ([tr('verification_write_failed')] if outcome == 'io' else [])
    finally:
        i18n.set_language(previous)
