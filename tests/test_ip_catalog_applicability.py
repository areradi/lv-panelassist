"""Conservative software applicability tests; no IP certification implied."""

import openpyxl
import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.i18n import i18n
from lv_assist.ip_rating import ip_meets
from lv_assist.models import (
    CatalogDevice,
    FeederInput,
    LoadType,
    ProjectSpec,
    ValidationStatus,
)


@pytest.mark.parametrize('actual,required', [
    ('IP67', 'IP65'), ('IP68', 'IP65'), ('IP69', 'IP66'),
    ('IP68', 'IP67'), ('IP69', 'IP68'), ('IP67', 'IP67'),
    ('IP66', 'IP67'), ('IP69', 'IP69'), ('IP68', 'IP00'),
])
def test_special_water_categories_need_separate_applicability(actual, required):
    assert not ip_meets(actual, required)


@pytest.mark.parametrize('actual,required,expected', [
    ('IP66', 'IP65', True), ('IP65', 'IP56', False), ('IP56', 'IP65', False),
    ('IP00', 'IP00', True), ('IP54', 'IP43', True), ('IPX5', 'IP45', False),
])
def test_supported_dimensions_keep_existing_conservative_comparison(actual, required, expected):
    assert ip_meets(actual, required) == expected


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('target,ratings,selected', [
    ('IP65', ['IP68', 'IP66'], 'E1'),
    ('IP65', ['IP67', 'IP68', 'IP69'], 'EST-PANEL'),
    ('IP69', ['IP69', 'IP66'], 'EST-PANEL'),
])
def test_actual_catalog_selection_and_reports_preserve_missing_applicability(
    monkeypatch, tmp_path, locale, target, ratings, selected,
):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        devices = [device for device in CatalogRepository.get_default_catalog()
                   if device.device_type != 'ENCLOSURE']
        devices += [CatalogDevice(part_number=f'E{index}', manufacturer='SYNTHETIC',
                                  series='TEST ONLY', device_type='ENCLOSURE', ip_rating=rating,
                                  width_mm=800, height_mm=2000, depth_mm=600)
                    for index, rating in enumerate(ratings)]
        monkeypatch.setattr(CatalogRepository, 'devices', property(lambda self: devices))
        repository = CatalogRepository()
        compatible = repository.get_compatible_enclosures(target)
        assert [item.part_number for item in compatible] == ([] if selected == 'EST-PANEL' else [selected])
        project = ProjectSpec(project_name='Synthetic IP applicability', target_ip=target)
        inputs = [FeederInput(feeder_id='F1', description='Small load',
                              load_type=LoadType.SUB_FEEDER, power_kw=1)]
        feeders, summary, checks = EngineeringEngine(devices).process_project(project, inputs)
        assert summary.selected_enclosure.part_number == selected
        if selected == 'EST-PANEL':
            assert summary.effective_ip_str == '?'
            missing = [check for check in checks if check.rule_id in ('RULE-ENC-IP-019', 'RULE-ENC-IP-020')]
            assert len(missing) == 2
            assert all(check.status == ValidationStatus.INSUFFICIENT_DATA for check in missing)
        else:
            missing = [check for check in checks if check.rule_id == 'RULE-ENC-IP-020']
            assert missing[0].status == ValidationStatus.WARNING
        html, xlsx = tmp_path / 'ip.html', tmp_path / 'ip.xlsx'
        PrintableReportExporter.generate_html_report(str(html), project, feeders, summary, checks)
        ExcelExporter.export_to_excel(str(xlsx), project, feeders, summary, checks)
        content = html.read_text(encoding='utf-8')
        book = openpyxl.load_workbook(xlsx)
        rows = list(book['03_Validation_Log'].iter_rows(min_row=2, values_only=True))
        for check in missing:
            assert check.description in content
            row = next(row for row in rows if row[0] == check.rule_id)
            assert row[3] == check.status.value
        book.close()
    finally:
        i18n.set_language(previous)
