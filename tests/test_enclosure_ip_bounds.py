"""Synthetic component ceilings, never installed assembly IP certification."""

import openpyxl
import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.i18n import i18n, tr
from lv_assist.ip_rating import ip_upper_bound
from lv_assist.models import FeederInput, LoadType, ProjectSpec, ValidationStatus


@pytest.mark.parametrize('ratings,expected', [
    (('IP65', 'IP56'), 'IP55'), (('IP43', 'IP45'), 'IP43'),
    (('IP65', 'IP66', 'IP44'), 'IP44'), (('IP65', ''), None),
    (('IP65', 'IPX4'), None), (('IP65', 'IP54 extra'), None),
    ((), None), (('IP00', 'IP66'), 'IP00'), (('IP65', 'IP68'), None),
    (('IP69', 'IP69'), None),
])
def test_ceiling_requires_exact_known_dimensions(ratings, expected):
    assert ip_upper_bound(*ratings) == expected


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('target,fan_ip,expected', [
    ('IP65', 'IP44', 'IP44'), ('IP65', 'IP56', 'IP55'),
    ('IP43', 'IP45', 'IP43'), ('IP65', 'IP66', 'IP65'),
    ('IP65', '', '?'),
])
def test_actual_fan_rating_bounds_engine_and_reports(tmp_path, locale, target, fan_ip, expected):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        devices = CatalogRepository.get_default_catalog()
        for device in devices:
            if device.device_type == 'FAN_FILTER':
                device.ip_rating = fan_ip
        enclosure = next(device for device in devices if device.device_type == 'ENCLOSURE')
        enclosure = enclosure.model_copy(update={'ip_rating': 'IP66', 'width_mm': 800,
                                                'height_mm': 2000, 'depth_mm': 600})
        devices = [device for device in devices if device.device_type != 'ENCLOSURE'] + [enclosure]
        project = ProjectSpec(project_name='Synthetic IP test', target_ip=target,
                              ambient_temp_c=40, max_internal_temp_c=50)
        inputs = [FeederInput(feeder_id=f'F{i}', description='Synthetic motor',
                              load_type=LoadType.MOTOR_DOL, power_kw=30,
                              cos_phi=0.85, efficiency=0.93) for i in (1, 2)]
        feeders, summary, checks = EngineeringEngine(devices).process_project(project, inputs)
        assert summary.selected_fan is not None
        assert summary.effective_ip_str == expected
        check = next(check for check in checks if check.rule_id == 'RULE-ENC-IP-020')
        assert check.status == (ValidationStatus.INSUFFICIENT_DATA if expected == '?' else ValidationStatus.WARNING)
        assert check.input_values['fan_ip'] == fan_ip
        assert check.method == 'COMPONENT_IP_UPPER_BOUND'
        html = tmp_path / 'ip.html'
        xlsx = tmp_path / 'ip.xlsx'
        PrintableReportExporter.generate_html_report(str(html), project, feeders, summary, checks)
        ExcelExporter.export_to_excel(str(xlsx), project, feeders, summary, checks)
        content = html.read_text(encoding='utf-8')
        assert tr('rpt_eff_ip') in content
        assert check.description in content
        book = openpyxl.load_workbook(xlsx)
        rows = list(book['03_Validation_Log'].iter_rows(min_row=2, values_only=True))
        row = next(row for row in rows if row[0] == check.rule_id)
        assert row[3] == check.status.value and row[4] == check.description
        book.close()
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('enclosure_ip,expected', [('IP66', 'IP54'), ('', '?')])
def test_natural_ventilation_does_not_invent_missing_enclosure_ip(enclosure_ip, expected):
    devices = CatalogRepository.get_default_catalog()
    enclosure = next(device for device in devices if device.device_type == 'ENCLOSURE')
    enclosure = enclosure.model_copy(update={'ip_rating': enclosure_ip, 'width_mm': 800,
                                            'height_mm': 2000, 'depth_mm': 600})
    devices = [device for device in devices if device.device_type != 'ENCLOSURE'] + [enclosure]
    project = ProjectSpec(project_name='Natural ventilation IP test')
    inputs = [FeederInput(feeder_id='F1', description='Small load',
                          load_type=LoadType.SUB_FEEDER, power_kw=1)]
    _, summary, checks = EngineeringEngine(devices).process_project(project, inputs)
    assert summary.selected_fan is None
    assert summary.effective_ip_str == expected
    check = next(check for check in checks if check.rule_id == 'RULE-ENC-IP-020')
    assert 'fan_ip' not in check.input_values
    assert check.status == (ValidationStatus.INSUFFICIENT_DATA if expected == '?' else ValidationStatus.WARNING)
