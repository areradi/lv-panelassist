"""Fault-location policy tests; not independently approved IEC reference cases."""

import math

import openpyxl
import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.core_verification import calculate_network_ik_profile
from lv_assist.engine import EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.i18n import i18n, tr
from lv_assist.models import (
    EarthingSystem,
    FeederInput,
    LoadType,
    ProjectSpec,
    ValidationStatus,
)


def calculate(*, bus=None, transformer=1000, length=100, material="CU", earthing="TN-S", motor=False):
    project = ProjectSpec(project_name="Scoped fault test", transformer_kva=transformer,
                          prospective_ik_ka=bus, earthing_system=earthing)
    feeder = FeederInput(feeder_id="F1", description="Test feeder",
                         load_type=LoadType.MOTOR_DOL if motor else LoadType.SUB_FEEDER,
                         power_kw=15, cable_length_m=length, cable_section_mm2=16,
                         conductor_material=material)
    result = EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, [feeder])
    return project, [feeder], result


@pytest.mark.parametrize("earthing", list(EarthingSystem))
@pytest.mark.parametrize("material", ["CU", "AL"])
def test_transformer_is_not_a_bus_or_earth_fault_input(earthing, material):
    _, _, (outputs, summary, checks) = calculate(earthing=earthing, material=material, motor=True)
    assert summary.ik_used_ka is None and summary.ik_bus_total_ka is None
    assert summary.short_circuit_profile.ik_transformer_3p_ka > 0
    assert summary.short_circuit_profile.ik_main_busbar_3p_ka is None
    assert outputs[0].short_circuit_profile.ik_feeder_start_3p_ka is None
    assert outputs[0].short_circuit_profile.ik_feeder_end_max_3p_ka is None
    assert outputs[0].short_circuit_profile.ik_feeder_end_min_1p_ka is None
    assert outputs[0].starting_dip_pct is None
    assert outputs[0].selected_pe_mm2 is None
    sc_checks = [c for c in checks if c.rule_id in ("RULE-MAIN-SC-001", "RULE-PROT-SC-001")]
    assert len(sc_checks) == 2
    assert all(c.status == ValidationStatus.INSUFFICIENT_DATA for c in sc_checks)
    assert all(c.input_values["ik_at_device_ka"] is None for c in sc_checks)


@pytest.mark.parametrize("transformer", [None, 1000, 2000])
def test_explicit_panel_bus_is_preserved_independently_of_transformer(transformer):
    _, _, (outputs, summary, checks) = calculate(bus=22, transformer=transformer)
    assert summary.ik_used_ka == summary.ik_bus_total_ka == 22
    for profile in (summary.short_circuit_profile, outputs[0].short_circuit_profile):
        assert profile.ik_main_busbar_3p_ka == profile.ik_feeder_start_3p_ka == 22
        assert profile.ik_feeder_end_max_3p_ka is None
        assert profile.ik_feeder_end_min_1p_ka is None
    assert all(c.input_values["ik_at_device_ka"] == 22 for c in checks
               if c.rule_id in ("RULE-MAIN-SC-001", "RULE-PROT-SC-001"))


def test_motor_adjusted_bus_profile_and_device_comparison_share_one_value():
    _, _, (outputs, summary, checks) = calculate(bus=22, motor=True)
    assert summary.motor_contribution_ka > 0
    assert summary.ik_bus_total_ka > summary.ik_used_ka
    assert summary.short_circuit_profile.ik_main_busbar_3p_ka == summary.ik_bus_total_ka
    assert outputs[0].short_circuit_profile.ik_feeder_start_3p_ka == summary.ik_bus_total_ka
    assert all(c.input_values["ik_at_device_ka"] == summary.ik_bus_total_ka for c in checks
               if c.rule_id in ("RULE-MAIN-SC-001", "RULE-PROT-SC-001"))


def test_changing_length_does_not_invent_source_or_end_fault_values():
    first = calculate(length=10)[2][0][0].short_circuit_profile
    second = calculate(length=200)[2][0][0].short_circuit_profile
    assert first.ik_transformer_3p_ka == second.ik_transformer_3p_ka
    for profile in (first, second):
        assert profile.ik_main_busbar_3p_ka is None
        assert profile.ik_feeder_end_max_3p_ka is None
        assert not profile.is_attenuated_by_feeder_cable


@pytest.mark.parametrize("argument,value", [
    ("transformer_kva", 0), ("uk_percent", -1), ("line_voltage_v", 0),
    ("main_bus_ik_ka", math.inf), ("main_bus_ik_ka", math.nan),
    ("feeder_cable_length_m", -1), ("line_voltage_v", None),
])
def test_invalid_fault_inputs_return_error_instead_of_plausible_numbers(argument, value):
    values = {"transformer_kva": 1000, "uk_percent": 6, "main_bus_ik_ka": 22}
    values[argument] = value
    profile = calculate_network_ik_profile(**values)
    assert profile.scope_status == ValidationStatus.ERROR
    assert profile.ik_transformer_3p_ka is None and profile.ik_main_busbar_3p_ka is None
    assert all(check.result_value is None for check in profile.checks)


@pytest.mark.parametrize("locale", ["fa", "en", "de"])
@pytest.mark.parametrize("bus", [None, 22])
def test_actual_scope_checks_reach_existing_gui_log_and_html_excel(locale, bus, tmp_path):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        project, _, (outputs, summary, checks) = calculate(bus=bus)
        # GUI uses these same ValidationResult rows, not a separate fault solver.
        scoped = [check for check in checks if check.rule_id.startswith("RULE-IK-")]
        ids = {check.check_id for check in scoped}
        assert {"IK_TRANSFORMER_3P", "IK_MAIN_BUS_3P", "IK_FEEDER_START_3P",
                "IK_FEEDER_END_MAX_3P", "IK_FEEDER_END_MIN_LPE"} <= ids
        assert all(check.status != ValidationStatus.COMPLETED for check in scoped)
        path = tmp_path / "faults.xlsx"
        ExcelExporter.export_to_excel(str(path), project, outputs, summary, checks)
        workbook = openpyxl.load_workbook(path)
        rows = list(workbook["03_Validation_Log"].iter_rows(min_row=2, values_only=True))
        for check in scoped:
            row = next(row for row in rows if row[0] == check.rule_id and row[1] == check.feeder_id)
            assert row[3] == check.status.value
            assert row[4] == check.description and row[5] == check.supporting_evidence
        workbook.close()
        html = tmp_path / "faults.html"
        PrintableReportExporter.generate_html_report(str(html), project, outputs, summary, checks)
        content = html.read_text(encoding="utf-8")
        assert tr("audit_ik_transformer_3p") in content
        assert tr("audit_ik_main_bus_3p") in content
        assert tr("audit_ik_feeder_end_min_lpe") in content
        assert "PRELIMINARY — NOT FOR CONSTRUCTION" in content
    finally:
        i18n.set_language(previous)
