"""Library snapshot/publication guards retained after retiring EPLAN generators."""

from types import SimpleNamespace

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.gui import LVAssistApp
from lv_assist.gui_output_bridge import GuiOutputBridge
from lv_assist.i18n import i18n, tr
from lv_assist.models import FeederInput, LoadType, ProjectSpec

CASES = [(GuiOutputBridge, 'export_all_svgs_to_folder', '_render_all_svgs', 'svgs')]


def results():
    project = ProjectSpec(project_name='EPLAN accepted run')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.MOTOR_DOL, power_kw=15)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('change', ['project', 'payload', 'checks', 'missing'])
def test_invalid_run_never_changes_previous_output(tmp_path, case, change):
    cls, method, _, name = case
    project, (outputs, summary, checks) = results()
    target = tmp_path / name
    if name.endswith('.cs'):
        target.write_bytes(b'previous script')
    else:
        target.mkdir()
        (target / 'user.txt').write_bytes(b'user content')
    if change == 'project':
        project.project_name = 'Changed'
    elif change == 'payload':
        summary.design_main_current_a += 10
    elif change == 'checks':
        checks.clear()
    else:
        summary.run_metadata = None
    with pytest.raises(ExportSnapshotError):
        getattr(cls, method)(str(target), project, outputs, summary, validations=checks)
    assert (target if name.endswith('.cs') else target / 'user.txt').read_bytes().startswith(b'previous' if name.endswith('.cs') else b'user')
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize('case', CASES)
def test_missing_context_rejected_before_creating_destination(tmp_path, case):
    cls, method, _, name = case
    project, (outputs, summary, _) = results()
    with pytest.raises(ExportSnapshotError):
        getattr(cls, method)(str(tmp_path / name), project, outputs, summary)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('case', CASES)
def test_existing_nonempty_library_is_never_overwritten(tmp_path, case):
    cls, method, _, name = case
    project, (outputs, summary, checks) = results()
    target = tmp_path / name
    written = getattr(cls, method)(str(target), project, outputs, summary, validations=checks)
    before = {path.name: path.read_bytes() for path in target.iterdir()}
    assert written
    with pytest.raises(FileExistsError):
        getattr(cls, method)(str(target), project, outputs, summary, validations=checks)
    assert before == {path.name: path.read_bytes() for path in target.iterdir()}
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('failure', ['io', 'mutation'])
def test_generation_failure_leaves_no_partial_publication(tmp_path, monkeypatch, case, failure):
    cls, method, renderer, name = case
    project, (outputs, summary, checks) = results()
    original = getattr(cls, renderer)
    def render(path, project, outputs, summary, *args, **kwargs):
        if failure == 'io':
            raise OSError('synthetic renderer error')
        generated = original(path, project, outputs, summary, *args, **kwargs)
        summary.design_main_current_a += 10
        return generated
    monkeypatch.setattr(cls, renderer, render)
    with pytest.raises(OSError if failure == 'io' else ExportSnapshotError):
        getattr(cls, method)(str(tmp_path / name), project, outputs, summary, validations=checks)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('case', CASES)
def test_publication_failure_restores_preexisting_empty_directory(tmp_path, monkeypatch, case):
    cls, method, _, name = case
    project, (outputs, summary, checks) = results()
    target = tmp_path / name
    target.mkdir()
    import os
    original = os.replace
    def replace(source, dest):
        if str(dest) == str(target):
            raise PermissionError('synthetic directory publication failure')
        return original(source, dest)
    monkeypatch.setattr('lv_assist.library_export.os.replace', replace)
    with pytest.raises(OSError):
        getattr(cls, method)(str(target), project, outputs, summary, validations=checks)
    assert target.is_dir() and not list(target.iterdir())
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_gui_occupied_library_explains_no_overwrite(tmp_path, monkeypatch, locale):
    project, result = results()
    parent = tmp_path
    target = parent / 'IEC_Schematics'
    target.mkdir()
    (target / 'user.svg').write_bytes(b'user edited drawing')
    previous = i18n.get_language()
    warnings, successes = [], []
    monkeypatch.setattr('lv_assist.gui.filedialog.askdirectory', lambda **kwargs: str(parent))
    monkeypatch.setattr('lv_assist.gui.messagebox.showwarning', lambda title, message: warnings.append(message))
    monkeypatch.setattr('lv_assist.gui.messagebox.showinfo', lambda *args: successes.append(args))
    app = SimpleNamespace(_results_are_current=lambda: True, last_results=result, current_project=project)
    try:
        i18n.set_language(locale)
        LVAssistApp.action_save_all_svgs_folder(app)
        assert warnings == [tr('library_exists')] and not successes
        assert (target / 'user.svg').read_bytes() == b'user edited drawing'
    finally:
        i18n.set_language(previous)
