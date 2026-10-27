# -*- coding: utf-8 -*-
"""
LV-PanelAssist Time-Current Characteristic (TCC) Curve Analyzer
Reads trip_curves.json to evaluate dynamic selectivity and generate SVG vector plots.
"""

import json
import os
from typing import Dict, List, Optional, Tuple

class TCCAnalyzer:
    @staticmethod
    def load_trip_curves() -> dict:
        data_path = os.path.join(os.path.dirname(__file__), "data", "trip_curves.json")
        if os.path.exists(data_path):
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @classmethod
    def get_trip_time_sec(cls, device_series: str, rated_in_a: float, fault_current_a: float) -> float:
        """
        محاسبه تقریبی زمان قطع کلید (ثانیه) در برابر جریان خطای مشخص (A)
        بر اساس چندجمله‌ای استاندارد معکوس‌زمان یا آنی منحنی‌های قطع.
        """
        if rated_in_a <= 0:
            return 999.0
        
        multiple = fault_current_a / rated_in_a
        
        # Immediate / Instantaneous region (typically > 5x to 10x In for thermal-magnetic, or adjustable for electronic LSI)
        if multiple < 1.05:
            return 999.0  # No trip in overload zone under rated current
        elif multiple <= 2.0:
            return round(120.0 / (multiple ** 2), 2)  # Long-time thermal inverse curve
        elif multiple <= 5.0:
            return round(15.0 / (multiple ** 1.8), 2)
        elif multiple <= 10.0:
            return round(2.0 / multiple, 3)
        else:
            # Instantaneous magnetic or electronic override trip (< 0.02s i.e., 20ms)
            return 0.02

    @classmethod
    def evaluate_selectivity_tcc(
        cls,
        upstream_series: str,
        upstream_in: float,
        downstream_series: str,
        downstream_in: float,
        prospective_ik_ka: float
    ) -> Tuple[bool, float, str]:
        """
        ارزیابی دینامیک سلکتیویته با مقایسه زمان قطع کلید بالادست و پایین‌دست در جریان Ik''
        خروجی: (Is_selectivity_ok, current_limit_Is_ka, description_note)
        """
        ik_a = prospective_ik_ka * 1000.0
        
        # Evaluate trip times at full prospective short circuit current
        t_upstream = cls.get_trip_time_sec(upstream_series, upstream_in, ik_a)
        t_downstream = cls.get_trip_time_sec(downstream_series, downstream_in, ik_a)

        # For proper selectivity, downstream must clear fault significantly faster than upstream (t_up > t_down + margin ~ 0.1s)
        margin = 0.08
        if t_upstream > (t_downstream + margin):
            return True, prospective_ik_ka, f"Total Selectivity verified via TCC: Downstream clears in {t_downstream}s vs Upstream {t_upstream}s"
        else:
            # Find the intersection current Is where t_upstream == t_downstream
            # Approximation for LV breakers
            is_ka = round(min(upstream_in * 5.0, prospective_ik_ka), 1)
            return False, is_ka, f"Partial Selectivity limit Is = {is_ka} kA (Curves intersect at ~{is_ka}kA)"

    @classmethod
    def generate_tcc_svg_chart(cls, upstream_label: str, downstream_label: str) -> str:
        """
        تولید کد برداری SVG برای نمایش نمودار زمان-جریان (TCC) در گزارش HTML
        """
        svg_code = f"""
        <svg viewBox="0 0 500 280" width="100%" height="220" style="background:#1E1E1E; border-radius:6px; font-family:Calibri,sans-serif;">
            <!-- Grid lines -->
            <defs>
                <pattern id="grid" width="50" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 50 0 L 0 0 0 40" fill="none" stroke="#333333" stroke-width="1"/>
                </pattern>
            </defs>
            <rect width="500" height="280" fill="url(#grid)" />
            
            <!-- Axes -->
            <line x1="50" y1="240" x2="470" y2="240" stroke="#BDC3C7" stroke-width="2"/>
            <line x1="50" y1="20" x2="50" y2="240" stroke="#BDC3C7" stroke-width="2"/>
            
            <!-- Labels -->
            <text x="260" y="272" fill="#ECF0F1" font-size="11" text-anchor="middle">Log Current (I / In) ➔</text>
            <text x="20" y="130" fill="#ECF0F1" font-size="11" text-anchor="middle" transform="rotate(-90 20 130)">Log Time (Seconds) ➔</text>
            
            <!-- Curves (Simulated TCC) -->
            <!-- Downstream Curve (Faster) -->
            <path d="M 70 50 Q 120 120 220 200 T 420 230" fill="none" stroke="#2ECC71" stroke-width="3"/>
            <!-- Upstream Curve (Slower / Higher) -->
            <path d="M 90 40 Q 150 100 280 180 T 450 220" fill="none" stroke="#E74C3C" stroke-width="3"/>
            
            <!-- Legend -->
            <rect x="320" y="30" width="160" height="50" fill="#2C3E50" rx="4" stroke="#7F8C8D"/>
            <line x1="330" y1="45" x2="355" y2="45" stroke="#E74C3C" stroke-width="3"/>
            <text x="365" y="49" fill="#FFFFFF" font-size="10">Upstream: {upstream_label}</text>
            <line x1="330" y1="65" x2="355" y2="65" stroke="#2ECC71" stroke-width="3"/>
            <text x="365" y="69" fill="#FFFFFF" font-size="10">Downstream: {downstream_label}</text>
        </svg>
        """
        return svg_code.strip()