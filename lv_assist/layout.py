# -*- coding: utf-8 -*-
"""برآورد اولیهٔ فضای تجهیزات؛ خروجی تصویری فقط نمای بلوکیِ معماری است."""
from typing import Dict, List, Optional

from lv_assist.models import (
    ProjectSpec, FeederCalcOutput, PanelSummaryOutput, CatalogDevice,
    LoadType, LayoutDevice, LayoutRow, PanelLayoutResult, ValidationResult, ValidationStatus,
)
from lv_assist.i18n import tr
from lv_assist.report_export import export_current_text


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class PanelLayoutGenerator:
    """جانمایی تجهیزات در چهار ناحیه: خنک‌سازی، قدرت، PFC و کنترل (با کانال سیم‌کشی، حریم قوس و فضای رزرو)."""

    HORIZONTAL_DUCT_HEIGHT_MM = 50.0       # داکت افقی بین ردیف‌ها
    VERTICAL_DUCT_WIDTH_MM = 60.0          # داکت عمودی دو طرف سینی مونتاژ
    MCCB_ARC_CLEARANCE_MM = 80.0           # حریم قوس/تخلیه گاز کلیدهای قدرت
    CABLE_GLAND_BOTTOM_ZONE_MM = 200.0     # ناحیه گلند و ترمینال پایین تابلو
    BUS_BAR_ZONE_HEIGHT_MM = 120.0         # ناحیه شینه اصلی (بالا)
    DEVICE_HORIZONTAL_GAP_MM = 12.0        # حداقل فاصله افقی تهویه و نصب بین دو تجهیز روی ریل
    RAIL_SIDE_PADDING_MM = 15.0            # حاشیه ایمنی دو سر ریل تا داکت عمودی
    MAX_FILL_PCT = 85.0                    # حد مجاز اشغال ریل (IEC 61439-2)
    SPARE_SPACE_PCT = 20.0                 # فضای رزرو الزامی
    ZONE_ORDER = ["COOLING", "POWER", "PFC", "CONTROL"]

    # حداقل فواصل هوایی عمودی (Clearance) بر اساس نوع تجهیز طبق IEC 61439-2
    DEFAULT_CLEARANCE_BY_TYPE: Dict[str, float] = {
        "ACB": 120.0,
        "MCCB": 80.0,
        "VFD": 100.0,
        "SOFT_STARTER": 100.0,
        "PSU": 35.0,
        "CONTACTOR": 25.0,
        "MCB": 25.0,
        "MPCB": 30.0,
    }

    @classmethod
    def _form_partition_factor(cls, form: str) -> float:
        f = str(form or "").lower()
        if f.startswith("form 4"):
            return 1.15
        if f.startswith("form 3"):
            return 1.10
        if f.startswith("form 2"):
            return 1.05
        return 1.0

    @classmethod
    def _dev(cls, tag: str, dev: Optional[CatalogDevice], zone: str, clearance: float = 0.0,
             qty: int = 1, extra_loss_w: float = 0.0) -> List[LayoutDevice]:
        if dev is None or dev.width_mm <= 0:
            return []
        dtype = str(getattr(dev, "device_type", "") or "").upper()
        min_clr = cls.DEFAULT_CLEARANCE_BY_TYPE.get(dtype, 20.0)
        if dtype == "MCCB":
            min_clr = max(min_clr, cls.MCCB_ARC_CLEARANCE_MM)
        clearance = max(clearance, min_clr)
        return [LayoutDevice(
            tag=tag, part_number=dev.part_number, zone=zone,
            width_mm=dev.width_mm * qty + 10.0 * (qty - 1),
            height_mm=dev.height_mm, depth_mm=dev.depth_mm,
            loss_w=dev.power_loss_w * qty + extra_loss_w,
            clearance_mm=clearance,
        )]

    @classmethod
    def _collect_devices(cls, project: ProjectSpec, feeders: List[FeederCalcOutput],
                         summary: PanelSummaryOutput) -> List[LayoutDevice]:
        devs: List[LayoutDevice] = []
        devs += cls._dev("-E1", summary.selected_fan, "COOLING")
        devs += cls._dev("-Q0", summary.main_breaker, "POWER")
        devs += cls._dev("-F9", summary.selected_spd, "POWER")
        for i, f in enumerate(feeders, start=1):
            devs += cls._dev(f"-Q{i}", f.selected_protection, "POWER",
                             extra_loss_w=f.total_feeder_loss_w)
            if f.load_type == LoadType.MOTOR_STAR_DELTA:
                devs += cls._dev(f"-K{i}M", f.selected_contactor_main, "POWER")
                devs += cls._dev(f"-K{i}D", f.selected_contactor_delta, "POWER")
                devs += cls._dev(f"-K{i}Y", f.selected_contactor_star, "POWER")
                devs += cls._dev(f"-F{i}", f.selected_bimetal, "POWER")
                devs += cls._dev(f"-K{i}T", f.selected_timer_yd, "CONTROL")
            elif f.load_type == LoadType.MOTOR_DOL:
                devs += cls._dev(f"-K{i}", f.selected_contactor_main, "POWER")
            devs += cls._dev(f"-G{i}", f.selected_soft_starter, "POWER", clearance=100.0)
            devs += cls._dev(f"-U{i}", f.selected_vfd, "POWER", clearance=100.0)
        n_steps = len(summary.cap_bank_steps) or 1
        devs += cls._dev("-Qcap", summary.cap_bank_protection, "PFC")
        devs += cls._dev("-Kcap", summary.cap_bank_contactor, "PFC", qty=n_steps)
        devs += cls._dev("-Lcap", summary.cap_bank_reactor_dev, "PFC", qty=n_steps)
        devs += cls._dev("-Ccap", summary.cap_bank_module_dev, "PFC", qty=n_steps)
        devs += cls._dev("-Q01", summary.selected_psu_primary_mcb, "CONTROL")
        devs += cls._dev("-G1", summary.selected_psu_24v, "CONTROL")
        devs += cls._dev("-F0", summary.selected_dc_selectivity_mod, "CONTROL")
        return devs

    @classmethod
    def generate(cls, project: ProjectSpec, feeders: List[FeederCalcOutput],
                 summary: PanelSummaryOutput, spare_space_pct: float = 20.0) -> PanelLayoutResult:
        panel_w = summary.estimated_panel_width_mm
        panel_h = summary.estimated_panel_height_mm
        panel_d = summary.estimated_panel_depth_mm
        if summary.selected_enclosure is not None:
            panel_w = panel_w or summary.selected_enclosure.width_mm
            panel_h = panel_h or summary.selected_enclosure.height_mm
            panel_d = panel_d or summary.selected_enclosure.depth_mm

        usable = max(panel_w - 2.0 * cls.VERTICAL_DUCT_WIDTH_MM, 100.0)
        effective_rail_w = max(usable - 2.0 * cls.RAIL_SIDE_PADDING_MM, 80.0)

        devices = cls._collect_devices(project, feeders, summary)
        rows: List[LayoutRow] = []
        y_mm = cls.BUS_BAR_ZONE_HEIGHT_MM
        row_no = 0
        for zone in cls.ZONE_ORDER:
            zone_devs = sorted(
                [d for d in devices if d.zone == zone],
                key=lambda d: (-d.clearance_mm, -d.loss_w, -d.width_mm),
            )
            row_devs: List[LayoutDevice] = []
            row_w = 0.0
            for d in zone_devs:
                gap = cls.DEVICE_HORIZONTAL_GAP_MM if row_devs else 0.0
                if row_devs and (row_w + gap + d.width_mm > effective_rail_w):
                    row_h = max(x.height_mm for x in row_devs) + max(x.clearance_mm for x in row_devs)
                    row_no += 1
                    rows.append(LayoutRow(row_no=row_no, zone=zone, y_mm=y_mm,
                                          used_width_mm=round(row_w, 1), devices=row_devs))
                    y_mm += row_h + cls.HORIZONTAL_DUCT_HEIGHT_MM
                    row_devs, row_w = [], 0.0
                    gap = 0.0
                row_devs.append(d)
                row_w += gap + d.width_mm
            if row_devs:
                row_h = max(x.height_mm for x in row_devs) + max(x.clearance_mm for x in row_devs)
                row_no += 1
                rows.append(LayoutRow(row_no=row_no, zone=zone, y_mm=y_mm,
                                      used_width_mm=round(row_w, 1), devices=row_devs))
                y_mm += row_h + cls.HORIZONTAL_DUCT_HEIGHT_MM

        form_factor = cls._form_partition_factor(project.internal_separation_form)
        total_w = sum(d.width_mm for d in devices) * form_factor
        n_rows = max(len(rows), 1)
        spare_frac = max(0.0, min(0.9, spare_space_pct / 100.0))
        fill_pct = round(100.0 * total_w / max(usable * n_rows * (1.0 - spare_frac), 1.0), 1)

        validations = cls._build_validations(project, summary, devices, rows, fill_pct, usable,
                                             spare_space_pct, form_factor)
        return PanelLayoutResult(
            panel_width_mm=panel_w, panel_height_mm=panel_h, panel_depth_mm=panel_d,
            usable_width_mm=round(usable, 1), rows=rows, fill_factor_pct=fill_pct,
            total_loss_w=round(summary.total_power_loss_w, 1),
            natural_dissipation_w=round(summary.enclosure_natural_dissipation_w, 1),
            spare_space_pct=spare_space_pct, form_partition_factor=form_factor,
            validations=validations,
        )

    @classmethod
    def _build_validations(cls, project: ProjectSpec, summary: PanelSummaryOutput,
                           devices: List[LayoutDevice], rows: List[LayoutRow],
                           fill_pct: float, usable: float, spare_space_pct: float,
                           form_factor: float) -> List[ValidationResult]:
        vals: List[ValidationResult] = []

        if fill_pct > 100.0:
            fill_status, fill_action = ValidationStatus.ERROR, tr("val_lay_fill_action")
        elif fill_pct > cls.MAX_FILL_PCT:
            fill_status, fill_action = ValidationStatus.WARNING, tr("val_lay_fill_action")
        else:
            fill_status, fill_action = ValidationStatus.COMPLETED, tr("val_no_action")
        vals.append(ValidationResult(
            rule_id="RULE-LAY-020", feeder_id="PANEL", standard_ref="IEC 61439-2",
            status=fill_status,
            description=tr("val_lay_fill_desc"),
            supporting_evidence=tr("val_lay_fill_ev", a=fill_pct, b=usable),
            consequence=tr("val_lay_fill_cons"),
            recommended_action=fill_action,
        ))

        used_h = max((r.y_mm + max(d.height_mm for d in r.devices) + max(d.clearance_mm for d in r.devices)
                      for r in rows), default=0.0)
        avail_h = (summary.estimated_panel_height_mm or 0.0) - cls.CABLE_GLAND_BOTTOM_ZONE_MM - cls.BUS_BAR_ZONE_HEIGHT_MM
        spare_ok = fill_pct <= 100.0 - spare_space_pct
        height_ok = used_h <= avail_h
        vals.append(ValidationResult(
            rule_id="RULE-LAY-024", feeder_id="PANEL", standard_ref="IEC 61439-2",
            status=ValidationStatus.COMPLETED if (spare_ok and height_ok) else ValidationStatus.WARNING,
            description=tr("val_lay_spare_desc"),
            supporting_evidence=tr("val_lay_spare_ev", a=fill_pct, b=100.0 - spare_space_pct,
                                   c=round(used_h, 1), d=round(avail_h, 1),
                                   e=cls.HORIZONTAL_DUCT_HEIGHT_MM, f=cls.VERTICAL_DUCT_WIDTH_MM,
                                   g=cls.CABLE_GLAND_BOTTOM_ZONE_MM, h=form_factor),
            consequence=tr("val_lay_spare_cons"),
            recommended_action=tr("val_no_action" if (spare_ok and height_ok) else "val_lay_spare_action"),
        ))

        dissip = summary.enclosure_natural_dissipation_w
        if summary.selected_fan is not None:
            dissipation_w = dissip + summary.selected_fan.airflow_m3h * 3.0
        else:
            dissipation_w = dissip
        loss_ok = summary.total_power_loss_w <= dissipation_w
        vals.append(ValidationResult(
            rule_id="RULE-LAY-021", feeder_id="PANEL", standard_ref="IEC 61439-2 / IEC TR 60890",
            status=ValidationStatus.COMPLETED if loss_ok else ValidationStatus.WARNING,
            description=tr("val_lay_loss_desc"),
            supporting_evidence=tr("val_lay_loss_ev", a=summary.total_power_loss_w, b=dissipation_w),
            consequence=tr("val_lay_loss_cons"),
            recommended_action=tr("val_no_action" if loss_ok else "val_lay_loss_action"),
        ))

        max_depth = max((d.depth_mm for d in devices), default=0.0)
        # لحاظ کردن 30mm فاصله نصب سینی و تجهیزات روی درب (پوشانده شدن تداخل عمق)
        depth_ok = max_depth <= (summary.estimated_panel_depth_mm or 0) - 30.0
        vals.append(ValidationResult(
            rule_id="RULE-LAY-022", feeder_id="PANEL", standard_ref="IEC 61439-2",
            status=ValidationStatus.COMPLETED if depth_ok else ValidationStatus.WARNING,
            description=tr("val_lay_depth_desc"),
            supporting_evidence=tr("val_lay_depth_ev", a=max_depth, b=summary.estimated_panel_depth_mm),
            consequence=tr("val_lay_depth_cons"),
            recommended_action=tr("val_no_action" if depth_ok else "val_lay_depth_action"),
        ))

        zones_seen = [r.zone for r in rows]
        separated = not ("CONTROL" in zones_seen and "POWER" in zones_seen
                         and zones_seen.index("CONTROL") < zones_seen.index("POWER"))
        vals.append(ValidationResult(
            rule_id="RULE-LAY-023", feeder_id="PANEL", standard_ref="IEC 61439-2",
            status=ValidationStatus.COMPLETED if separated else ValidationStatus.WARNING,
            description=tr("val_lay_zone_desc"),
            supporting_evidence=tr("val_lay_zone_ev"),
            consequence=tr("val_lay_zone_cons"),
            recommended_action=tr("val_no_action" if separated else "val_lay_zone_action"),
        ))
        return vals

    # ---------------------------------------------------------------- SVG front view (Mounting Plate + Separate Door Region)




    @classmethod
    def generate_svg(cls, project, feeders, summary):
        from lv_assist.architecture import ArchitectureOverview
        return ArchitectureOverview.generate_svg(project, feeders, summary)

    @classmethod
    def generate_svg_file(cls, filepath: str, project: ProjectSpec,
                          feeders: List[FeederCalcOutput], summary: PanelSummaryOutput, *, validations=None) -> None:
        return export_current_text(filepath, project, feeders, summary, validations, cls.generate_svg)
