"""Companion-product scope, functional handoff and conceptual architecture tests."""

import csv
import importlib.util
import json
import re
from dataclasses import asdict
from itertools import pairwise
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import openpyxl
import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.control_circuits import ControlCircuitGenerator
from lv_assist.engine import EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.functional_connections import FunctionalConnections
from lv_assist.gui import LVAssistApp
from lv_assist.gui_output_bridge import GuiOutputBridge
from lv_assist.i18n import i18n, tr
from lv_assist.layout import PanelLayoutGenerator
from lv_assist.models import FeederInput, LoadType, ProjectSpec


def calculate(load_type=LoadType.MOTOR_DOL, *, identifier='F1', voltage=400, fault=22):
    project = ProjectSpec(project_name='Companion design', prospective_ik_ka=fault, nominal_voltage_v=voltage)
    inputs = [FeederInput(feeder_id=identifier, description='Proposed load', load_type=load_type, power_kw=15)]
    return project, EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, inputs)


@pytest.mark.parametrize('name', ['eplan_macro', 'eplan_macro_files', 'eplan_field_test', 'dxf_export'])
def test_retired_generators_are_absent_from_active_package(name):
    assert importlib.util.find_spec('lv_assist.' + name) is None


@pytest.mark.parametrize('name', ['action_export_eplan_script', 'action_export_eplan_macros',
                                  'action_export_eplan_page_macros', 'action_export_eplan_test_kit',
                                  'action_export_dxf'])
def test_retired_product_actions_cannot_be_invoked(name):
    assert not hasattr(LVAssistApp, name)


@pytest.mark.parametrize('load_type', list(LoadType))
def test_functional_relationships_cover_loads_without_fabricated_wire_or_pin_data(load_type):
    project, (outputs, summary, _) = calculate(load_type)
    rows = FunctionalConnections.build(project, outputs, summary)
    feeder_rows = [row for row in rows if row.scope_type == 'FEEDER']
    assert feeder_rows and {row.scope for row in feeder_rows} == {'F1'}
    assert all(row.status == 'PROPOSED' for row in rows)
    assert all(set(asdict(row)).isdisjoint({'wire_no', 'from_pin', 'to_pin', 'section', 'color'}) for row in rows)
    power = [row for row in feeder_rows if row.kind == 'POWER']
    assert power[0].source == tr('fc_node_bus')
    assert power[-1].target == tr('fc_node_motor' if load_type.value.startswith('MOTOR_') else 'fc_node_load') + ' (F1)'
    for left, right in pairwise(power):
        assert left.target == right.source
    if load_type.value.startswith('MOTOR_'):
        command = next(row for row in feeder_rows if row.kind == 'CONTROL')
        feedback = next(row for row in feeder_rows if row.kind == 'SIGNAL')
        assert command.source == feedback.target and command.target == feedback.source
        assert command.source_parts == ()  # no invented PLC/controller selection
    selected = outputs[0].selected_protection
    if selected is not None:
        assert power[0].target_parts == (selected.part_number,)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_bundle_preserves_remaining_outputs_and_never_generates_retired_assets(tmp_path, locale):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        project, run = calculate()
        path = tmp_path / 'companion.zip'
        count = LVAssistApp.build_document_bundle(str(path), project, *run, include_pdf=False)
        with ZipFile(path) as archive:
            names = archive.namelist()
            assert count == len(names) == 13
            assert not any(name.endswith(('.ema', '.emp', '.dxf', '.dwg', '.cs')) for name in names)
            assert not any('Macro' in name or 'FieldTest' in name or 'Panel_Layout' in name for name in names)
            assert {'06_Functional_Connections.csv', '07_Architecture_Overview.svg',
                    '03_Single_Line_Diagram.svg', '04_Time_Current_Curves.svg',
                    '05_Control_Circuits.svg', '09_EPLAN_Parts_Import.csv',
                    '10_EPLAN_Parts_Management.csv'} <= set(names)
            manifest = json.loads(archive.read('00_Export_Manifest.json'))
            assert {row['path'] for row in manifest['files'] if row['status'] == 'GENERATED'} <= set(names)
            assert tr('fc_title') in archive.read('02_Engineering_Report.html').decode()
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_csv_xlsx_and_html_use_identical_functional_rows_and_literal_tags(tmp_path, locale):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        project, (outputs, summary, checks) = calculate(identifier='=F<&1')
        expected = [tuple(row.cells()) for row in FunctionalConnections.build(project, outputs, summary)]
        csv_path, xlsx, html = tmp_path / 'connections.csv', tmp_path / 'report.xlsx', tmp_path / 'report.html'
        FunctionalConnections.export_csv(str(csv_path), project, outputs, summary, validations=checks)
        ExcelExporter.export_to_excel(str(xlsx), project, outputs, summary, checks)
        PrintableReportExporter.generate_html_report(str(html), project, outputs, summary, checks)
        with csv_path.open(encoding='utf-8-sig', newline='') as stream:
            exported = list(csv.reader(stream))
        assert exported[0][:8] == list(FunctionalConnections.headers())
        assert [tuple(row[:8]) for row in exported[1:]] == expected
        assert not any(header in exported[0] for header in ('Wire No.', 'From pin', 'To pin', 'Color', 'Cross-section (mm²)'))
        book = openpyxl.load_workbook(xlsx)
        try:
            sheet = book['05_Functional_Connections']
            values = list(sheet.values)
            assert values[0] == FunctionalConnections.headers()
            assert values[1:1 + len(expected)] == [tuple(value or None for value in row) for row in expected]
            assert all(cell.data_type == 's' for row in sheet for cell in row if isinstance(cell.value, str))
        finally:
            book.close()
        assert 'id="functional-connections"' in html.read_text()
        assert '=F&lt;&amp;1' in html.read_text()
        compatibility = tmp_path / 'old-api.csv'
        ControlCircuitGenerator.export_connections_csv(str(compatibility), project, outputs, summary, validations=checks)
        assert compatibility.read_bytes() == csv_path.read_bytes()
    finally:
        i18n.set_language(previous)


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
@pytest.mark.parametrize('load_type', [LoadType.MOTOR_DOL, LoadType.MOTOR_STAR_DELTA, LoadType.MOTOR_VFD])
def test_architecture_shows_functional_groups_and_parts_without_execution_dimensions(locale, load_type):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        project, (outputs, summary, _) = calculate(load_type)
        svg = PanelLayoutGenerator.generate_svg(project, outputs, summary)
        root = ET.fromstring(svg)
        visible = ' '.join(node.get('aria-label') or node.text or '' for node in root.findall('{http://www.w3.org/2000/svg}text'))
        assert tr('arch_title') in visible and tr('arch_main_power') in visible
        assert 'F1' in visible and 'Proposed load' in visible
        assert 'ductHatch' not in svg
        assert not re.search(r'\b(?:W|H|D)\s*=|\d\s*(?:mm|cm)\b', visible)
        assert 'PRELIMINARY' in visible and summary.status.value in visible
        assert tr('arch_not_layout') in visible
        if summary.main_breaker:
            compact = ''.join(visible.split())
            assert summary.main_breaker.part_number in compact
    finally:
        i18n.set_language(previous)


def test_panel_and_feeder_scope_collision_does_not_merge_architecture_groups():
    project, (outputs, summary, _) = calculate(identifier='+MCC1')
    rows = FunctionalConnections.build(project, outputs, summary)
    assert {row.scope_type for row in rows} == {'PANEL', 'FEEDER'}
    assert sum(row.kind == 'POWER' and row.scope_type == 'FEEDER' for row in rows) == 3
    assert 'Proposed load' in PanelLayoutGenerator.generate_svg(project, outputs, summary)


@pytest.mark.parametrize('fault,voltage', [(None, 400), (22, 690)])
def test_remaining_sld_bridge_does_not_invent_fault_or_use_400v_rating(fault, voltage):
    project, (outputs, summary, _) = calculate(fault=fault, voltage=voltage)
    dto = GuiOutputBridge.to_sld_dto(project, outputs, summary)
    assert dto.prospective_ik_ka == summary.ik_bus_total_ka
    if fault is None:
        assert dto.prospective_ik_ka is None
        assert "Ik'' = ? kA" in GuiOutputBridge.generate_sld_svg(project, outputs, summary)
    if voltage == 690:
        assert dto.main_breaker_icu_ka is None


def test_gui_displays_functional_rows_for_whole_panel_and_selected_feeder():
    project, (outputs, summary, checks) = calculate()
    inserted = []
    selection = ['SLD: all']
    app = SimpleNamespace(_results_are_current=lambda: True, last_results=(outputs, summary, checks),
        current_project=project, _get_selected_svg_and_name=lambda: ('<svg/>', 'preview.svg'),
        cmb_sheet_selector=SimpleNamespace(get=lambda: selection[0]),
        tree_wires_preview=SimpleNamespace(get_children=lambda: (), delete=lambda *a: None,
            insert=lambda *a, **kw: inserted.append(kw['values'])),
        txt_svg_inspector=SimpleNamespace(delete=lambda *a: None, insert=lambda *a: None))
    LVAssistApp.action_refresh_schematic_preview(app)
    expected = FunctionalConnections.build(project, outputs, summary)
    assert inserted == [row.cells() for row in expected]
    inserted.clear()
    selection[0] = 'Feeder F1 — Proposed load'
    LVAssistApp.action_refresh_schematic_preview(app)
    assert inserted == [row.cells() for row in expected if row.scope_type == 'FEEDER']


def test_persian_architecture_has_shaped_labels_and_original_accessible_text():
    previous = i18n.get_language()
    try:
        i18n.set_language('fa')
        project, (outputs, summary, _) = calculate()
        root = ET.fromstring(PanelLayoutGenerator.generate_svg(project, outputs, summary))
        labels = root.findall('{http://www.w3.org/2000/svg}text')
        title = next(label for label in labels if label.get('aria-label') == tr('arch_title'))
        assert title.text != tr('arch_title')
        assert any('\ufb50' <= character <= '\ufeff' for character in title.text)
        assert 'bidi-override' in title.get('style')
        assert not any(label.get('x') == '50%' for label in labels)
    finally:
        i18n.set_language(previous)


def test_svg_text_shaping_preserves_literal_xml_and_latin_identifiers():
    from lv_assist.svg_typography import readable_labels
    svg = '<svg><text x="1">Motor &lt;F1&gt; &amp; 3RV2021</text></svg>'
    label = ET.fromstring(readable_labels(svg)).find('text')
    assert label.text == 'Motor <F1> & 3RV2021'
    assert label.get('aria-label') == label.text
