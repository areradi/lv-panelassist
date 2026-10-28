"""Synthetic busbar verdict regressions, not engineering reference cases."""

import openpyxl
import pytest

from lv_assist.busbar import BusbarEngine
from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.i18n import i18n
from lv_assist.models import FeederInput, LoadType, ProjectSpec, ValidationStatus


@pytest.mark.parametrize('fault', [None, 1, 1000])
@pytest.mark.parametrize('current', [100, 1464, 2000])
def test_continuous_current_verdict_depends_on_selected_rating(current, fault):
    result = BusbarEngine.select(current, fault, 800)
    checks = {check.rule_id: check for check in result.validations}
    assert (checks['RULE-BUS-024'].status == ValidationStatus.ERROR) == (result.rating_a < current)
    if fault == 1000:
        assert checks['RULE-BUS-025'].status == ValidationStatus.ERROR
        assert checks['RULE-BUS-026'].status == ValidationStatus.ERROR
    if fault is None:
        assert all(checks[key].status == ValidationStatus.INSUFFICIENT_DATA
                   for key in ('RULE-BUS-025', 'RULE-BUS-026', 'RULE-BUS-027'))


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_fault_failure_does_not_become_ampacity_failure_in_engine_reports(locale, tmp_path):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        project = ProjectSpec(project_name='Synthetic busbar verdict', prospective_ik_ka=1000)
        inputs = [FeederInput(feeder_id='F1', description='Synthetic load',
                              load_type=LoadType.SUB_FEEDER, power_kw=15)]
        feeders, summary, checks = EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)
        rows = {check.rule_id: check for check in checks if check.rule_id.startswith('RULE-BUS-')}
        assert summary.busbar_rating_a >= summary.design_main_current_a
        assert rows['RULE-BUS-024'].status == ValidationStatus.WARNING
        assert rows['RULE-BUS-025'].status == ValidationStatus.ERROR
        assert rows['RULE-BUS-026'].status == ValidationStatus.ERROR
        html = tmp_path / 'report.html'
        xlsx = tmp_path / 'report.xlsx'
        PrintableReportExporter.generate_html_report(str(html), project, feeders, summary, checks)
        ExcelExporter.export_to_excel(str(xlsx), project, feeders, summary, checks)
        assert rows['RULE-BUS-024'].description in html.read_text(encoding='utf-8')
        workbook = openpyxl.load_workbook(xlsx)
        exported = list(workbook['03_Validation_Log'].iter_rows(min_row=2, values_only=True))
        for key in ('RULE-BUS-024', 'RULE-BUS-025', 'RULE-BUS-026'):
            row = next(row for row in exported if row[0] == key)
            assert row[3] == rows[key].status.value
            assert row[4] == rows[key].description
        workbook.close()
    finally:
        i18n.set_language(previous)
