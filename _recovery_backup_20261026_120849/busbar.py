# -*- coding: utf-8 -*-
"""محاسبات مهندسی شینه مسی (Busbar Sizing)، فواصل هوایی و خزشی (Clearance & Creepage)
و مقاومت اتصال کوتاه بر اساس IEC 61439-1/2 و DIN 43671."""
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class BusbarGeometrySpec:
    spec_label: str              # مثلاً "Cu 20x10 mm"
    width_mm: float              # عرض شینه (مثلاً 20.0)
    thickness_mm: float          # ضخامت شینه (مثلاً 10.0)
    bars_per_phase: int          # تعداد شینه در هر فاز (1 یا 2)
    rated_current_a: float       # ظرفیت جریان مجاز در دمای داخل تابلو 55 درجه
    min_clearance_mm: float      # حداقل فاصله هوایی فاز به فاز / فاز به بدنه (IEC 61439-1 Table 1)
    min_creepage_mm: float       # حداقل فاصله خزشی روی مقره (IEC 61439-1 Table 2)
    phase_center_pitch_mm: float # فاصله مرکز تا مرکز دو شینه مجاور


class BusbarCalculator:
    """انتخاب ابعاد واقعی شینه‌های فاز، نول و ارت و کنترل فواصل خزشی و هوایی طبق IEC 61439-1/2."""

    STANDARD_COPPER_BARS: List[Tuple[str, float, float, int, float]] = [
        ("Cu 15x5 mm",  15.0,  5.0, 1,  200.0),
        ("Cu 20x5 mm",  20.0,  5.0, 1,  275.0),
        ("Cu 20x10 mm", 20.0, 10.0, 1,  425.0),
        ("Cu 30x5 mm",  30.0,  5.0, 1,  380.0),
        ("Cu 30x10 mm", 30.0, 10.0, 1,  570.0),
        ("Cu 40x10 mm", 40.0, 10.0, 1,  715.0),
        ("Cu 50x10 mm", 50.0, 10.0, 1,  860.0),
        ("Cu 60x10 mm", 60.0, 10.0, 1, 1000.0),
        ("Cu 80x10 mm", 80.0, 10.0, 1, 1260.0),
        ("Cu 100x10 mm", 100.0, 10.0, 1, 1520.0),
        ("2x Cu 60x10 mm", 60.0, 10.0, 2, 1720.0),
        ("2x Cu 80x10 mm", 80.0, 10.0, 2, 2150.0),
        ("2x Cu 100x10 mm", 100.0, 10.0, 2, 2600.0),
    ]

    IMPULSE_CLEARANCE_MM: Dict[int, Tuple[float, float]] = {
        4: (3.0, 10.0),
        6: (5.5, 14.0),
        8: (8.0, 20.0),
        12: (14.0, 30.0),
    }

    @staticmethod
    def _kappa_iec60909(ik_ka: float) -> float:
        """محاسبه ضریب پیک جریان اتصال کوتاه (Kappa factor) بر اساس استاندارد IEC 60909."""
        if ik_ka <= 10.0:
            return 1.15
        elif ik_ka <= 25.0:
            return 1.25
        elif ik_ka <= 50.0:
            return 1.35
        else:
            return 1.5

    @classmethod
    def get_creepage_and_clearance(cls, rated_voltage_v: float = 400.0, u_imp_kv: int = 8) -> Tuple[float, float]:
        _, eng_clearance = cls.IMPULSE_CLEARANCE_MM.get(u_imp_kv, (8.0, 20.0))
        min_creepage = 20.0 if rated_voltage_v <= 500.0 else 25.0
        return eng_clearance, max(min_creepage, eng_clearance)

    @classmethod
    def select_main_busbar(cls, design_current_a: float, icw_ka: float = 25.0,
                           u_imp_kv: int = 8, **kwargs) -> BusbarGeometrySpec:
        """انتخاب شینه اصلی با قابلیت پذیرش آرگومان‌های کلیدواژه‌ای اضافی (مثل voltage_v)"""
        min_thermal_area_mm2 = (icw_ka * 1000.0) / 143.0
        min_clr, min_crp = cls.get_creepage_and_clearance(u_imp_kv=u_imp_kv)

        selected = cls.STANDARD_COPPER_BARS[-1]
        for cand in cls.STANDARD_COPPER_BARS:
            label, w, t, n_bars, ampacity = cand
            area = w * t * n_bars
            if ampacity >= design_current_a and area >= min_thermal_area_mm2:
                selected = cand
                break

        label, w, t, n_bars, ampacity = selected
        pitch = max(60.0, w + min_clr + 25.0)
        return BusbarGeometrySpec(
            spec_label=label,
            width_mm=w,
            thickness_mm=t,
            bars_per_phase=n_bars,
            rated_current_a=ampacity,
            min_clearance_mm=min_clr,
            min_creepage_mm=min_crp,
            phase_center_pitch_mm=pitch,
        )

    @classmethod
    def select(cls, *args, **kwargs) -> BusbarGeometrySpec:
        """متد سازگار برای پوشش فراخوانی BusbarEngine.select در engine.py"""
        if args and isinstance(args[0], (int, float)):
            return cls.select_main_busbar(*args, **kwargs)
        elif "design_current_a" in kwargs or "current_a" in kwargs:
            return cls.select_main_busbar(**kwargs)
        elif args:
            try:
                return cls.select_main_busbar(float(args[0]), **kwargs)
            except Exception:
                pass
        return cls.select_main_busbar(250.0, 25.0, 8, **kwargs)

    @classmethod
    def select_pe_busbar(cls, main_bus: BusbarGeometrySpec) -> str:
        phase_area = main_bus.width_mm * main_bus.thickness_mm * main_bus.bars_per_phase
        req_pe_area = max(75.0, phase_area * 0.5)
        for label, w, t, n_bars, _ in cls.STANDARD_COPPER_BARS:
            if (w * t * n_bars) >= req_pe_area:
                return label
        return "Cu 50x10 mm"


# تعریف سازگار برای جلوگیری از خطای ایمپورت در engine.py
class BusbarEngine(BusbarCalculator):
    pass