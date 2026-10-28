"""Synthetic inequality/range policy tests, not manufacturer reference cases."""

import openpyxl
import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.core_verification import verify_overload_coordination
from lv_assist.engine import CableSizingEngine, EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.models import (
    CatalogDevice,
    FeederInput,
    LoadType,
    ProjectSpec,
    ValidationStatus,
)


def run(*, ir=50, i2=70, frame=100, minimum=40, maximum=100,
        power=5, section=10, kind="MCCB"):
    catalog = [device for device in CatalogRepository.get_default_catalog()
               if device.device_type not in ("MCB", "MCCB", "MPCB")]
    catalog.append(CatalogDevice(part_number="SYNTHETIC-SETTING-TEST", manufacturer="TEST",
                                 series="TEST", device_type=kind, rated_current_in_a=frame,
                                 setting_min_a=minimum, setting_max_a=maximum))
    project = ProjectSpec(project_name="Setting inequality test", prospective_ik_ka=22,
                          ambient_temp_c=30, cable_grouping_factor_k2=1)
    feeder = FeederInput(feeder_id="F1", description="Synthetic policy case", load_type=LoadType.SUB_FEEDER,
                         power_kw=power, cable_length_m=20, cable_section_mm2=section,
                         protection_ir_a=ir, protection_i2_a=i2)
    outputs, summary, checks = EngineeringEngine(catalog).process_project(project, [feeder])
    overload = next(check for check in checks if check.rule_id == "RULE-CABLE-OVERLOAD")
    cable = next(check for check in checks if check.rule_id == "RULE-CABLE-009")
    return project, outputs, summary, checks, overload, cable


def test_frame_above_ampacity_is_not_an_error_when_actual_setting_is_lower(tmp_path):
    project, outputs, summary, checks, overload, cable = run()
    assert outputs[0].selected_protection.rated_current_in_a > outputs[0].cable_derated_iz_a
    assert overload.input_values["ir_a"] < outputs[0].cable_derated_iz_a
    assert overload.status == cable.status == ValidationStatus.WARNING
    assert overload.input_values == cable.input_values
    assert overload.supporting_evidence == cable.supporting_evidence
    assert "Ir=50 A" in overload.supporting_evidence
    assert "frame In=100 A" in overload.supporting_evidence
    assert outputs[0].selection_status == "PROPOSED"
    path = tmp_path / "settings.xlsx"
    ExcelExporter.export_to_excel(str(path), project, outputs, summary, checks)
    workbook = openpyxl.load_workbook(path)
    for row in workbook["03_Validation_Log"].iter_rows(min_row=2, values_only=True):
        if row[0] in ("RULE-CABLE-009", "RULE-CABLE-OVERLOAD"):
            assert row[3] == "WARNING" and "Ir=50 A" in row[5]
    workbook.close()
    html = tmp_path / "settings.html"
    PrintableReportExporter.generate_html_report(str(html), project, outputs, summary, checks)
    assert "Ir=50 A" in html.read_text(encoding="utf-8")


@pytest.mark.parametrize("changes,expected", [
    ({"ir": None}, "INSUFFICIENT_DATA"),
    ({"i2": None}, "INSUFFICIENT_DATA"),
    ({"minimum": 0, "maximum": 0}, "INSUFFICIENT_DATA"),
    ({"ir": 60}, "ERROR"),  # Known Ir above Iz.
    ({"ir": 30}, "ERROR"),  # Below stated setting range, even though Ir < Iz.
    ({"ir": 110}, "ERROR"),  # Above frame/range.
    ({"i2": 100}, "ERROR"),  # Known I2 condition fails.
    ({"ir": None, "power": 50}, "ERROR"),  # Ib > Iz is impossible for every Ir.
    ({"kind": "MCB", "frame": 50, "ir": 40, "minimum": 0, "maximum": 0}, "ERROR"),
    ({"kind": "MCB", "frame": 50, "ir": None, "minimum": 0, "maximum": 0}, "WARNING"),
])
def test_one_setting_verdict_reaches_both_legacy_and_structured_checks(changes, expected):
    _, _, _, _, overload, cable = run(**changes)
    assert overload.status.value == cable.status.value == expected
    assert overload.input_values == cable.input_values


def test_load_above_ampacity_is_an_error_even_without_ir():
    check = verify_overload_coordination(60, None, 57, None)
    assert check.status == ValidationStatus.ERROR


@pytest.mark.parametrize("minimum,maximum", [(-1, 100), (100, 40)])
def test_invalid_catalog_range_is_rejected_before_a_result_is_created(minimum, maximum):
    with pytest.raises(ValueError):
        run(minimum=minimum, maximum=maximum, ir=None)


def test_no_protection_device_cannot_complete_coordination():
    catalog = [device for device in CatalogRepository.get_default_catalog()
               if device.device_type not in ("MCB", "MCCB", "MPCB")]
    project = ProjectSpec(project_name="No protective device", prospective_ik_ka=22)
    feeder = FeederInput(feeder_id="F1", description="Load", load_type=LoadType.SUB_FEEDER,
                         power_kw=5, cable_length_m=20)
    outputs, _, checks = EngineeringEngine(catalog).process_project(project, [feeder])
    assert outputs[0].selected_protection is None
    for check in checks:
        if check.rule_id in ("RULE-CABLE-009", "RULE-CABLE-OVERLOAD"):
            assert check.status == ValidationStatus.INSUFFICIENT_DATA
            assert check.input_values["device_selected"] is False


def test_missing_range_is_reported_as_unknown_not_a_zero_amp_setting():
    _, _, _, _, overload, _ = run(minimum=0, maximum=0)
    assert overload.status == ValidationStatus.INSUFFICIENT_DATA
    assert overload.input_values["setting_min_a"] is None
    assert overload.input_values["setting_max_a"] is None
    assert "setting range=?..? A" in overload.supporting_evidence


def test_auto_cable_proposal_uses_known_ir_and_keeps_unknown_setting_conservative():
    args = {"ib_a": 45, "protection_in_a": 100, "is_adjustable_prot": True,
            "length_m": 20, "cos_phi": 0.9, "voltage_v": 400, "phases": 3,
            "ambient_temp_c": 30, "grouping_k2": 1, "max_vdrop_pct": 5,
            "load_type": LoadType.SUB_FEEDER}
    known = CableSizingEngine.select_feeder_cable(**args, protection_ir_a=50)
    unknown = CableSizingEngine.select_feeder_cable(**args)
    assert 50 <= known[3] < 100
    assert unknown[3] >= 100
    assert known[0] < unknown[0]


@pytest.mark.parametrize("invalid", [0, -1, float("nan"), float("inf")])
def test_invalid_direct_setting_does_not_size_a_cable(invalid):
    with pytest.raises(ValueError):
        CableSizingEngine.select_feeder_cable(
            ib_a=45, protection_in_a=100, is_adjustable_prot=True, length_m=20,
            cos_phi=0.9, voltage_v=400, phases=3, ambient_temp_c=30, grouping_k2=1,
            max_vdrop_pct=5, load_type=LoadType.SUB_FEEDER, protection_ir_a=invalid)
