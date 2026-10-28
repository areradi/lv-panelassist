"""Unchanged run IDs must not conceal modified calculated data or check rows."""

from types import SimpleNamespace

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.gui import LVAssistApp
from lv_assist.models import FeederInput, LoadType, ProjectSpec, ValidationStatus
from lv_assist.run_metadata import result_fingerprint


def results():
    project = ProjectSpec(project_name='Derived result fingerprint')
    inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
    result = EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)
    return project, inputs, result


def modify(result, change):
    outputs, summary, checks = result
    if change == 'current':
        outputs[0].design_current_ib_a += 10
    elif change == 'cable':
        outputs[0].cable_designation_str = 'Modified cable'
    elif change == 'part':
        summary.selected_enclosure.part_number = 'OTHER-PART'
    elif change == 'summary':
        summary.design_main_current_a += 10
    elif change == 'status':
        summary.status = ValidationStatus.COMPLETED
    elif change == 'check':
        checks[0].status = ValidationStatus.COMPLETED
    elif change == 'reason':
        checks[0].reason = 'Altered review reason'
    elif change == 'removed':
        checks.clear()
    elif change == 'legacy':
        metadata = summary.run_metadata.model_copy(update={'result_fingerprint': None})
        summary.run_metadata = metadata
        for output in outputs:
            output.run_metadata = metadata


@pytest.mark.parametrize('change', ['current', 'cable', 'part', 'summary', 'status', 'check', 'reason', 'removed', 'legacy'])
def test_modified_derived_data_cannot_be_bundled_with_old_run_id(tmp_path, change):
    project, _, result = results()
    outputs, summary, checks = result
    run_id = summary.run_metadata.input_fingerprint
    modify(result, change)
    assert summary.run_metadata.input_fingerprint == run_id
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    with pytest.raises(ExportSnapshotError):
        LVAssistApp.build_document_bundle(str(path), project, outputs, summary, checks, include_pdf=False)
    assert path.read_bytes() == b'previous bundle'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('change', ['current', 'part', 'check', 'removed', 'legacy'])
def test_gui_marks_modified_derived_result_stale(change):
    project, inputs, result = results()
    app = SimpleNamespace(_stale=False, last_results=result, current_project=project, current_feeders=inputs)
    assert LVAssistApp._results_are_current(app)
    modify(result, change)
    assert not LVAssistApp._results_are_current(app)
    assert app._stale


def test_unchanged_result_and_private_copy_have_same_fingerprint(tmp_path):
    import copy
    import json
    from zipfile import ZipFile

    project, _, result = results()
    outputs, summary, checks = result
    assert summary.run_metadata.result_fingerprint == result_fingerprint(*result)
    assert result_fingerprint(*copy.deepcopy(result)) == summary.run_metadata.result_fingerprint
    path = tmp_path / 'bundle.zip'
    LVAssistApp.build_document_bundle(str(path), project, outputs, summary, checks, include_pdf=False)
    with ZipFile(path) as archive:
        manifest = json.loads(archive.read('00_Export_Manifest.json'))
        assert manifest['run_metadata']['result_fingerprint'] == summary.run_metadata.result_fingerprint


def test_generator_mutation_is_rejected_before_publication(tmp_path, monkeypatch):
    project, _, result = results()
    original = LVAssistApp._build_document_bundle
    def build(path, project, outputs, summary, checks, include_pdf):
        generated = original(path, project, outputs, summary, checks, include_pdf)
        summary.design_main_current_a += 10
        return generated
    monkeypatch.setattr(LVAssistApp, '_build_document_bundle', build)
    path = tmp_path / 'old.zip'
    path.write_bytes(b'previous bundle')
    with pytest.raises(ExportSnapshotError):
        LVAssistApp.build_document_bundle(str(path), project, *result, include_pdf=False)
    assert path.read_bytes() == b'previous bundle'
