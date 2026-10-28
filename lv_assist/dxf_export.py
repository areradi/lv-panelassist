# -*- coding: utf-8 -*-
"""خروجی DXF (فرمت R12) دیاگرام نردبانی مدار کنترلی — قابل ایمپورت به EPLAN P8 و CAD."""
from datetime import datetime
from typing import List, Tuple

from lv_assist.models import ProjectSpec, FeederCalcOutput, PanelSummaryOutput
from lv_assist.control_circuits import ControlCircuitGenerator
from lv_assist.report_export import export_current_text


def _ascii(s: str) -> str:
    return "".join(ch if 32 <= ord(ch) < 127 else " " for ch in str(s)).strip()


class _DxfDoc:
    """سند مینیمال DXF R12 (اتوکد 1009) با لایه‌بندی استاندارد CAD و استایل متن میلی‌متری."""

    # لایه‌های استاندارد مهندسی با رنگ ACI (مطابق توصیه ممیزی)
    LAYERS = [
        ("0", 7),
        ("LV_ENCLOSURE", 7),     # کادر و بدنه — سفید/مشکی
        ("LV_BUSBAR", 30),       # ریل‌های تغذیه L+/M — نارنجی مسی
        ("LV_DEVICES", 4),       # تجهیزات — فیروزه‌ای
        ("LV_WIRING_DUCT", 8),   # کانال سیم‌کشی — خاکستری خط‌چین
        ("LV_TEXT_TAGS", 2),     # متن و تگ‌ها — زرد
        ("LV_DIMENSIONS", 5),    # اندازه‌گذاری — آبی
    ]
    DUCT_LTYPES = {"LV_WIRING_DUCT"}

    def __init__(self) -> None:
        self.lines: List[Tuple[str, float, float, float, float]] = []
        self.texts: List[Tuple[str, float, float, float, str]] = []
        self.circles: List[Tuple[str, float, float, float]] = []
        self.polys: List[Tuple[str, List[Tuple[float, float]]]] = []

    @staticmethod
    def _f(v: float) -> str:
        return f"{v:.2f}"

    def line(self, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.lines.append((layer, x1, y1, x2, y2))

    def text(self, layer: str, x: float, y: float, h: float, s: str) -> None:
        self.texts.append((layer, x, y, h, _ascii(s)))

    def circle(self, layer: str, cx: float, cy: float, r: float) -> None:
        self.circles.append((layer, cx, cy, r))

    def rect(self, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.polys.append((layer, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]))

    def render(self) -> str:
        out: List[str] = ["0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n0\nENDSEC\n"]
        out.append("0\nSECTION\n2\nTABLES\n")
        # لایه‌ها
        out.append("0\nTABLE\n2\nLAYER\n70\n")
        out.append(f"{len(self.LAYERS)}\n")
        for name, color in self.LAYERS:
            ltype = "DASHED" if name in self.DUCT_LTYPES else "CONTINUOUS"
            out.append(f"0\nLAYER\n2\n{name}\n70\n0\n62\n{color}\n6\n{ltype}\n")
        out.append("0\nENDTAB\n")
        # نوع خط DASHED برای کانال سیم‌کشی
        out.append("0\nTABLE\n2\nLTYPE\n70\n1\n0\nLTYPE\n2\nDASHED\n70\n64\n3\n_ _ _ _\n72\n65\n73\n2\n40\n0.75\n49\n0.5\n74\n0\n49\n-0.25\n74\n0\n0\nENDTAB\n")
        # استایل متن STANDARD با فونت سازگار CAD و ارتفاع متغیر (میلی‌متر)
        out.append("0\nTABLE\n2\nSTYLE\n70\n1\n0\nSTYLE\n2\nSTANDARD\n70\n0\n40\n0.0\n3\ntxt.shx\n0\nENDTAB\n")
        out.append("0\nENDSEC\n0\nSECTION\n2\nENTITIES\n")
        for layer, x1, y1, x2, y2 in self.lines:
            out.append(f"0\nLINE\n8\n{layer}\n10\n{self._f(x1)}\n20\n{self._f(y1)}\n11\n{self._f(x2)}\n21\n{self._f(y2)}\n")
        for layer, x, y, h, s in self.texts:
            out.append(f"0\nTEXT\n8\n{layer}\n10\n{self._f(x)}\n20\n{self._f(y)}\n40\n{self._f(h)}\n1\n{s}\n")
        for layer, cx, cy, r in self.circles:
            out.append(f"0\nCIRCLE\n8\n{layer}\n10\n{self._f(cx)}\n20\n{self._f(cy)}\n40\n{self._f(r)}\n")
        for layer, pts in self.polys:
            out.append(f"0\nPOLYLINE\n8\n{layer}\n66\n1\n70\n1\n")
            for x, y in pts:
                out.append(f"0\nVERTEX\n8\n{layer}\n10\n{self._f(x)}\n20\n{self._f(y)}\n")
            out.append(f"0\nSEQEND\n8\n{layer}\n")
        out.append("0\nENDSEC\n0\nEOF\n")
        return "".join(out)


class ControlLadderDxfExporter:
    """دیاگرام نردبانی ۲۴ ولت DC به صورت DXF با همان هندسه SVG (محور Y رو به بالا)."""

    RAIL_X_L, RAIL_X_R = 50.0, 950.0
    DEV_W, DEV_H, PITCH = 84.0, 34.0, 52.0
    FRAME_L, FRAME_R, FRAME_TOP, FRAME_BOT = 20.0, 980.0, 16.0, 6.0
    KIND_MARK = {"io": "", "coil": "COIL", "no": "NO", "nc": "NC", "lamp": ""}

    @classmethod
    def _add_dimensions(cls, doc: _DxfDoc, total_h: float) -> None:
        """اندازه‌گذاری کلی نقشه روی لایه LV_DIMENSIONS (ACI 5)."""
        def dy(svg_y: float) -> float:
            return total_h - svg_y
        y_dim = dy(total_h) - 14.0
        doc.line("LV_DIMENSIONS", cls.FRAME_L, y_dim, cls.FRAME_R, y_dim)
        for x in (cls.FRAME_L, cls.FRAME_R):
            doc.line("LV_DIMENSIONS", x, y_dim - 3.0, x, y_dim + 3.0)
        doc.text("LV_DIMENSIONS", (cls.FRAME_L + cls.FRAME_R) / 2.0, y_dim - 4.0, 3.5, f"{cls.FRAME_R - cls.FRAME_L:.0f} mm")
        x_dim = cls.FRAME_L - 14.0
        doc.line("LV_DIMENSIONS", x_dim, dy(cls.FRAME_TOP), x_dim, dy(total_h - cls.FRAME_BOT))
        for y_svg in (cls.FRAME_TOP, total_h - cls.FRAME_BOT):
            doc.line("LV_DIMENSIONS", x_dim - 3.0, dy(y_svg), x_dim + 3.0, dy(y_svg))

    @classmethod
    def generate(cls, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput) -> str:
        specs = ControlCircuitGenerator.rung_specs(project, feeders)
        total_h = 194.0 + sum(32.0 + 52.0 * len(rungs) for kind, _, _, _, rungs in specs if kind == "feeder") + 34.0
        wires_all = ControlCircuitGenerator.build_all_wires(project, feeders, summary)
        doc = _DxfDoc()

        def dy(svg_y: float) -> float:
            return total_h - svg_y

        # قاب و عنوان (متن لاتین برای سازگاری CAD)
        doc.rect("LV_ENCLOSURE", cls.FRAME_L, dy(total_h - cls.FRAME_BOT), cls.FRAME_R, dy(cls.FRAME_TOP))
        doc.text("LV_TEXT_TAGS", 30.0, dy(38.0), 7.0, f"CONTROL CIRCUIT - {project.project_name} ({project.panel_tag})")
        doc.text("LV_TEXT_TAGS", 30.0, dy(54.0), 4.0, f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | 24VDC per IEC 60204-1")
        # ریل‌های تغذیه L+/M روی لایه شینه
        doc.line("LV_BUSBAR", cls.RAIL_X_L, dy(62.0), cls.RAIL_X_L, dy(total_h - 22.0))
        doc.line("LV_BUSBAR", cls.RAIL_X_R, dy(62.0), cls.RAIL_X_R, dy(total_h - 22.0))
        doc.text("LV_TEXT_TAGS", cls.RAIL_X_L - 14.0, dy(62.0), 4.0, "L+")
        doc.text("LV_TEXT_TAGS", cls.RAIL_X_R + 8.0, dy(62.0), 4.0, "M")

        y = 64.0
        for kind, title, wno, color, rungs in specs:
            if kind == "common":
                doc.rect("LV_ENCLOSURE", 20.0, dy(y - 16.0), 980.0, dy(y + 114.0))
                doc.text("LV_TEXT_TAGS", 32.0, dy(y - 6.0), 5.0, title)
                y += 22
                cls._draw_rung(doc, rungs[0], wno, y, total_h)
                y += 52
                cls._draw_rung(doc, rungs[1], wno, y, total_h)
                y += 56
            else:
                block_h = 52.0 * len(rungs) + 30.0
                doc.rect("LV_ENCLOSURE", 20.0, dy(y - 14.0), 980.0, dy(y + block_h - 14.0))
                doc.text("LV_TEXT_TAGS", 32.0, dy(y - 6.0), 5.0, title)
                y += 20
                for rung in rungs:
                    cls._draw_rung(doc, rung, wno, y, total_h)
                    y += 52
                y += 12

        doc.text("LV_TEXT_TAGS", 30.0, dy(y + 10.0), 4.0, f"Wires: {len(wires_all)} | drawn by LV-PanelAssist (DXF R12)")
        cls._add_dimensions(doc, total_h)
        return doc.render()

    @classmethod
    def _draw_rung(cls, doc: _DxfDoc, devices: List[Tuple[str, str, str]], wno: str, y: float, total_h: float) -> None:
        def dy(svg_y: float) -> float:
            return total_h - svg_y

        doc.line("LV_BUSBAR", cls.RAIL_X_L, dy(y), cls.RAIL_X_R, dy(y))
        doc.text("LV_TEXT_TAGS", cls.RAIL_X_L + 70.0, dy(y - 14.0), 3.5, wno)
        n = len(devices)
        span = cls.RAIL_X_R - cls.RAIL_X_L - 100.0
        for i, (tag, terms, kind) in enumerate(devices):
            x = cls.RAIL_X_L + 70.0 + span * (i + 0.5) / n
            if kind == "lamp":
                doc.circle("LV_DEVICES", x, dy(y), 10.0)
                doc.text("LV_TEXT_TAGS", x, dy(y - 17.0), 3.0, tag)
                doc.text("LV_TEXT_TAGS", x, dy(y + 9.0), 2.5, terms)
            else:
                doc.rect("LV_DEVICES", x - cls.DEV_W / 2, dy(y - cls.DEV_H / 2), x + cls.DEV_W / 2, dy(y + cls.DEV_H / 2))
                doc.text("LV_TEXT_TAGS", x, dy(y - 17.0 - 5.0), 3.2, tag)
                doc.text("LV_TEXT_TAGS", x, dy(y + 8.0), 2.6, terms)
                mark = cls.KIND_MARK.get(kind, "")
                if mark:
                    doc.text("LV_TEXT_TAGS", x, dy(y + 17.0 + 10.0), 3.0, mark)

    @classmethod
    def export_file(cls, filepath: str, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput, *, validations=None) -> None:
        return export_current_text(filepath, project, feeders, summary, validations, cls.generate,
                                   encoding="ascii", errors="replace")
