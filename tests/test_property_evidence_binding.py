"""Synthetic evidence matching tests; no real source or engineer is simulated."""

import openpyxl
import pytest

from lv_assist.catalog import (
    CatalogRepository,
    SiemensSelectivityRepository,
    catalog_repo,
)
from lv_assist.catalog_provenance import CatalogDataProvenance, DataConfidenceLevel
from lv_assist.engine import EngineeringEngine
from lv_assist.evidence_matching import exact_applicability, exact_value
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
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


def evidence(value=36, **changes):
    fields = {"value": value, "unit": "kA", "source_type": "MANUFACTURER",
              "source_document": "SYNTHETIC TEST DOCUMENT", "revision": "test-only", "page_or_table": "table 1",
              "verified_at": "2026-10-28", "verified_by": "synthetic-test-reviewer",
              "quality": "REAL_VERIFIED", "applicability": {"part_number": "T", "manufacturer": "TEST",
                  "voltage_v": "400", "frequency_hz": "50", "ambient_temp_c": "50"}}
    fields.update(changes)
    return PropertySource(**fields)


CONDITIONS = {"part_number": "T", "manufacturer": "TEST", "voltage_v": 400,
              "frequency_hz": 50, "ambient_temp_c": 50}


@pytest.mark.parametrize("changes", [
    {"value": None}, {"value": ""}, {"value": 36.0001}, {"value": "NaN"},
    {"unit": ""}, {"unit": "A"}, {"unit": "KA"}, {"verified_at": "not-a-date"},
    {"verified_by": "  "}, {"applicability": {"voltage_v": "400"}},
])
def test_incomplete_or_mismatched_property_cannot_supply_reviewed_capacity(changes):
    assert not evidence(**changes).matches(36, "kA", CONDITIONS)


@pytest.mark.parametrize("field,value", [
    ("part_number", "OTHER"), ("manufacturer", "OTHER"), ("voltage_v", "415"),
    ("frequency_hz", "60"), ("ambient_temp_c", "40"), ("unmodelled_poles", "2P"),
])
def test_subject_or_operating_conditions_cannot_be_ignored(field, value):
    conditions = dict(evidence().applicability)
    conditions[field] = value
    assert not evidence(applicability=conditions).matches(36, "kA", CONDITIONS)


def test_exact_numeric_notation_is_allowed_but_tolerance_is_not_invented():
    assert exact_value("36.0", 36)
    assert exact_applicability({"voltage": "4e2"}, {"voltage": 400})
    assert not exact_value("36.0000000001", 36)
    assert evidence(value="36.0").matches(36, "kA", CONDITIONS)


@pytest.mark.parametrize("value", [True, False])
def test_boolean_source_cannot_be_coerced_to_a_measured_current(value):
    with pytest.raises(ValueError):
        evidence(value=value)


def test_named_source_buckets_cannot_promote_whole_device():
    source = evidence(value=1)
    device = CatalogDevice(part_number="T", manufacturer="TEST", series="T", device_type="MCCB",
        data_quality="REAL_VERIFIED", property_sources={name: source for name in
            ("power_loss_w", "dimensions", "thermal", "ip", "icu_ka", "trip_curve")})
    assert all(source.has_reviewed_evidence() for source in device.property_sources.values())
    assert device.data_quality == DataQuality.ESTIMATED


@pytest.mark.parametrize("condition,value", [(None, None), ("voltage_v", "415"),
    ("frequency_hz", "60"), ("ambient_temp_c", "40"), ("upstream_part_number", "OTHER"),
    ("unmodelled_restriction", "unsupported")])
def test_selectivity_proof_must_match_the_rule_scope_and_return_the_actual_document(monkeypatch, condition, value):
    conditions = {"upstream_part_number": "U", "downstream_part_number": "D",
                  "upstream_manufacturer": "TEST", "downstream_manufacturer": "TEST",
                  "voltage_v": "400", "upstream_setting_a": "200", "downstream_setting_a": "100",
                  "frequency_hz": "50", "ambient_temp_c": "50"}
    if condition:
        conditions[condition] = value
    source = evidence(applicability=conditions)
    rule = SelectivityRuleRecord(upstream_series="U", upstream_min_in_a=100,
        downstream_series="D", downstream_max_in_a=100, selectivity_limit_is_ka=36,
        catalog_reference="UNRELATED LABEL", upstream_part_number="U", downstream_part_number="D",
        operating_voltage_v=400, upstream_setting_a=200, downstream_setting_a=100, source=source)
    monkeypatch.setattr(SiemensSelectivityRepository, "get_selectivity_rules", classmethod(lambda cls: [rule]))
    upstream = CatalogDevice(part_number="U", manufacturer="TEST", series="U", device_type="MCCB", rated_current_in_a=200)
    downstream = CatalogDevice(part_number="D", manufacturer="TEST", series="D", device_type="MCCB", rated_current_in_a=100)
    state, _, reference = SiemensSelectivityRepository.evaluate_pair(upstream, downstream, 25, 400, 200, 100,
                                                                    frequency_hz=50, ambient_temp_c=50)
    assert (state == SelectivityEvalState.VERIFIED_TOTAL) is (condition is None)
    if condition is None:
        assert "SYNTHETIC TEST DOCUMENT" in reference and "UNRELATED LABEL" not in reference


@pytest.mark.parametrize("mismatch", [False, True])
def test_real_icu_path_and_reports_use_matching_property_not_whole_device_label(tmp_path, mismatch):
    original = next(device for device in CatalogRepository.get_default_catalog() if device.device_type == "MCCB")
    icu = catalog_repo.get_device_icu_at_voltage(original.part_number, 400)
    source = evidence(value=icu + 1 if mismatch else icu, applicability={
        **evidence().applicability, "part_number": original.part_number, "manufacturer": original.manufacturer})
    candidate = original.model_copy(update={"property_sources": {"icu_ka": source}, "data_quality": DataQuality.REAL_VERIFIED})
    project = ProjectSpec(project_name="Property binding", prospective_ik_ka=1)
    feeder = FeederInput(feeder_id="F1", description="Synthetic property case", load_type=LoadType.SUB_FEEDER, power_kw=1)
    outputs, summary, checks = EngineeringEngine([candidate]).process_project(project, [feeder])
    relevant = [check for check in checks if check.rule_id in ("RULE-PROT-SC-001", "RULE-MAIN-SC-001")]
    assert len(relevant) == 2
    for check in relevant:
        assert check.status == ValidationStatus.WARNING
        assert check.input_values["property_evidence_matches"] is (not mismatch)
        assert bool(check.source_ref) is (not mismatch)
        assert check.input_values["icu_ka"] == icu
    assert outputs[0].selected_protection.data_quality == DataQuality.ESTIMATED
    html = tmp_path / "source.html"
    PrintableReportExporter.generate_html_report(str(html), project, outputs, summary, checks)
    if not mismatch:
        assert "SYNTHETIC TEST DOCUMENT" in html.read_text(encoding="utf-8")
    path = tmp_path / "source.xlsx"
    ExcelExporter.export_to_excel(str(path), project, outputs, summary, checks)
    workbook = openpyxl.load_workbook(path)
    for row in workbook["03_Validation_Log"].iter_rows(min_row=2, values_only=True):
        if row[0] in ("RULE-PROT-SC-001", "RULE-MAIN-SC-001"):
            assert ("SYNTHETIC TEST DOCUMENT" in row[5]) is (not mismatch)
    workbook.close()


@pytest.mark.parametrize("invalid", [0, -1, float("nan"), float("inf")])
def test_invalid_fault_level_cannot_be_a_verified_selectivity_result(invalid):
    upstream = CatalogDevice(part_number="U", manufacturer="TEST", series="U", device_type="MCCB", rated_current_in_a=200)
    downstream = CatalogDevice(part_number="D", manufacturer="TEST", series="D", device_type="MCB", rated_current_in_a=100)
    with pytest.raises(ValueError):
        SiemensSelectivityRepository.evaluate_pair(upstream, downstream, invalid, 400, 200, 100,
                                                   frequency_hz=50, ambient_temp_c=50)


def test_legacy_bibliography_cannot_approve_a_device_for_production():
    record = CatalogDataProvenance(manufacturer="TEST", part_number="T",
        datasheet_title_or_id="SYNTHETIC", datasheet_edition_date="2026",
        confidence=DataConfidenceLevel.REAL_VERIFIED, last_audited_by="synthetic-test-reviewer",
        last_audited_date="2026-10-28")
    assert not record.is_production_verified()


def test_different_documented_frequency_conditions_are_not_duplicate_rules():
    from lv_assist.catalog_validation import validated_rules

    rules = [SelectivityRuleRecord(upstream_series="U", upstream_min_in_a=100,
        downstream_series="D", downstream_max_in_a=100, selectivity_limit_is_ka=36,
        catalog_reference="synthetic", source=evidence(applicability={"frequency_hz": str(frequency)}))
        for frequency in (50, 60)]
    assert len(validated_rules(rules)) == 2


def test_overlapping_reviewed_rules_do_not_choose_the_most_favorable_limit(monkeypatch):
    conditions = {"upstream_part_number": "U", "downstream_part_number": "D",
                  "upstream_manufacturer": "TEST", "downstream_manufacturer": "TEST",
                  "voltage_v": "400", "upstream_setting_a": "200", "downstream_setting_a": "100",
                  "frequency_hz": "50", "ambient_temp_c": "50"}
    rules = [SelectivityRuleRecord(upstream_series=f"different legacy alias {limit}", upstream_min_in_a=100,
        downstream_series="D", downstream_max_in_a=100, selectivity_limit_is_ka=limit,
        catalog_reference="synthetic", upstream_part_number="U", downstream_part_number="D",
        operating_voltage_v=400, upstream_setting_a=200, downstream_setting_a=100,
        source=evidence(value=limit, applicability=conditions)) for limit in (20, 36)]
    monkeypatch.setattr(SiemensSelectivityRepository, "get_selectivity_rules", classmethod(lambda cls: rules))
    upstream = CatalogDevice(part_number="U", manufacturer="TEST", series="U", device_type="MCCB", rated_current_in_a=200)
    downstream = CatalogDevice(part_number="D", manufacturer="TEST", series="D", device_type="MCB", rated_current_in_a=100)
    with pytest.raises(ValueError, match="Ambiguous"):
        SiemensSelectivityRepository.evaluate_pair(upstream, downstream, 25, 400, 200, 100,
                                                   frequency_hz=50, ambient_temp_c=50)
