"""Catalog scope regressions using synthetic enclosure declarations."""

import openpyxl
import pytest

from lv_assist.catalog import CatalogRepository, catalog_repo
from lv_assist.engine import EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.i18n import i18n
from lv_assist.models import (
    CatalogDevice,
    FeederInput,
    LoadType,
    ProjectSpec,
    ValidationStatus,
)
from lv_assist.outputs import _bom_entries
from lv_assist.run_metadata import selection_hash


def enclosure(part, maker='TEST', width=800, ip='IP66'):
    return CatalogDevice(part_number=part, manufacturer=maker, series='SYNTHETIC',
                         device_type='ENCLOSURE', width_mm=width, height_mm=2000,
                         depth_mm=600, ip_rating=ip)


def calculate(engine, **kwargs):
    project = ProjectSpec(project_name='Catalog scope test', **kwargs)
    inputs = [FeederInput(feeder_id='F1', description='Small load',
                          load_type=LoadType.SUB_FEEDER, power_kw=1)]
    return project, engine.process_project(project, inputs)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('present', [True, False])
def test_only_run_catalog_reaches_summary_bom_and_reports(locale, present, monkeypatch, tmp_path):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        # A repository candidate is deliberately incompatible with the supplied
        # catalog identity. It must not be consulted by the calculation path.
        monkeypatch.setattr(catalog_repo, 'get_compatible_enclosures',
                            lambda target: [enclosure('OUTSIDE-RUN')])
        devices = CatalogRepository.get_default_catalog()
        devices = [device for device in devices if device.device_type != 'ENCLOSURE']
        if present:
            devices.append(enclosure('IN-RUN'))
        engine = EngineeringEngine(devices)
        project, (feeders, summary, checks) = calculate(engine)
        expected = 'IN-RUN' if present else 'EST-PANEL'
        assert summary.selected_enclosure.part_number == expected
        assert summary.run_metadata.catalog_selection_hash == selection_hash(engine.catalog)
        entries = _bom_entries(project, feeders, summary)
        cabinet = next(entry for entry in entries if entry[2] == '-U0')
        assert cabinet[4].part_number == expected
        assert all(not entry[4] or entry[4].part_number != 'OUTSIDE-RUN' for entry in entries)
        if not present:
            assert summary.effective_ip_str == '?'
            assert any(check.rule_id == 'RULE-ENC-IP-019' and
                       check.status == ValidationStatus.INSUFFICIENT_DATA for check in checks)
        html, xlsx = tmp_path / 'report.html', tmp_path / 'report.xlsx'
        PrintableReportExporter.generate_html_report(str(html), project, feeders, summary, checks)
        ExcelExporter.export_to_excel(str(xlsx), project, feeders, summary, checks)
        content = html.read_text(encoding='utf-8')
        assert expected in content and 'OUTSIDE-RUN' not in content
        book = openpyxl.load_workbook(xlsx)
        values = [cell.value for sheet in book for row in sheet for cell in row]
        assert expected in values and 'OUTSIDE-RUN' not in values
        book.close()
    finally:
        i18n.set_language(previous)


def test_repeated_runs_restore_catalog_after_manufacturer_filter():
    engine = EngineeringEngine([enclosure('OTHER', width=600), enclosure('ABB-ENC', maker='ABB')])
    _, (_, abb, _) = calculate(engine, preferred_manufacturer='ABB')
    assert abb.selected_enclosure.part_number == 'ABB-ENC'
    _, (_, any_maker, _) = calculate(engine)
    assert any_maker.selected_enclosure.part_number == 'OTHER'
    assert abb.run_metadata.catalog_selection_hash != any_maker.run_metadata.catalog_selection_hash
    _, (_, abb_again, _) = calculate(engine, preferred_manufacturer='ABB')
    assert abb_again.selected_enclosure.part_number == 'ABB-ENC'
    assert abb_again.run_metadata.catalog_selection_hash == abb.run_metadata.catalog_selection_hash


def test_supplied_enclosure_still_requires_supported_ip():
    engine = EngineeringEngine([enclosure('UNSUPPORTED', ip='IP68')])
    _, (_, summary, checks) = calculate(engine)
    assert summary.selected_enclosure.part_number == 'EST-PANEL'
    assert summary.effective_ip_str == '?'
    assert any(check.rule_id == 'RULE-ENC-IP-019' for check in checks)
