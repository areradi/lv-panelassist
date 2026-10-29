"""Structural trip-curve domain checks, never manufacturer/engineering approval."""

import copy
import math

from lv_assist.i18n import tr
from lv_assist.text_validation import require_exportable_text


def validated_curve(name, curve, error_type=ValueError):
    def invalid(field):
        message = tr('audit_curve_invalid', name='__NAME__', field='__FIELD__')
        raise error_type(message.replace('__NAME__', str(name)).replace('__FIELD__', field))
    try:
        require_exportable_text(name)
        require_exportable_text(curve)
    except ValueError as error:
        raise error_type(str(error)) from error
    if not isinstance(name, str) or not name.strip():
        invalid('curve_id')
    if not isinstance(curve, dict):
        invalid('record')
    def positive(value, field):
        try:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0
        except OverflowError:
            valid = False
        if not valid:
            invalid(field)
        return value
    low = positive(curve.get('im_min_mult'), 'im_min_mult')
    high = positive(curve.get('im_max_mult'), 'im_max_mult')
    if low > high:
        invalid('im_min_mult <= im_max_mult')
    for field in ('thermal_k', 'alpha'):
        if field in curve or 'points' not in curve:
            positive(curve.get(field), field)
    if 'points' in curve:
        points = curve['points']
        if not isinstance(points, (list, tuple)) or len(points) < 2:
            invalid('points')
        previous = 0
        for index, pair in enumerate(points):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                invalid(f'points[{index}]')
            current = float(positive(pair[0], f'points[{index}].current_multiple'))
            positive(pair[1], f'points[{index}].time_s')
            if current <= previous:
                invalid(f'points[{index}].current_multiple (strictly increasing)')
            previous = current
    for field in ('curve_source', 'datasheet_ref', 'ref'):
        if field in curve and (not isinstance(curve[field], str) or not curve[field].strip()):
            invalid(field)
    if curve.get('curve_source') == 'DATASHEET_POINTS' and ('points' not in curve or not curve.get('datasheet_ref')):
        invalid('points/datasheet_ref')
    return copy.deepcopy(curve)


def positive_curve_argument(series, value, field, error_type=ValueError):
    try:
        valid = (isinstance(value, (int, float)) and not isinstance(value, bool)
                 and math.isfinite(value) and value > 0)
    except OverflowError:
        valid = False
    if not valid:
        message = tr('audit_curve_invalid', name='__NAME__', field='__FIELD__')
        raise error_type(message.replace('__NAME__', str(series)).replace('__FIELD__', field))
    return value
