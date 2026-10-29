"""Compare externally supplied reference claims; never authenticate or certify them."""

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt, field_validator

from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.evidence_matching import valid_review_date
from lv_assist.models import FeederInput, ProjectSpec
from lv_assist.text_validation import require_exportable_text

CASE_IDS = ('dol_15kw', 'vfd_37kw', 'distribution', 'lighting_1p', 'tt_rcd',
            'feeder_200m', 'missing_ik', 'motor_contribution', 'mccb_derating', 'ip_assembly')
QUANTITIES = {
    'design_current_ib_a': 'A', 'selected_phase_mm2': 'mm2',
    'selected_pe_mm2': 'mm2', 'voltage_drop_percent': '%',
    'cable_derated_iz_a': 'A', 'protection_icu_ka': 'kA',
    'ik_feeder_end_max_3p_ka': 'kA', 'ik_feeder_end_min_1p_ka': 'kA',
}


class ReferenceMetric(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    feeder_id: str
    quantity: str
    unit: str
    value: StrictFloat | StrictInt | None
    absolute_tolerance: StrictFloat | StrictInt
    relative_tolerance: StrictFloat | StrictInt
    tolerance_rationale: str

    @field_validator('value', 'absolute_tolerance', 'relative_tolerance')
    @classmethod
    def finite_number(cls, value, info):
        if value is None and info.field_name == 'value':
            return value
        try:
            valid = math.isfinite(value) and (info.field_name == 'value' or value >= 0)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('Reference values/tolerances must be finite; tolerances nonnegative')
        return value


class ReferenceCase(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    case_id: str
    state: Literal['PROVIDED']
    source_document: str
    source_revision: str
    page_or_table: str
    independent_method: str
    reviewer: str
    reviewed_at: str
    project: ProjectSpec
    feeders: list[FeederInput]
    expected: list[ReferenceMetric]

    @field_validator('*', mode='before')
    @classmethod
    def nonblank_text(cls, value):
        require_exportable_text(value)
        if isinstance(value, str) and not value.strip():
            raise ValueError('Reference metadata cannot be blank')
        return value


def evaluate_pack(document):
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'cases'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1
            or not isinstance(document['cases'], list)):
        raise ValueError('Invalid reference pack schema')
    identifiers = [case.get('case_id') for case in document['cases'] if isinstance(case, dict)]
    if len(identifiers) != len(document['cases']) or set(identifiers) != set(CASE_IDS) or len(identifiers) != len(set(identifiers)):
        raise ValueError('All ten unique requested case IDs are required')
    runs = []
    for raw in document['cases']:
        if raw.get('state') == 'AWAITING_INDEPENDENT_REFERENCE':
            if set(raw) != {'case_id', 'state'}:
                raise ValueError('Pending cases cannot carry unreviewed numerical expectations')
            runs.append({'case_id': raw['case_id'], 'status': 'BLOCKED', 'reason': 'Independent evidence not supplied'})
            continue
        case = ReferenceCase.model_validate(raw)
        if not valid_review_date(case.reviewed_at) or not case.expected or not case.feeders:
            raise ValueError('A dated review, nonempty inputs and explicit expectations are required')
        identities = [(metric.feeder_id, metric.quantity) for metric in case.expected]
        if len(identities) != len(set(identities)):
            raise ValueError('Duplicate reference metric')
        outputs, _, _ = EngineeringEngine(CatalogRepository.get_default_catalog()).process_project(case.project, case.feeders)
        by_id = {row.feeder_id: row for row in outputs}
        differences = []
        for metric in case.expected:
            if (metric.feeder_id not in by_id or QUANTITIES.get(metric.quantity) != metric.unit
                    or not metric.tolerance_rationale.strip()):
                raise ValueError('Invalid reference subject, quantity/unit or tolerance rationale')
            row = by_id[metric.feeder_id]
            obj = row.short_circuit_profile if metric.quantity.startswith('ik_') else row
            actual = getattr(obj, metric.quantity)
            matches = actual is None if metric.value is None else (
                actual is not None and math.isclose(actual, metric.value,
                    rel_tol=metric.relative_tolerance, abs_tol=metric.absolute_tolerance))
            if not matches:
                differences.append({'feeder_id': metric.feeder_id, 'quantity': metric.quantity,
                                    'expected': metric.value, 'actual': actual, 'unit': metric.unit})
        runs.append({'case_id': case.case_id, 'status': 'MATCH' if not differences else 'DIFFERENCE',
                     'differences': differences})
    status = ('DIFFERENCE' if any(row['status'] == 'DIFFERENCE' for row in runs) else
              'BLOCKED' if any(row['status'] == 'BLOCKED' for row in runs) else 'MATCH')
    return {'status': status, 'engineering_verification': 'NOT_VERIFIED',
            'evidence_authentication': 'NOT_PERFORMED', 'runs': runs}
