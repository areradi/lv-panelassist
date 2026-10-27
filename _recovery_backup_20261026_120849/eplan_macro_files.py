# -*- coding: utf-8 -*-
"""تولید فایل‌های ماکروی استاندارد EPLAN P8 (.ema, .emp, .ems) با ساختار چندسیمه (Multi-line)،
هم‌راستایی شبکه 4.0mm برای حذف خطوط مورب، ارجاعات متقابل (Cross-References) و ساختار IEC 81346."""
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as _xml_esc

from lv_assist.models import ProjectSpec, FeederCalcOutput, PanelSummaryOutput, LoadType


VALID_MACRO_EXTENSIONS = (".ema", ".emp", ".ems")
EPLAN_GRID_MM = 4.0


def snap_grid(val: float, grid: float = EPLAN_GRID_MM) -> float:
    """قفل کردن مختصات روی شبکه استاندارد 4.0 میلی‌متری EPLAN برای اتصال خودکار (Autoconnecting)."""
    return round(float(val) / grid) * grid


def _safe_id(val: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", str(val or "")).strip("_") or "LV"


def _pn(dev) -> str:
    return str(dev.part_number) if dev is not None and getattr(dev, "part_number", None) else ""


class EplanMacroFileGenerator:
    """تولیدکننده فایل‌های ماکروی پنجره‌ای (.ema)، صفحه‌ای (.emp) و سیمبلی (.ems) برای EPLAN Electric P8."""

    MACRO_DIR_VAR = "$(MD_MACROS)"
    SYMBOL_LIB_MULTILINE = "IEC_symbol"
    SYMBOL_LIB_SINGLELINE = "IEC_single_symbol"

    @classmethod
    def resolve_macro_filepath(cls, base_dir: str, filename: str, macro_type: str = "ema") -> str:
        """تضمین ذخیره فایل ماکرو با پسوند معتبر (.ema, .emp, .ems) و ساختار پوشه استاندارد."""
        ext = "." + macro_type.lower().lstrip(".")
        if ext not in VALID_MACRO_EXTENSIONS:
            ext = ".ema"
        root, current_ext = os.path.splitext(filename)
        if current_ext.lower() in VALID_MACRO_EXTENSIONS:
            final_name = filename
        else:
            final_name = root + ext
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, final_name)

    @classmethod
    def build_hierarchical_tag(cls, project: ProjectSpec, short_tag: str, on_door: bool = False) -> Tuple[str, str, str, str]:
        """
        ساخت تگ منطبق با ساختار سلسله‌مراتبی پروژه (IEC 81346):
        بازگشت: (full_tag, higher_level_func, mounting_loc, device_tag)
        مثال: ('=MCC1+MP1-Q1', 'MCC1', 'MP1', '-Q1')
        """
        hlf = _safe_id(project.project_name)
        base_loc = _safe_id(project.panel_tag)
        loc = f"{base_loc}_DR1" if on_door else f"{base_loc}_MP1"
        dt = short_tag if short_tag.startswith("-") else f"-{short_tag}"
        full_tag = f"={hlf}+{loc}{dt}"
        return full_tag, hlf, loc, dt

    @classmethod
    def _collect_multiline_elements(
        cls, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput
    ) -> List[Dict[str, object]]:
        """
        ایجاد لیست المان‌های چندسیمه (Multi-line)، نقاط اتصال (Connection Points)،
        گره‌های مسیریابی (T_NODE / ANGLE) و Bundle Connection Points.
        """
        elements: List[Dict[str, object]] = []

        def add_elem(page: str, tag: str, sym: str, representation: str, x: float, y: float,
                     part_no: str = "", func_text: str = "", is_main: bool = True,
                     on_door: bool = False, pins: str = "1,3,5/2,4,6") -> None:
            full_tag, hlf, loc, dt = cls.build_hierarchical_tag(project, tag, on_door=on_door)
            elements.append({
                "page": page,
                "full_tag": full_tag,
                "hlf": hlf,
                "loc": loc,
                "dt": dt,
                "symbol": sym,
                "representation": representation,  # "MultiLine" یا "SingleLine"
                "library": cls.SYMBOL_LIB_MULTILINE if representation == "MultiLine" else cls.SYMBOL_LIB_SINGLELINE,
                "x": snap_grid(x),
                "y": snap_grid(y),
                "part_no": part_no,
                "func_text": func_text,
                "is_main": is_main,
                "cross_ref_enabled": True,
                "pins": pins,
            })

        # ۱. بخش قدرت چندسیمه (Multi-line Power Circuit) - کلید اصلی و فیدرها
        incomer_x, incomer_y = 64.0, 240.0
        add_elem("001", "-Q0", "QL3", "MultiLine", incomer_x, incomer_y,
                 part_no=_pn(summary.main_breaker), func_text="Main Incomer 3P", is_main=True)
        # نقطه انتقال Bundle Connection Point برای ارتباط تک‌سیم/چندسیمه و شینه
        add_elem("001", "-BCP0", "BUNDLE_CP", "MultiLine", incomer_x, 208.0,
                 func_text="3P+N+PE Busbar Bundle", is_main=False, pins="L1,L2,L3,N,PE")

        for idx, f in enumerate(feeders, start=1):
            fx = snap_grid(64.0 + (idx - 1) * 56.0)
            p_page = "002"
            # گره انشعاب سه راهی روی شینه افقی (جلوگیری از خط مورب بین فیدرها)
            add_elem(p_page, f"-T_BUS_{idx}", "T_NODE_3P", "MultiLine", fx, 248.0,
                     func_text="Busbar Tap 3P", is_main=False, pins="1,2,3")
            # کلید حفاظت فیدر (چندسیمه ۳ پل)
            add_elem(p_page, f"-Q{idx}", "QL3", "MultiLine", fx, 216.0,
                     part_no=_pn(f.selected_protection), func_text=f"Feeder {f.feeder_id} Protection", is_main=True)

            if f.load_type == LoadType.MOTOR_DOL:
                add_elem(p_page, f"-K{idx}", "K_3P", "MultiLine", fx, 176.0,
                         part_no=_pn(f.selected_contactor_main), func_text="Main Contactor 3P", is_main=False)
                add_elem(p_page, f"-X{idx}", "X_4P", "MultiLine", fx, 136.0,
                         func_text="Motor Terminal Strip", is_main=True, pins="U1,V1,W1,PE")
                add_elem(p_page, f"-M{idx}", "M3", "MultiLine", fx, 96.0,
                         func_text=f"Motor {f.feeder_id}", is_main=True, pins="U1,V1,W1,PE")

            elif f.load_type == LoadType.MOTOR_STAR_DELTA:
                add_elem(p_page, f"-K{idx}M", "K_3P", "MultiLine", fx, 184.0,
                         part_no=_pn(f.selected_contactor_main), func_text="Line Contactor", is_main=False)
                add_elem(p_page, f"-F{idx}", "F_3P", "MultiLine", fx, 152.0,
                         part_no=_pn(f.selected_bimetal), func_text="Thermal Overload", is_main=True)
                # انشعاب استاندارد با گره زاویه (ANGLE) و سه‌راهی (T_NODE) برای کنتاکتورهای مثلث و ستاره
                add_elem(p_page, f"-K{idx}D", "K_3P", "MultiLine", fx + 24.0, 184.0,
                         part_no=_pn(f.selected_contactor_delta), func_text="Delta Contactor", is_main=False)
                add_elem(p_page, f"-K{idx}Y", "K_3P", "MultiLine", fx + 48.0, 184.0,
                         part_no=_pn(f.selected_contactor_star), func_text="Star Contactor", is_main=False)
                add_elem(p_page, f"-X{idx}", "X_6P", "MultiLine", fx, 120.0,
                         func_text="Motor Terminal 6P+PE", is_main=True, pins="U1,V1,W1,W2,U2,V2,PE")
                add_elem(p_page, f"-M{idx}", "M3_YD", "MultiLine", fx, 84.0,
                         func_text=f"Motor Y/D {f.feeder_id}", is_main=True, pins="U1,V1,W1,W2,U2,V2,PE")

            elif f.load_type == LoadType.MOTOR_VFD:
                add_elem(p_page, f"-U{idx}", "U_3P", "MultiLine", fx, 168.0,
                         part_no=_pn(f.selected_vfd), func_text="VFD Drive 3P", is_main=True,
                         pins="L1,L2,L3/U,V,W,PE")
                add_elem(p_page, f"-X{idx}", "X_4P", "MultiLine", fx, 128.0,
                         func_text="Shielded Motor Terminals", is_main=True, pins="U,V,W,PE")
                add_elem(p_page, f"-M{idx}", "M3", "MultiLine", fx, 88.0,
                         func_text=f"VFD Motor {f.feeder_id}", is_main=True, pins="U1,V1,W1,PE")

            elif f.load_type == LoadType.MOTOR_SOFT_STARTER:
                add_elem(p_page, f"-G{idx}", "G_3P", "MultiLine", fx, 168.0,
                         part_no=_pn(f.selected_soft_starter), func_text="Soft Starter 3P", is_main=True,
                         pins="1,3,5/2,4,6")
                add_elem(p_page, f"-X{idx}", "X_4P", "MultiLine", fx, 128.0,
                         func_text="Motor Terminal Strip", is_main=True, pins="U1,V1,W1,PE")
                add_elem(p_page, f"-M{idx}", "M3", "MultiLine", fx, 88.0,
                         func_text=f"Motor {f.feeder_id}", is_main=True, pins="U1,V1,W1,PE")

            # ۲. بخش فرمان (Control Circuit): هم‌راستا در ستون عمودی X=80.0 و X=128.0 با فعال‌سازی Cross-Reference
            if f.load_type in (LoadType.MOTOR_DOL, LoadType.MOTOR_STAR_DELTA,
                               LoadType.MOTOR_SOFT_STARTER, LoadType.MOTOR_VFD):
                c_page = f"1{idx:02d}"
                cx1, cx2 = 80.0, 128.0
                # کنتاکت کمکی کلید حفاظت فیدر (ارجاع متقابل مستقیم به -Q{idx} در صفحه قدرت)
                add_elem(c_page, f"-Q{idx}", "Q_AUX_NO", "MultiLine", cx1, 224.0,
                         func_text="Aux Contact (Cross-Ref to Power)", is_main=False, pins="13/14")
                # شستی استپ روی درب تابلو (+DR1)
                add_elem(c_page, f"-S{idx}0", "S2", "MultiLine", cx1, 184.0,
                         func_text="Stop Pushbutton (Door)", is_main=True, on_door=True, pins="11/12")
                # گره انشعاب T_NODE بالای شستی استارت برای تیغه خودنگهدار کنتاکتور (حذف خط مورب!)
                add_elem(c_page, f"-T_SEAL_{idx}A", "T_O", "MultiLine", cx1, 160.0,
                         func_text="Routing Tee Top", is_main=False, pins="1,2,3")
                add_elem(c_page, f"-S{idx}1", "S1", "MultiLine", cx1, 144.0,
                         func_text="Start Pushbutton (Door)", is_main=True, on_door=True, pins="13/14")
                # کنتاکت خودنگهدار (NO) در ستون موازی cx2=128.0 با زاویه‌های 90 درجه بالا و پایین
                k_tag = f"-K{idx}M" if f.load_type == LoadType.MOTOR_STAR_DELTA else f"-K{idx}"
                k_pn = _pn(f.selected_contactor_main)
                add_elem(c_page, f"-ANG_{idx}T", "ANGLE_DL", "MultiLine", cx2, 160.0,
                         func_text="Orthogonal Corner Top", is_main=False, pins="1,2")
                add_elem(c_page, k_tag, "K_NO", "MultiLine", cx2, 144.0,
                         func_text="Seal-in Aux Contact", is_main=False, pins="13/14")
                add_elem(c_page, f"-ANG_{idx}B", "ANGLE_UL", "MultiLine", cx2, 128.0,
                         func_text="Orthogonal Corner Bottom", is_main=False, pins="1,2")
                add_elem(c_page, f"-T_SEAL_{idx}B", "T_O", "MultiLine", cx1, 128.0,
                         func_text="Routing Tee Bottom", is_main=False, pins="1,2,3")
                # بوبین اصلی کنتاکتور (Main Function برای ایجاد جدول کنتاکت‌های Cross-Reference در زیر بوبین)
                add_elem(c_page, k_tag, "K1", "MultiLine", cx1, 96.0,
                         part_no=k_pn, func_text="Main Contactor Coil (A1/A2)", is_main=True, pins="A1/A2")
                # چراغ سیگنال روی درب تابلو (+DR1)
                add_elem(c_page, f"-H{idx}1", "H1", "MultiLine", 176.0, 96.0,
                         func_text="Run Indicator Lamp (Door)", is_main=True, on_door=True, pins="X1/X2")

        return elements

    @classmethod
    def generate_macro_xml(
        cls, project: ProjectSpec, feeders: List[FeederCalcOutput],
        summary: PanelSummaryOutput, macro_type: str = "ema"
    ) -> str:
        """
        تولید محتوای XML استاندارد ماکروی EPLAN (.ema / .emp / .ems) شامل:
        - RepresentationType="MultiLine"
        - RoutingPath و Autoconnecting هم‌راستا روی گام 4.0mm
        - CrossReferencedObjectsAll="true"
        - Higher-Level Function (=) و Mounting Location (+)
        """
        ext = macro_type.lower().lstrip(".")
        if ext not in ("ema", "emp", "ems"):
            ext = "ema"
        macro_kind_label = {
            "ema": "WindowMacro",
            "emp": "PageMacro",
            "ems": "SymbolMacro",
        }[ext]

        elems = cls._collect_multiline_elements(project, feeders, summary)
        hlf = _safe_id(project.project_name)
        loc = _safe_id(project.panel_tag)

        lines: List[str] = [
            '<?xml version="1.0" encoding="utf-8"?>',
            f'<EplanP8Macro Type="{macro_kind_label}" Extension=".{ext}" Version="2024" '
            f'MacroPath="{cls.MACRO_DIR_VAR}/{hlf}_{loc}.{ext}" '
            f'GeneratedAt="{datetime.now().strftime("%Y-%m-%d %H:%M")}">',
            '  <MacroSettings '
            'GridSizeMM="4.0" '
            'AutoConnectOrthogonal="true" '
            'RouteConnectionsAction="Topology:RouteConnections" '
            'UpdateCrossReferencesAction="UpdateCrossReferences" '
            'CrossReferencedObjectsAll="true" '
            f'HigherLevelFunction="={_xml_esc(hlf)}" '
            f'MountingLocation="+{_xml_esc(loc)}_MP1" '
            f'DoorLocation="+{_xml_esc(loc)}_DR1"/>',
            '  <Functions>',
        ]

        for el in elems:
            lines.append(
                f'    <Function '
                f'Page="{_xml_esc(str(el["page"]))}" '
                f'FullDeviceTag="{_xml_esc(str(el["full_tag"]))}" '
                f'HigherLevelFunction="={_xml_esc(str(el["hlf"]))}" '
                f'MountingLocation="+{_xml_esc(str(el["loc"]))}" '
                f'DeviceTag="{_xml_esc(str(el["dt"]))}" '
                f'SymbolLibrary="{_xml_esc(str(el["library"]))}" '
                f'SymbolName="{_xml_esc(str(el["symbol"]))}" '
                f'Representation="{_xml_esc(str(el["representation"]))}" '
                f'X="{el["x"]:.1f}" Y="{el["y"]:.1f}" '
                f'MainFunction="{str(el["is_main"]).lower()}" '
                f'CrossReferencedObjectsAll="{str(el["cross_ref_enabled"]).lower()}" '
                f'ConnectionPoints="{_xml_esc(str(el["pins"]))}" '
                f'PartNumber="{_xml_esc(str(el["part_no"]))}" '
                f'FunctionText="{_xml_esc(str(el["func_text"]))}"/>'
            )

        lines.append('  </Functions>')
        # تعریف مسیرهای سیم ارتوگونال (Orthogonal Routing Paths) بین قطعات هم‌راستا
        lines.append('  <OrthogonalRoutingPaths>')
        by_page_x: Dict[Tuple[str, float], List[Dict[str, object]]] = {}
        for el in elems:
            key = (str(el["page"]), float(el["x"]))
            by_page_x.setdefault(key, []).append(el)

        for (page, x_val), group in by_page_x.items():
            ordered = sorted(group, key=lambda item: -float(item["y"]))
            for i in range(len(ordered) - 1):
                src, dst = ordered[i], ordered[i + 1]
                lines.append(
                    f'    <RoutingPath Page="{_xml_esc(page)}" '
                    f'Source="{_xml_esc(str(src["full_tag"]))}" '
                    f'Target="{_xml_esc(str(dst["full_tag"]))}" '
                    f'X1="{x_val:.1f}" Y1="{float(src["y"]):.1f}" '
                    f'X2="{x_val:.1f}" Y2="{float(dst["y"]):.1f}" '
                    f'Direction="Vertical" Orthogonal="true"/>'
                )

        lines.append('  </OrthogonalRoutingPaths>')
        lines.append('</EplanP8Macro>')
        return "\n".join(lines)

    @classmethod
    def export_all_macro_variants(
        cls, output_dir: str, project: ProjectSpec,
        feeders: List[FeederCalcOutput], summary: PanelSummaryOutput
    ) -> Dict[str, str]:
        """ذخیره هر سه فرمت استاندارد ماکروی EPLAN (.ema, .emp, .ems) در مسیر خروجی."""
        base_name = f"{_safe_id(project.project_name)}_{_safe_id(project.panel_tag)}"
        saved_paths: Dict[str, str] = {}
        for ext in ("ema", "emp", "ems"):
            path = cls.resolve_macro_filepath(output_dir, base_name, macro_type=ext)
            xml_content = cls.generate_macro_xml(project, feeders, summary, macro_type=ext)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(xml_content)
            saved_paths[ext] = path
        return saved_paths
    # --- کلاس‌های سازگار با gui.py جهت جلوگیری از ImportError ---
class EplanMacroFileExporter(EplanMacroFileGenerator):
    """نام معادل سازگار با gui.py برای صادرات فایل‌های ماکرو"""
    pass


class EplanPageMacroExporter(EplanMacroFileGenerator):
    """نام معادل سازگار با gui.py برای صادرات ماکروی صفحه"""
    pass