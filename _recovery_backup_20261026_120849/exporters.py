# -*- coding: utf-8 -*-
"""ماژول صادرات گزارش‌های مهندسی، فایل‌های اکسل و مستندات تأیید طراحی (Design Verification)."""
import os
from datetime import datetime
from typing import List

from lv_assist.models import ProjectSpec, FeederCalcOutput, PanelSummaryOutput
from lv_assist.layout import PanelLayoutGenerator
from lv_assist.dxf_export import ControlLadderDxfExporter


class ExcelExporter:
    """صادرات لیست بار، نتایج محاسبات و خلاصه تجهیزات به فرمت اکسل."""

    @classmethod
    def export_file(cls, filepath: str, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput) -> None:
        try:
            import pandas as pd
            data = []
            for f in feeders:
                data.append({
                    "Feeder ID": f.feeder_id,
                    "Load Type": f.load_type.value,
                    "Power (kW)": f.power_kw,
                    "Current (A)": f.current_a,
                    "Cable Size": f.recommended_cable,
                    "Protection": f.selected_protection.part_number if f.selected_protection else "-",
                    "Loss (W)": f.total_feeder_loss_w,
                })
            df = pd.DataFrame(data)
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Feeders", index=False)
        except ImportError:
            # روش جایگزین در صورت عدم نصب pandas/openpyxl
            with open(filepath, "w", encoding="utf-8") as fh:
                fh.write(f"Project: {project.project_name}\nPanel Tag: {project.panel_tag}\nFeeders Count: {len(feeders)}\n")


class PrintableReportExporter:
    """تولید گزارش مهندسی جامع قابل چاپ (HTML / Printable Report)."""

    @classmethod
    def generate_html(cls, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput) -> str:
        svg_content = PanelLayoutGenerator.generate_svg(project, feeders, summary)
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LV Panel Engineering Report - {project.project_name}</title>
    <style>
        body {{ font-family: Tahoma, Arial, sans-serif; margin: 20px; color: #2C3E50; }}
        h1 {{ color: #1F4E78; border-bottom: 2px solid #1F4E78; padding-bottom: 8px; }}
        .section {{ margin-top: 20px; padding: 15px; border: 1px solid #D5D8DC; border-radius: 5px; background: #F8F9F9; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ABB2B9; padding: 8px; text-align: center; font-size: 13px; }}
        th {{ background: #1F4E78; color: white; }}
    .svg-container {{ text-align: center; margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>LV Panel Engineering Report</h1>
    <div class="section">
        <h3>Project Specifications</h3>
        <p><b>Project Name:</b> {project.project_name} | <b>Panel Tag:</b> {project.panel_tag}</p>
        <p><b>Standard:</b> IEC 61439-1/2 | <b>Generated At:</b> {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        <p><b>Estimated Dimensions:</b> W = {summary.estimated_panel_width_mm} mm, H = {summary.estimated_panel_height_mm} mm, D = {summary.estimated_panel_depth_mm} mm</p>
    </div>
    <div class="section">
        <h3>Panel Layout (Front View)</h3>
        <div class="svg-container">
            {svg_content}
        </div>
    </div>
</body>
</html>"""
        return html

    @classmethod
    def export_file(cls, filepath: str, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput) -> None:
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(cls.generate_html(project, feeders, summary))


class DesignVerificationExporter:
    """صادرات گزارش تأیید طراحی و اعتبار سنجی استانداردها (Design Verification per IEC 61439)."""

    @classmethod
    def export_file(cls, filepath: str, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput) -> None:
        layout_res = PanelLayoutGenerator.generate(project, feeders, summary)
        lines = [
            f"=== DESIGN VERIFICATION REPORT (IEC 61439) ===",
            f"Project: {project.project_name} ({project.panel_tag})",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"=" * 50,
            f"Fill Factor: {layout_res.fill_factor_pct}% (Max allowed: {PanelLayoutGenerator.MAX_FILL_PCT}%)",
            f"Total Power Loss: {layout_res.total_loss_w} W",
            f"Natural Dissipation: {layout_res.natural_dissipation_w} W",
            f"=" * 50,
            "Validation Rules Status:"
        ]
        for val in layout_res.validations:
            lines.append(f" - [{val.status.name}] {val.rule_id} ({val.standard_ref}): {val.description}")
            lines.append(f"   Evidence: {val.supporting_evidence}")
        
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))