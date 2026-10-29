"""Missing curve applicability is unknown; runtime numbers cannot coerce defaults."""

import pytest

from lv_assist.catalog import (
    CatalogRepository,
    SiemensSelectivityRepository,
    TripCurveRepository,
)
from lv_assist.catalog_validation import CatalogValidationError
from lv_assist.engine import EngineeringEngine
from lv_assist.i18n import i18n, tr
from lv_assist.models import (
    CatalogDevice,
    FeederInput,
    LoadType,
    ProjectSpec,
    SelectivityEvalState,
)
from lv_assist.outputs import TccGenerator


@pytest.mark.parametrize('series', ['DEFAULT', 'UNKNOWN'])
@pytest.mark.parametrize('method', ['thermal_time_s', 'instantaneous_band_a'])
@pytest.mark.parametrize('value', [None, True, False, 0, -1, float('nan'), float('inf'), '2'])
def test_invalid_runtime_arguments_are_rejected_without_coercion(series, method, value):
    with pytest.raises(CatalogValidationError):
        getattr(TripCurveRepository, method)(series, value)


def test_unknown_series_never_inherits_default_but_explicit_default_is_available():
    assert TripCurveRepository.get_curve('UNKNOWN') == {}
    assert TripCurveRepository.thermal_time_s('UNKNOWN', 2) is None
    assert TripCurveRepository.instantaneous_band_a('UNKNOWN', 100) == (None, None)
    assert TripCurveRepository.thermal_time_s('DEFAULT', 2) == 22.5
    assert TripCurveRepository.instantaneous_band_a('DEFAULT', 100)[0] > 0


@pytest.mark.parametrize('series', [None, [], '', 'bad\x00series'])
def test_invalid_series_identity_is_a_value_error(series):
    with pytest.raises(ValueError):
        TripCurveRepository.get_curve(series)


@pytest.mark.parametrize('method', ['thermal_time_s', 'instantaneous_band_a'])
def test_arithmetic_overflow_cannot_become_a_clipped_plausible_result(method):
    with pytest.raises(CatalogValidationError):
        getattr(TripCurveRepository, method)('DEFAULT', 1e308)


@pytest.mark.parametrize('missing', ['upstream', 'downstream'])
def test_missing_curve_cannot_supply_selectivity_current(missing):
    up = CatalogDevice(part_number='U', manufacturer='TEST', series='DEFAULT', device_type='MCCB', rated_current_in_a=400)
    down = CatalogDevice(part_number='D', manufacturer='TEST', series='DEFAULT', device_type='MCCB', rated_current_in_a=40)
    (up if missing == 'upstream' else down).series = 'UNKNOWN'
    assert TripCurveRepository.current_selectivity_limit_ka(up, down) is None
    state, limit, _ = SiemensSelectivityRepository.evaluate_pair(up, down, 10)
    assert state == SelectivityEvalState.PRELIMINARY_RATIO_ONLY
    assert limit is None


@pytest.mark.parametrize('locale', ['fa', 'en', 'de'])
def test_engine_and_actual_tcc_export_show_unavailable_curve_without_fabrication(tmp_path, locale):
    previous = i18n.get_language()
    try:
        i18n.set_language(locale)
        devices = CatalogRepository.get_default_catalog()
        for device in devices:
            if device.device_type in ('MCCB', 'MPCB', 'MCB'):
                device.series = 'UNKNOWN'
        project = ProjectSpec(project_name='Unknown protective curve', prospective_ik_ka=10)
        inputs = [FeederInput(feeder_id='F1', description='Test', load_type=LoadType.SUB_FEEDER, power_kw=1)]
        outputs, summary, checks = EngineeringEngine(devices).process_project(project, inputs)
        assert outputs[0].selected_protection is not None
        assert outputs[0].trip_time_estimate.time_s is None
        path = tmp_path / 'tcc.svg'
        TccGenerator.generate_svg_file(str(path), project, outputs, summary, validations=checks)
        svg = path.read_text()
        assert tr('tcc_curve_missing') in svg
        assert '<polyline' not in svg
        assert 'PRELIMINARY' in svg
    finally:
        i18n.set_language(previous)
