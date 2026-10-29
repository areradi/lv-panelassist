"""Secondary IEC preview/injection APIs share the accepted-run boundary."""

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.export_preflight import ExportSnapshotError
from lv_assist.exporters import PrintableReportExporter
from lv_assist.gui_output_bridge import GuiOutputBridge
from lv_assist.models import FeederInput, LoadType, ProjectSpec


def results():
    project = ProjectSpec(project_name='IEC <preview> & project')
    feeder = FeederInput(feeder_id='F1', description='Motor', load_type=LoadType.MOTOR_DOL, power_kw=15)
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, [feeder])


@pytest.mark.parametrize('method', ['export_selected_preview', 'inject_schematics_into_html_report'])
@pytest.mark.parametrize('change', ['project', 'checks', 'missing'])
def test_stale_preview_or_injection_preserves_previous_document(tmp_path, method, change):
    project, (outputs, summary, checks) = results()
    target = tmp_path / 'previous.html'
    target.write_bytes(b'previous report')
    if change == 'project':
        project.project_name = 'Changed'
    elif change == 'checks':
        checks.clear()
    else:
        summary.run_metadata = None
    with pytest.raises(ExportSnapshotError):
        getattr(GuiOutputBridge, method)(str(target), project, outputs, summary, validations=checks)
    assert target.read_bytes() == b'previous report'


def test_valid_preview_escapes_title_and_shows_preliminary_status(tmp_path):
    project, (outputs, summary, checks) = results()
    target = tmp_path / 'preview.html'
    GuiOutputBridge.export_selected_preview(str(target), project, outputs, summary,
                                            validations=checks, feeder_id='F1')
    html = target.read_text()
    assert '<title>IEC &lt;preview&gt; &amp; project</title>' in html
    assert 'PRELIMINARY' in html and summary.status.value in html
    assert summary.run_metadata.input_fingerprint in html


def test_injection_requires_matching_base_report_and_publishes_atomically(tmp_path):
    project, (outputs, summary, checks) = results()
    target = tmp_path / 'report.html'
    target.write_text('<html>old report without run identity</html>')
    before = target.read_bytes()
    with pytest.raises(ExportSnapshotError):
        GuiOutputBridge.inject_schematics_into_html_report(str(target), project, outputs, summary, validations=checks)
    assert target.read_bytes() == before
    PrintableReportExporter.generate_html_report(str(target), project, outputs, summary, checks)
    GuiOutputBridge.inject_schematics_into_html_report(str(target), project, outputs, summary, validations=checks)
    assert 'PRELIMINARY' in target.read_text()
    assert target.read_text().count('<svg') >= 2
