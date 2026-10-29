"""Accepted-run context and publication boundaries for five drawing file APIs."""

from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.control_circuits import ControlCircuitGenerator
from lv_assist.engine import EngineeringEngine
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.gui import LVAssistApp
from lv_assist.i18n import i18n, tr
from lv_assist.layout import PanelLayoutGenerator
from lv_assist.models import FeederInput, LoadType, ProjectSpec
from lv_assist.outputs import SldGenerator, TccGenerator

CASES = [
    (SldGenerator, 'generate_svg_file', 'generate_svg', '.svg', 'action_export_sld'),
    (TccGenerator, 'generate_svg_file', 'generate_svg', '.svg', 'action_export_tcc'),
    (ControlCircuitGenerator, 'generate_svg_file', 'generate_svg', '.svg', 'action_export_ctrl_svg'),
    (PanelLayoutGenerator, 'generate_svg_file', 'generate_svg', '.svg', 'action_export_layout'),
]


def results():
    project = ProjectSpec(project_name='Drawing accepted run')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.MOTOR_DOL, power_kw=15)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('change', ['project', 'payload', 'checks', 'missing_identity'])
def test_changed_run_cannot_replace_existing_drawing(tmp_path, case, change):
    cls, method, _, extension, _ = case
    project, (outputs, summary, checks) = results()
    path = tmp_path / ('old' + extension)
    path.write_bytes(b'previous drawing')
    if change == 'project':
        project.project_name = 'Changed project'
    elif change == 'payload':
        summary.design_main_current_a += 10
    elif change == 'checks':
        checks.clear()
    else:
        summary.run_metadata = None
    with pytest.raises(ExportSnapshotError):
        getattr(cls, method)(str(path), project, outputs, summary, validations=checks)
    assert path.read_bytes() == b'previous drawing'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('case', CASES)
def test_check_context_cannot_be_omitted(tmp_path, case):
    cls, method, _, extension, _ = case
    project, (outputs, summary, _) = results()
    path = tmp_path / ('new' + extension)
    with pytest.raises(ExportSnapshotError):
        getattr(cls, method)(str(path), project, outputs, summary)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('case', CASES)
def test_unchanged_run_produces_parseable_drawing(tmp_path, case):
    cls, method, _, extension, _ = case
    project, (outputs, summary, checks) = results()
    path = tmp_path / ('new' + extension)
    getattr(cls, method)(str(path), project, outputs, summary, validations=checks)
    if extension == '.svg':
        assert ElementTree.parse(path).getroot().tag.endswith('svg')
    else:
        content = path.read_text(encoding='ascii')
        assert content.startswith('0\nSECTION') and content.rstrip().endswith('EOF')
        assert all(byte < 128 for byte in path.read_bytes())
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('failure', ['io', 'mutation'])
def test_renderer_failure_or_mutation_does_not_publish(tmp_path, monkeypatch, case, failure):
    cls, method, renderer, extension, _ = case
    project, (outputs, summary, checks) = results()
    original = getattr(cls, renderer)
    def render(project, outputs, summary):
        if failure == 'io':
            raise OSError('synthetic drawing failure')
        content = original(project, outputs, summary)
        summary.design_main_current_a += 10
        return content
    monkeypatch.setattr(cls, renderer, render)
    path = tmp_path / ('old' + extension)
    path.write_bytes(b'previous drawing')
    with pytest.raises(OSError if failure == 'io' else ExportSnapshotError):
        getattr(cls, method)(str(path), project, outputs, summary, validations=checks)
    assert path.read_bytes() == b'previous drawing'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_gui_rejects_stale_drawing_without_opening_or_success(tmp_path, monkeypatch, case, locale):
    _, _, _, extension, action = case
    project, result = results()
    project.project_name = 'Changed project'
    path = tmp_path / ('old' + extension)
    path.write_bytes(b'previous drawing')
    warnings, successes, opened = [], [], []
    previous = i18n.get_language()
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda title, message: warnings.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    monkeypatch.setattr('lv_assist.gui.webbrowser.open', lambda *args: opened.append(args))
    app = SimpleNamespace(_get_results=lambda: result, current_project=project)
    app._export_drawing = lambda *args, **kwargs: LVAssistApp._export_drawing(app, *args, **kwargs)
    try:
        i18n.set_language(locale)
        getattr(LVAssistApp, action)(app)
        assert warnings == [tr('lbl_stale')]
        assert not successes and not opened
        assert path.read_bytes() == b'previous drawing'
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_gui_drawing_io_failure_is_localized_and_never_opens_file(tmp_path, monkeypatch, locale):
    project, result = results()
    path = tmp_path / 'old.svg'
    path.write_bytes(b'previous drawing')
    errors, successes, opened = [], [], []
    previous = i18n.get_language()
    def render(*args):
        raise OSError('synthetic renderer IO failure')
    monkeypatch.setattr(SldGenerator, 'generate_svg', render)
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showerror', lambda title, message: errors.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    monkeypatch.setattr('lv_assist.gui.webbrowser.open', lambda *args: opened.append(args))
    app = SimpleNamespace(_get_results=lambda: result, current_project=project)
    try:
        i18n.set_language(locale)
        LVAssistApp._export_drawing(app, SldGenerator.generate_svg_file, 'SLD.svg', '.svg')
        assert errors == [tr('drawing_write_failed')]
        assert not successes and not opened
        assert path.read_bytes() == b'previous drawing'
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('case', CASES)
def test_gui_success_forwards_complete_context_and_opens_only_svg(tmp_path, monkeypatch, case):
    _, _, _, extension, action = case
    project, result = results()
    path = tmp_path / ('new' + extension)
    successes, opened = [], []
    monkeypatch.setattr('lv_assist.gui.filedialog.asksaveasfilename', lambda **kwargs: str(path))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    monkeypatch.setattr('lv_assist.gui.webbrowser.open', lambda *args: opened.append(args))
    app = SimpleNamespace(_get_results=lambda: result, current_project=project)
    app._export_drawing = lambda *args, **kwargs: LVAssistApp._export_drawing(app, *args, **kwargs)
    getattr(LVAssistApp, action)(app)
    assert path.stat().st_size > 0
    assert len(successes) == 1
    assert len(opened) == (extension == '.svg')
    assert list(tmp_path.iterdir()) == [path]
