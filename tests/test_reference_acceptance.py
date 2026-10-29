"""Synthetic contract tests for reference ingestion, not independent reference data."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from lv_assist.reference_acceptance import CASE_IDS, evaluate_pack

ROOT = Path(__file__).resolve().parents[1]


def pending():
    return {'schema_version': 1, 'cases': [
        {'case_id': name, 'state': 'AWAITING_INDEPENDENT_REFERENCE'} for name in CASE_IDS]}


def supplied():
    document = pending()
    # A deliberately synthetic unknown-PE policy fixture, never an independent calculation.
    document['cases'][0] = {
        'case_id': 'dol_15kw', 'state': 'PROVIDED', 'source_document': 'SYNTHETIC TEST ONLY',
        'source_revision': 'test-1', 'page_or_table': 'test table',
        'independent_method': 'Synthetic parser test, no engineering claim',
        'reviewer': 'Synthetic test fixture', 'reviewed_at': '2026-01-01',
        'project': {'project_name': 'Synthetic parser test'},
        'feeders': [{'feeder_id': 'F1', 'description': 'Motor', 'load_type': 'MOTOR_DOL', 'power_kw': 15}],
        'expected': [{'feeder_id': 'F1', 'quantity': 'selected_pe_mm2', 'unit': 'mm2', 'value': None,
                      'absolute_tolerance': 0, 'relative_tolerance': 0,
                      'tolerance_rationale': 'Synthetic missing-data equality; no numerical tolerance claim'}]}
    return document


def test_default_cli_reports_ten_missing_references_and_nonzero_blocked_exit():
    path = ROOT / 'tests/reference_cases/pending.json'
    before = path.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_reference_acceptance.py')],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report['status'] == 'BLOCKED' and len(report['runs']) == 10
    assert report['engineering_verification'] == 'NOT_VERIFIED'
    assert path.read_bytes() == before


def test_matching_and_mismatching_expectations_do_not_authenticate_evidence():
    document = supplied()
    before = copy.deepcopy(document)
    result = evaluate_pack(document)
    assert document == before
    assert result['status'] == 'BLOCKED' and result['runs'][0]['status'] == 'MATCH'
    assert result['evidence_authentication'] == 'NOT_PERFORMED'
    document['cases'][0]['expected'][0]['value'] = 16
    result = evaluate_pack(document)
    assert result['status'] == 'DIFFERENCE'
    difference = result['runs'][0]['differences'][0]
    assert difference['expected'] == 16 and difference['actual'] is None


@pytest.mark.parametrize('change', ['duplicate', 'missing', 'blank_source', 'bad_date', 'unit',
                                  'bool_tolerance', 'negative_tolerance', 'infinite', 'blank_rationale',
                                  'unknown_quantity', 'duplicate_metric', 'pending_numbers'])
def test_invalid_or_incomplete_reference_claims_fail_closed(change):
    document = supplied()
    case = document['cases'][0]
    metric = case['expected'][0]
    if change == 'duplicate':
        document['cases'].append(copy.deepcopy(case))
    elif change == 'missing':
        document['cases'].pop()
    elif change == 'blank_source':
        case['source_document'] = ' '
    elif change == 'bad_date':
        case['reviewed_at'] = 'invalid'
    elif change == 'unit':
        metric['unit'] = 'A'
    elif change == 'bool_tolerance':
        metric['absolute_tolerance'] = True
    elif change == 'negative_tolerance':
        metric['relative_tolerance'] = -1
    elif change == 'infinite':
        metric['value'] = float('inf')
    elif change == 'blank_rationale':
        metric['tolerance_rationale'] = ''
    elif change == 'unknown_quantity':
        metric['quantity'] = '__dict__'
    elif change == 'duplicate_metric':
        case['expected'].append(copy.deepcopy(metric))
    else:
        document['cases'][1]['expected'] = 100
    with pytest.raises(ValueError):
        evaluate_pack(document)
