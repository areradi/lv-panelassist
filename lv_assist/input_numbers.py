"""Explicit numeric adapters for user input; quantities never accept booleans."""

import math
from decimal import Decimal, InvalidOperation

from lv_assist.i18n import tr


def invalid_input(field):
    raise ValueError(tr('audit_input_invalid') + ' [' + field + ']')


def native_input(value, annotation, field, optional=False):
    if value is None and optional:
        return value
    if annotation is bool:
        if type(value) is not bool:
            invalid_input(field)
    elif annotation is int:
        if type(value) is not int or not -(2**63) <= value <= 2**63 - 1:
            invalid_input(field)
    elif annotation is float:
        try:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            invalid_input(field)
    return value


def spreadsheet_number(value, field, *, integer=False):
    """Text conversion belongs at the spreadsheet boundary, with no truncation."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        invalid_input(field)
    try:
        if integer and isinstance(value, int):
            return native_input(value, int, field)
        if integer and isinstance(value, str):
            exact = Decimal(value.strip())
            if (not exact.is_finite() or not -(2**63) <= exact <= 2**63 - 1
                    or exact != exact.to_integral_value()):
                invalid_input(field)
            return native_input(int(exact), int, field)
        result = float(value)
    except (ValueError, OverflowError, InvalidOperation):
        invalid_input(field)
    if not math.isfinite(result):
        invalid_input(field)
    if integer:
        if not result.is_integer():
            invalid_input(field)
        return native_input(int(result), int, field)
    return result
