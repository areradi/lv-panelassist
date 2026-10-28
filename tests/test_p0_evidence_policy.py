"""Synthetic policy cases: metadata completeness does not certify real equipment."""

import pytest
from pydantic import ValidationError

from lv_assist.catalog import (
    CatalogRepository,
    SiemensSelectivityRepository,
    catalog_repo,
)
from lv_assist.catalog_provenance import evaluate_selectivity_status
from lv_assist.core_verification import (
    verify_breaking_capacity_icu,
    verify_overload_coordination,
)
from lv_assist.engine import EngineeringEngine
from lv_assist.ip_rating import ip_meets
from lv_assist.models import (
    CatalogDevice,
    DataQuality,
    FeederInput,
    LoadType,
    ProjectSpec,
    PropertySource,
    SelectivityEvalState,
    SelectivityRuleRecord,
    ValidationStatus,
)


def feeder(**updates):
    return FeederInput(feeder_id="F1", description="Test load", load_type=LoadType.SUB_FEEDER,
                       power_kw=5, cable_length_m=100, cable_section_mm2=16, **updates)


@pytest.mark.parametrize("icu,ik,expected", [
    (20, 25, "ERROR"), (25, 25, "COMPLETED"), (36, 25, "COMPLETED"),
    (None, 25, "INSUFFICIENT_DATA"), (36, None, "INSUFFICIENT_DATA"),
])
def test_numeric_icu_check_is_scoped_and_missing_values_never_pass(icu, ik, expected):
    assert verify_breaking_capacity_icu(icu, ik).status.value == expected


def test_icu_voltage_does_not_mean_nearby_voltage():
    device = next(device for device in catalog_repo.devices if device.device_type == "MCCB")
    assert catalog_repo.get_device_icu_at_voltage(device.part_number, 400) is not None
    assert catalog_repo.get_device_icu_at_voltage(device.part_number, 401) is None
    with pytest.raises(ValueError, match="applicability"):
        catalog_repo.get_device_icu_at_voltage(device.part_number, 401, tolerance_v=20)


@pytest.mark.parametrize("ir,iz,i2,expected", [
    (20, 10, None, "ERROR"), (5, 20, 10, "ERROR"),
    (None, 20, 20, "INSUFFICIENT_DATA"), (10, None, 20, "INSUFFICIENT_DATA"),
    (10, 20, None, "INSUFFICIENT_DATA"), (10, 20, 30, "ERROR"),
    (10, 20, 29, "WARNING"),
])
def test_actual_overload_settings_and_i2_are_required(ir, iz, i2, expected):
    assert verify_overload_coordination(10, ir, iz, i2).status.value == expected


def test_real_engine_uses_overload_verdict_and_cannot_validate_candidate(monkeypatch):
    engine = EngineeringEngine(CatalogRepository.get_default_catalog())
    project = ProjectSpec(project_name="Settings", prospective_ik_ka=25)
    monkeypatch.setattr(engine, "_get_derating_factor", lambda *_: 1)
    outputs, _, checks = engine.process_project(project, [feeder(protection_ir_a=1000)])
    check = next(check for check in checks if check.rule_id == "RULE-CABLE-OVERLOAD")
    assert check.status == ValidationStatus.ERROR
    assert check.input_values["ir_a"] == 1000
    assert outputs[0].status == ValidationStatus.ERROR
    assert outputs[0].selection_status == "PROPOSED"


def test_missing_setting_is_not_inferred_from_adjustability():
    outputs, _, checks = EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(
        ProjectSpec(project_name="Settings", prospective_ik_ka=25), [feeder()])
    check = next(check for check in checks if check.rule_id == "RULE-CABLE-OVERLOAD")
    assert check.status == ValidationStatus.INSUFFICIENT_DATA
    assert check.input_values["i2_a"] is None
    assert outputs[0].selection_status == "PROPOSED"


def source(**updates):
    values = {"value": 36, "unit": "kA", "source_type": "MANUFACTURER", "source_document": "synthetic test document",
              "revision": "test-only", "page_or_table": "table 1", "verified_at": "2026-10-28",
              "verified_by": "synthetic-test-reviewer", "applicability": {"voltage_v": "400"}, "quality": "REAL_VERIFIED"}
    values.update(updates)
    return PropertySource(**values)


@pytest.mark.parametrize("missing", ["source_document", "revision", "page_or_table", "verified_at", "verified_by", "applicability"])
def test_a_quality_label_is_not_property_evidence(missing):
    evidence = source(**{missing: {} if missing == "applicability" else None})
    assert not evidence.has_reviewed_evidence()
    assert evidence.quality == DataQuality.ESTIMATED


def test_one_property_cannot_verify_the_whole_device():
    device = CatalogDevice(part_number="T", manufacturer="T", series="T", device_type="MCCB",
                           data_quality="REAL_VERIFIED", property_sources={"icu_ka": source()})
    assert device.data_quality == DataQuality.ESTIMATED


@pytest.mark.parametrize("ratio", [1.1, 1.5, 1.6, 3])
def test_current_ratio_never_proves_or_disproves_selectivity(ratio):
    upstream = CatalogDevice(part_number="U", manufacturer="T", series="U", device_type="MCCB", rated_current_in_a=100 * ratio)
    downstream = CatalogDevice(part_number="D", manufacturer="T", series="D", device_type="MCCB", rated_current_in_a=100)
    state, _, _ = SiemensSelectivityRepository.evaluate_pair(upstream, downstream, 25, 400)
    assert state in (SelectivityEvalState.PRELIMINARY, SelectivityEvalState.PRELIMINARY_RATIO_ONLY)
    assert evaluate_selectivity_status(100 * ratio, 100).status == ValidationStatus.WARNING


@pytest.mark.parametrize("mismatch", [None, "voltage", "part", "setting", "reviewer"])
def test_manufacturer_rule_requires_exact_pair_voltage_settings_and_recorded_review(monkeypatch, mismatch):
    # Fictional values exercise matching only; they are NOT real reference cases.
    rule = SelectivityRuleRecord(upstream_series="U", upstream_min_in_a=1,
        downstream_series="D", downstream_max_in_a=1000, selectivity_limit_is_ka=36,
        catalog_reference="synthetic test", upstream_part_number="U", downstream_part_number="D",
        operating_voltage_v=400, upstream_setting_a=200, downstream_setting_a=100,
        source=source(verified_by=None if mismatch == "reviewer" else "synthetic-test-reviewer",
                      applicability={"upstream_part_number": "U", "downstream_part_number": "D",
                                     "upstream_manufacturer": "T", "downstream_manufacturer": "T",
                                     "voltage_v": "400", "upstream_setting_a": "200",
                                     "downstream_setting_a": "100", "frequency_hz": "50",
                                     "ambient_temp_c": "40"}))
    monkeypatch.setattr(SiemensSelectivityRepository, "get_selectivity_rules", classmethod(lambda cls: [rule]))
    upstream = CatalogDevice(part_number="X" if mismatch == "part" else "U", rated_current_in_a=200,
                             manufacturer="T", series="U", device_type="MCCB")
    downstream = CatalogDevice(part_number="D", rated_current_in_a=100,
                               manufacturer="T", series="D", device_type="MCB")
    state, _, _ = SiemensSelectivityRepository.evaluate_pair(upstream, downstream, 25,
        415 if mismatch == "voltage" else 400, 160 if mismatch == "setting" else 200, 100,
        frequency_hz=50, ambient_temp_c=40)
    assert (state == SelectivityEvalState.VERIFIED_TOTAL) == (mismatch is None)


@pytest.mark.parametrize("actual,required,expected", [
    ("IP54", "IP55", False), ("IP65", "IP55", True), ("IP65", "IP56", False),
    ("IP66", "IP55", True), ("IP55", "IP65", False), ("invalid", "IP54", False),
])
def test_ip_dimensions_are_compared_separately(actual, required, expected):
    assert ip_meets(actual, required) == expected


def test_empty_duplicate_and_mutated_invalid_projects_are_rejected():
    engine = EngineeringEngine(CatalogRepository.get_default_catalog())
    project = ProjectSpec(project_name="Invalid")
    for inputs in ([], [feeder(), feeder()]):
        with pytest.raises(ValueError):
            engine.process_project(project, inputs)
    invalid = feeder()
    invalid.power_kw = float("inf")
    with pytest.raises(ValidationError):
        engine.process_project(project, [invalid])
    with pytest.raises(ValidationError):
        FeederInput(feeder_id=" ", description="Load", load_type="SUB_FEEDER", power_kw=5)
    with pytest.raises(ValidationError):
        FeederInput(feeder_id="F", description="Load", load_type="SUB_FEEDER", power_kw=5, phases=2)
