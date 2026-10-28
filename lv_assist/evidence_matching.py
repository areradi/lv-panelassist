"""Exact recorded-evidence matching; no invented numerical tolerances."""

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation


def valid_review_date(value: str | None) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def exact_value(recorded: object, expected: object) -> bool:
    if recorded is None or expected is None or isinstance(recorded, bool) or isinstance(expected, bool):
        return False
    if isinstance(expected, (int, float, Decimal)):
        try:
            actual_number, expected_number = Decimal(str(recorded)), Decimal(str(expected))
        except InvalidOperation:
            return False
        return actual_number.is_finite() and expected_number.is_finite() and actual_number == expected_number
    return isinstance(recorded, str) and isinstance(expected, str) and recorded.strip() == expected.strip()


def exact_applicability(recorded: Mapping[str, str], expected: Mapping[str, object]) -> bool:
    # Extra restrictions (e.g. poles, frequency, temperature ranges) must not be
    # silently ignored merely because the caller has not modelled them.
    return recorded.keys() == expected.keys() and all(exact_value(recorded[key], value)
                                                     for key, value in expected.items())
