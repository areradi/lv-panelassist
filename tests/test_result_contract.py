import itertools

import pytest

from lv_assist.catalog import CatalogRepository
from lv_assist.core_verification import CheckResult, aggregate_status
from lv_assist.engine import EngineeringEngine, build_design_verification
from lv_assist.gui import build_demo_project
from lv_assist.models import (
    CatalogDevice,
    DataQuality,
    ValidationResult,
    ValidationStatus,
    VerificationStatus,
)
from lv_assist.result_contract import STATUS_SEVERITY_ORDER, worst_status


@pytest.mark.parametrize("left,right", list(itertools.product(ValidationStatus, repeat=2)))
def test_missing_data_outweighs_warning_in_every_aggregation(left, right):
    expected = max((left, right), key=STATUS_SEVERITY_ORDER.__getitem__)
    assert worst_status([left, right]) == expected
    assert aggregate_status([CheckResult("a", "A", left), CheckResult("b", "B", right)]) == expected


def test_unknown_device_never_defaults_to_verified():
    device = CatalogDevice(part_number="unknown", manufacturer="unknown", series="unknown", device_type="MCB")
    assert device.data_quality == DataQuality.ESTIMATED


def test_legacy_check_without_documented_method_cannot_claim_completed():
    result = ValidationResult(rule_id="legacy", feeder_id="F1", standard_ref="standard name alone",
                              status="COMPLETED", description="calculated", supporting_evidence="number",
                              consequence="unknown", recommended_action="none")
    assert result.status == ValidationStatus.WARNING
    assert result.assumptions and result.recommended_action != "none"


def test_actual_demo_checks_have_auditable_contract_and_no_assembly_pass(tmp_path):
    project, feeders = build_demo_project()
    outputs, summary, checks = EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(project, feeders)
    required = {"check_id", "scope", "subject_id", "status", "input_values", "result_value",
                "unit", "limit", "method", "source_ref", "assumptions", "reason", "recommended_action"}
    assert checks
    for check in checks:
        assert required <= check.model_dump().keys()
        assert check.check_id and check.subject_id and check.reason
    report = build_design_verification(project, outputs, summary, checks)
    assert len(report.items) == 13
    assert report.conclusion_status in (VerificationStatus.NOT_VERIFIED, VerificationStatus.FAIL)
    assert all(item.status != VerificationStatus.PASS for item in report.items)
    assert all(item.source_ref and not item.reviewer and not item.evidence_document for item in report.items)
    from lv_assist.exporters import DesignVerificationExporter
    path = tmp_path / "checklist.html"
    DesignVerificationExporter.generate_html(str(path), project, summary, report, feeders=outputs, validations=checks)
    content = path.read_text(encoding="utf-8")
    assert "badge-insufficient" in content
    assert 'badge badge-verified' not in content
