from dataclasses import dataclass, field
from typing import List, Optional, Callable, Tuple
import math


from lv_assist.result_contract import ValidationStatus, worst_status


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: ValidationStatus
    measured_or_calc_value: Optional[str] = None
    limit_or_reference: Optional[str] = None
    cause: str = ""
    effect: str = ""
    recommended_action: str = ""
    scope: str = "CHECK"
    subject_id: str = ""
    input_values: dict = field(default_factory=dict)
    result_value: float | None = None
    unit: str | None = None
    limit: float | None = None
    method: str = "UNSPECIFIED"
    source_ref: str | None = None
    assumptions: list[str] = field(default_factory=list)

    @property
    def reason(self) -> str:
        return self.cause or self.effect or self.title


def aggregate_status(results: List[CheckResult]) -> ValidationStatus:
    return worst_status(r.status for r in results)


@dataclass
class TripTimeEstimate:
    time_s: Optional[float]
    is_curve_estimated: bool
    exceeds_adiabatic_5s_limit: bool
    status: ValidationStatus
    note: str


def estimate_clear_time_s(
    series: str,
    fault_multiple: Optional[float],
    thermal_curve_lookup: Callable[[str, float], Optional[float]],
    is_approximated_curve: bool = True,
) -> TripTimeEstimate:
    if fault_multiple is None or not math.isfinite(fault_multiple) or fault_multiple <= 0:
        return TripTimeEstimate(
            time_s=None,
            is_curve_estimated=is_approximated_curve,
            exceeds_adiabatic_5s_limit=False,
            status=ValidationStatus.INSUFFICIENT_DATA,
            note="ضریب جریان خطا نامشخص یا نامعتبر است."
        )

    raw_time_s = thermal_curve_lookup(series, fault_multiple)
    if raw_time_s is None or not math.isfinite(raw_time_s) or raw_time_s <= 0:
        return TripTimeEstimate(
            time_s=None,
            is_curve_estimated=is_approximated_curve,
            exceeds_adiabatic_5s_limit=False,
            status=ValidationStatus.INSUFFICIENT_DATA,
            note=f"برای سری حفاظتی '{series}' زمان قطع از منحنی استخراج نشد."
        )

    if raw_time_s > 5.0:
        return TripTimeEstimate(
            time_s=raw_time_s,
            is_curve_estimated=is_approximated_curve,
            exceeds_adiabatic_5s_limit=True,
            status=ValidationStatus.ERROR,
            note=(
                f"زمان قطع استخراج‌شده ({raw_time_s:.2f} s) بیشتر از حد مجاز 5.0 s "
                "برای فرمول آدیاباتیک (IEC 60364-5-54) است."
            )
        )

    status = ValidationStatus.WARNING if is_approximated_curve else ValidationStatus.COMPLETED
    note = (
        "زمان قطع از مدل منحنی تخمینی استخراج شده است."
        if is_approximated_curve
        else "زمان قطع از منحنی تأییدشده سازنده استخراج شد."
    )
    return TripTimeEstimate(
        time_s=raw_time_s,
        is_curve_estimated=is_approximated_curve,
        exceeds_adiabatic_5s_limit=False,
        status=status,
        note=note
    )


def calculate_adiabatic_pe_mm2(
    fault_current_a: Optional[float],
    trip_estimate: TripTimeEstimate,
    k_factor: float = 143.0,
) -> Tuple[Optional[float], CheckResult]:
    if (fault_current_a is None or not math.isfinite(fault_current_a)
            or fault_current_a <= 0 or trip_estimate.time_s is None):
        return None, CheckResult(
            check_id="PE_ADIABATIC_SIZING",
            title="سایزینگ آدیاباتیک هادی حفاظتی (PE)",
            status=ValidationStatus.INSUFFICIENT_DATA,
            cause="جریان خطای انتهای مسیر یا زمان قطع حفاظت نامشخص است.",
            effect="امکان اثبات استقامت حرارتی هادی PE وجود ندارد.",
            recommended_action="طول کابل، امپدانس منبع و مشخصات منحنی کلید را تکمیل کنید."
        )

    if (not math.isfinite(k_factor) or k_factor <= 0
            or not math.isfinite(trip_estimate.time_s) or trip_estimate.time_s <= 0):
        return None, CheckResult(
            check_id="PE_ADIABATIC_SIZING", title="PE", status=ValidationStatus.ERROR,
            cause="Invalid time or k factor; finite positive values are required.",
            recommended_action="Provide documented conductor and protection parameters.")

    if trip_estimate.exceeds_adiabatic_5s_limit or trip_estimate.time_s > 5.0:
        return None, CheckResult(
            check_id="PE_ADIABATIC_SIZING",
            title="سایزینگ آدیاباتیک هادی حفاظتی (PE)",
            status=ValidationStatus.ERROR,
            measured_or_calc_value=f"t = {trip_estimate.time_s:.2f} s",
            limit_or_reference="t <= 5.0 s (IEC 60364-5-54 Clause 543.1.2)",
            cause=trip_estimate.note,
            effect="فرمول آدیاباتیک در زمان‌های بالای ۵ ثانیه غیرمعتبر است.",
            recommended_action="تنظیمات کلید را کاهش دهید یا سایز کابل را افزایش دهید."
        )

    s_min_mm2 = (fault_current_a * math.sqrt(trip_estimate.time_s)) / k_factor
    return round(s_min_mm2, 2), CheckResult(
        check_id="PE_ADIABATIC_SIZING",
        title="سایزینگ آدیاباتیک هادی حفاظتی (PE)",
        status=trip_estimate.status,
        measured_or_calc_value=f"S_min = {s_min_mm2:.2f} mm²",
        limit_or_reference=f"k = {k_factor} (IEC 60364-5-54)",
        cause=trip_estimate.note if trip_estimate.is_curve_estimated else "",
        effect="حداقل سطح مقطع حرارتی PE محاسبه شد.",
        recommended_action="در صورت تخمینی بودن منحنی، زمان قطع را با دیتاشیت کلید کنترل کنید.",
        input_values={"fault_current_a": fault_current_a, "time_s": trip_estimate.time_s,
                        "k_factor": k_factor}, result_value=round(s_min_mm2, 2), unit="mm²",
        method="I*sqrt(t)/k", source_ref="IEC 60364-5-54; applicability requires review",
        assumptions=[trip_estimate.note, "k factor applicability must be documented"]
    )


@dataclass
class ShortCircuitProfile:
    ik_transformer_3p_ka: Optional[float]
    ik_main_busbar_3p_ka: Optional[float]
    ik_feeder_start_3p_ka: Optional[float]
    ik_feeder_end_max_3p_ka: Optional[float]
    ik_feeder_end_min_1p_ka: Optional[float]
    is_attenuated_by_feeder_cable: bool
    scope_status: ValidationStatus
    scope_warning_note: str


def calculate_network_ik_profile(
    transformer_kva: Optional[float],
    uk_percent: Optional[float],
    line_voltage_v: float = 400.0,
    incomer_cable_length_m: Optional[float] = None,
    incomer_cable_mm2: Optional[float] = None,
    feeder_cable_length_m: Optional[float] = None,
    feeder_phase_mm2: Optional[float] = None,
    feeder_pe_mm2: Optional[float] = None,
    voltage_factor_c_max: float = 1.05,
    voltage_factor_c_min: float = 0.95,
) -> ShortCircuitProfile:
    if not transformer_kva or not uk_percent or transformer_kva <= 0 or uk_percent <= 0:
        return ShortCircuitProfile(
            ik_transformer_3p_ka=None,
            ik_main_busbar_3p_ka=None,
            ik_feeder_start_3p_ka=None,
            ik_feeder_end_max_3p_ka=None,
            ik_feeder_end_min_1p_ka=None,
            is_attenuated_by_feeder_cable=False,
            scope_status=ValidationStatus.INSUFFICIENT_DATA,
            scope_warning_note="مشخصات ترانسفورماتور وارد نشده است."
        )

    z_tr_ohm = (uk_percent / 100.0) * ((line_voltage_v ** 2) / (transformer_kva * 1000.0))
    r_tr_ohm = 0.3 * z_tr_ohm
    x_tr_ohm = math.sqrt(max(0.0, z_tr_ohm ** 2 - r_tr_ohm ** 2))

    u_phase_v = line_voltage_v / math.sqrt(3.0)
    ik_tr_ka = (voltage_factor_c_max * u_phase_v) / (z_tr_ohm * 1000.0)

    r_bus = r_tr_ohm
    x_bus = x_tr_ohm
    rho_cu_20 = 0.018
    x_per_m = 0.00008

    if incomer_cable_length_m and incomer_cable_mm2 and incomer_cable_length_m > 0 and incomer_cable_mm2 > 0:
        r_bus += rho_cu_20 * (incomer_cable_length_m / incomer_cable_mm2)
        x_bus += x_per_m * incomer_cable_length_m

    z_bus_ohm = math.hypot(r_bus, x_bus)
    ik_bus_ka = (voltage_factor_c_max * u_phase_v) / (z_bus_ohm * 1000.0)

    if not feeder_cable_length_m or not feeder_phase_mm2 or feeder_cable_length_m <= 0 or feeder_phase_mm2 <= 0:
        return ShortCircuitProfile(
            ik_transformer_3p_ka=round(ik_tr_ka, 3),
            ik_main_busbar_3p_ka=round(ik_bus_ka, 3),
            ik_feeder_start_3p_ka=round(ik_bus_ka, 3),
            ik_feeder_end_max_3p_ka=None,
            ik_feeder_end_min_1p_ka=None,
            is_attenuated_by_feeder_cable=False,
            scope_status=ValidationStatus.WARNING,
            scope_warning_note="طول یا سطح مقطع کابل فیدر مشخص نیست."
        )

    r_feeder_max = r_bus + rho_cu_20 * (feeder_cable_length_m / feeder_phase_mm2)
    x_feeder_max = x_bus + x_per_m * feeder_cable_length_m
    z_feeder_max = math.hypot(r_feeder_max, x_feeder_max)
    ik_end_max_3p_ka = (voltage_factor_c_max * u_phase_v) / (z_feeder_max * 1000.0)

    pe_s = feeder_pe_mm2 if (feeder_pe_mm2 and feeder_pe_mm2 > 0) else feeder_phase_mm2
    rho_hot = rho_cu_20 * 1.5
    r_loop_min = (2.0 * r_bus) + rho_hot * feeder_cable_length_m * ((1.0 / feeder_phase_mm2) + (1.0 / pe_s))
    x_loop_min = (2.0 * x_bus) + (2.0 * x_per_m * feeder_cable_length_m)
    z_loop_min = math.hypot(r_loop_min, x_loop_min)
    ik_end_min_1p_ka = (voltage_factor_c_min * u_phase_v) / (z_loop_min * 1000.0)

    return ShortCircuitProfile(
        ik_transformer_3p_ka=round(ik_tr_ka, 3),
        ik_main_busbar_3p_ka=round(ik_bus_ka, 3),
        ik_feeder_start_3p_ka=round(ik_bus_ka, 3),
        ik_feeder_end_max_3p_ka=round(ik_end_max_3p_ka, 3),
        ik_feeder_end_min_1p_ka=round(ik_end_min_1p_ka, 3),
        is_attenuated_by_feeder_cable=True,
        scope_status=ValidationStatus.WARNING,
        scope_warning_note="PRELIMINARY: assumed source R/X, Cu temperature and loop return; not independently verified."
    )


def verify_breaking_capacity_icu(
    device_icu_ka: Optional[float],
    prospective_ik_ka: Optional[float],
    is_ik_preliminary: bool = False,
) -> CheckResult:
    if (prospective_ik_ka is None or device_icu_ka is None
            or not math.isfinite(prospective_ik_ka) or not math.isfinite(device_icu_ka)
            or prospective_ik_ka <= 0 or device_icu_ka <= 0):
        return CheckResult(
            check_id="BREAKING_CAPACITY_ICU",
            title="بررسی قدرت قطع کلید حفاظتی (Icu >= Ik)",
            status=ValidationStatus.INSUFFICIENT_DATA,
            measured_or_calc_value=f"Icu = {device_icu_ka} kA, Ik = {prospective_ik_ka} kA",
            limit_or_reference="IEC 60947-2 / IEC 61439-1 Clause 10.11",
            cause="مقدار جریان اتصال کوتاه (Ik) یا قدرت قطع کلید (Icu) ناموجود است.",
            effect="امکان تأیید استقامت کلید در برابر اتصال کوتاه وجود ندارد.",
            recommended_action="مشخصات ترانسفورماتور و قدرت قطع کلید را وارد کنید."
        )

    if device_icu_ka < prospective_ik_ka:
        return CheckResult(
            check_id="BREAKING_CAPACITY_ICU",
            title="بررسی قدرت قطع کلید حفاظتی (Icu >= Ik)",
            status=ValidationStatus.ERROR,
            measured_or_calc_value=f"Icu = {device_icu_ka:.1f} kA < Ik = {prospective_ik_ka:.2f} kA",
            limit_or_reference="Icu >= Ik",
            cause="قدرت قطع نامی کلید کمتر از جریان اتصال کوتاه محل نصب است.",
            effect="خطر تخریب کلید حفاظتی در زمان بروز اتصال کوتاه.",
            recommended_action="کلیدی با قدرت قطع بالاتر انتخاب کنید."
        )

    status = ValidationStatus.WARNING if is_ik_preliminary else ValidationStatus.COMPLETED
    return CheckResult(
        check_id="BREAKING_CAPACITY_ICU",
        title="بررسی قدرت قطع کلید حفاظتی (Icu >= Ik)",
        status=status,
        measured_or_calc_value=f"Icu = {device_icu_ka:.1f} kA >= Ik = {prospective_ik_ka:.2f} kA",
        limit_or_reference="Icu >= Ik",
        effect="قدرت قطع کلید بالاتر از جریان اتصال کوتاه محاسبه شده است."
    )


def verify_overload_coordination(ib_a: float, ir_a: float | None, iz_a: float | None,
                                 i2_a: float | None) -> CheckResult:
    """Check the requested inequalities only, without inventing device settings."""
    values = {"ib_a": ib_a, "ir_a": ir_a, "iz_a": iz_a, "i2_a": i2_a}
    present = [value for value in values.values() if value is not None]
    invalid = any(not math.isfinite(value) or value <= 0 for value in present)
    violated = ((ir_a is not None and ir_a < ib_a)
                or (ir_a is not None and iz_a is not None and ir_a > iz_a)
                or (i2_a is not None and iz_a is not None and i2_a > 1.45 * iz_a))
    status = (ValidationStatus.ERROR if invalid or violated else
              ValidationStatus.INSUFFICIENT_DATA if None in (ir_a, iz_a, i2_a) else
              ValidationStatus.WARNING)
    return CheckResult(
        check_id="OVERLOAD_COORDINATION", title="Ib <= Ir <= Iz; I2 <= 1.45 Iz",
        status=status, input_values=values, unit="A", result_value=ir_a, limit=iz_a,
        method="Ib <= Ir <= Iz AND I2 <= 1.45 Iz",
        source_ref="IEC 60364-4-43; device-specific applicability requires review",
        cause="Actual settings/ampacity/I2 required; inequalities alone do not verify equipment.",
        recommended_action="Obtain documented protection settings, I2 and applicable cable data.",
        assumptions=["No manufacturer setting/standard applicability sign-off recorded"],
    )
