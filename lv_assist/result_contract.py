"""Shared check status semantics. COMPLETED is scoped to one check only."""

from collections.abc import Iterable
from enum import Enum


class ValidationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    WARNING = "WARNING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"


STATUS_SEVERITY_ORDER = {
    ValidationStatus.COMPLETED: 0,
    ValidationStatus.WARNING: 1,
    ValidationStatus.INSUFFICIENT_DATA: 2,
    ValidationStatus.ERROR: 3,
}

VERIFICATION_STATUS = {
    ValidationStatus.COMPLETED: "PASS",
    ValidationStatus.WARNING: "WARNING",
    ValidationStatus.INSUFFICIENT_DATA: "NOT_VERIFIED",
    ValidationStatus.ERROR: "FAIL",
}


def worst_status(statuses: Iterable[ValidationStatus]) -> ValidationStatus:
    return max(statuses, key=STATUS_SEVERITY_ORDER.__getitem__,
               default=ValidationStatus.INSUFFICIENT_DATA)
