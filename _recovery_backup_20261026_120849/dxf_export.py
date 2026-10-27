# -*- coding: utf-8 -*-
"""خروجی DXF استاندارد (فرمت R12 / AC1009 با مقیاس میلی‌متر و نمادهای IEC 60617) — قابل ایمپورت در EPLAN P8 و AutoCAD."""
from datetime import datetime
from typing import List, Tuple

from lv_assist.models import ProjectSpec, FeederCalcOutput, PanelSummaryOutput
from lv_assist.control_circuits import ControlCircuitGenerator


def _ascii(s: str) -> str:
    return "".join(ch if 32 <= ord(ch) < 127 else " " for ch in str(s)).strip()


class _DxfDoc:
    """سند استاندارد DXF R12 (AC1009) با واحد میلی‌متر ($INSUNITS=4)، لایه‌بندی استاندارد و تراز متنی."""

    LAYERS = [
        ("0", 7),
        ("LV_ENCLOSURE", 7),     # کادر و بدنه — سفید/مشکی
        ("LV_BUSBAR", 30),       # ریل‌های تغذیه L+/M — نارنجی مسی
        ("LV_WIRES", 3),         # سیم‌های ارتباطی مدار فرمان — سبز
        ("LV_DEVICES", 4),       # نمادهای استاندارد IEC 60617 — فیروزه‌ای
        ("LV_WIRING_DUCT", 8),   # کانال سیم‌کشی — خاکستری خط‌چین
        ("LV_TEXT_TAGS", 2),     # متن و تگ‌ها — زرد
        ("LV_DIMENSIONS", 5),    # اندازه‌گذاری — آبی
    ]
    DUCT_LTYPES = {"LV_WIRING_DUCT"}

    def __init__(self) -> None:
        self.lines: List[Tuple[str, float, float, float, float]] = []
        # (layer, x, y, h, text, center_align)
        self.texts: List[Tuple[str, float, float, float, str, bool]] = []
        self.circles: List[Tuple[str, float, float, float]] = []
        self.polys: List[Tuple[str, List[Tuple[float, float]]]] = []

    @staticmethod
    def _f(v: float) -> str:
        return f"{v:.2f}"

    def line(self, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.lines.append((layer, x1, y1, x2, y2))

    def text(self, layer: str, x: float, y: float, h: float, s: str, center: bool = False) -> None:
        self.texts.append((layer, x, y, h, _ascii(s), center))

    def circle(self, layer: str, cx: float, cy: float, r: float) -> None:
        self.circles.append((layer, cx, cy, r))

    def rect(self, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.polys.append((layer, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]))

    def render(self) -> str:
        # ۱. HEADER با تعریف صریح واحد میلی‌متر ($INSUNITS = 4) و سیستم متریک ($MEASUREMENT = 1)
        out: List[str] = [
            "0\nSECTION\n2\nHEADER\n"
            "9\n$ACADVER\n1\nAC1009\n"
            "9\n$INSUNITS\n70\n4\n"
            "9\n$MEASUREMENT\n70\n1\n"
            "9\n$EXTMIN\n10\n0.00\n20\n-50.00\n"
            "9\n$EXTMAX\n10\n1020.00\n20\n2000.00\n"
            "0\nENDSEC\n"
        ]

        # ۲. TABLES (ترتیب اجباری استاندارد اتوکد: ابتدا LTYPE، سپس LAYER، سپس STYLE)
        out.append("0\nSECTION\n2\nTABLES\n")
        out.append(
            "0\nTABLE\n2\nLTYPE\n70\n2\n"
            "0\nLTYPE\n2\nCONTINUOUS\n70\n64\n3\nSolid line\n72\n65\n73\n0\n40\n0.0\n"
            "0\nLTYPE\n2\nDASHED\n70\n64\n3\n_ _ _ _\n72\n65\n73\n2\n40\n0.75\n49\n0.5\n74\n0\n49\n-0.25\n74\n0\n"
            "0\nENDTAB\n"
        )
        out.append(f"0\nTABLE\n2\nLAYER\n70\n{len(self.LAYERS)}\n")
        for name, color in self.LAYERS:
            ltype = "DASHED" if name in self.DUCT_LTYPES else "CONTINUOUS"
            out.append(f"0\nLAYER\n2\n{name}\n70\n0\n62\n{color}\n6\n{ltype}\n")
        out.append("0\nENDTAB\n")

        # استایل متن استاندارد با فونت سازگار و قابل ویرایش در AutoCAD و EPLAN
        out.append(
            "0\nTABLE\n2\nSTYLE\n70\n1\n"
            "0\nSTYLE\n2\nSTANDARD\n70\n0\n40\n0.0\n41\n1.0\n50\n0.0\n71\n0\n42\n3.5\n3\narial.ttf\n"
            "0\nENDTAB\n0\nENDSEC\n"
        )

        # ۳. ENTITIES
        out.append("0\nSECTION\n2\nENTITIES\n")
        for layer, x1, y1, x2, y2 in self.lines:
            out.append(
                f"0\nLINE\n8\n{layer}\n6\nBYLAYER\n"
                f"10\n{self._f(x1)}\n20\n{self._f(y1)}\n30\n0.00\n"
                f"11\n{self._f(x2)}\n21\n{self._f(y2)}\n31\n0.00\n"
            )
        for layer, x, y, h, s, center in self.texts:
            if center:
                out.append(
                    f"0\nTEXT\n8\n{layer}\n7\nSTANDARD\n"
                    f"10\n{self._f(x)}\n20\n{self._f(y)}\n30\n0.00\n"
                    f"40\n{self._f(h)}\n1\n{s}\n"
                    f"72\n1\n11\n{self._f(x)}\n21\n{self._f(y)}\n31\n0.00\n"
                )
            else:
                out.append(
                    f"0\nTEXT\n8\n{layer}\n7\nSTANDARD\n"
                    f"10\n{self._f(x)}\n20\n{self._f(y)}\n30\n0.00\n"
                    f"40\n{self._f(h)}\n1\n{s}\n"
                )
        for layer, cx, cy, r in self.circles:
            out.append(
                f"0\nCIRCLE\n8\n{layer}\n6\nBYLAYER\n"
                f"10\n{self._f(cx)}\n20\n{self._f(cy)}\n30\n0.00\n40\n{self._f(r)}\n"
            )
        for layer, pts in self.polys:
            out.append(f"0\nPOLYLINE\n8\n{layer}\n66\n1\n70\n1\n")
            for x, y in pts:
                out.append(f"0\nVERTEX\n8\n{layer}\n10\n{self._f(x)}\n20\n{self._f(y)}\n30\n0.00\n")
            out.append(f"0\nSEQEND\n8\n{layer}\n")
        out.append("0\nENDSEC\n0\nEOF\n")
        return "".join(out)


class ControlLadderDxfExporter:
    """دیاگرام نردبانی ۲۴ ولت DC به صورت DXF با نمادهای استاندارد IEC 60617 و مقیاس ۱:۱ میلی‌متری."""

    RAIL_X_L, RAIL_X_R = 50.0, 950.0
    DEV_W, DEV_H, PITCH = 36.0, 20.0, 52.0
    FRAME_L, FRAME_R, FRAME_TOP, FRAME_BOT = 20.0, 980.0, 16.0, 6.0
    KIND_MARK = {"io": "PROT", "coil": "COIL", "no": "NO", "nc": "NC", "lamp": "IND"}

    @classmethod
    def _add_dimensions(cls, doc: _DxfDoc, total_h: float) -> None:
        """اندازه‌گذاری کلی نقشه روی لایه LV_DIMENSIONS (ACI 5)."""
        def dy(svg_y: float) -> float:
            return total_h - svg_y
        y_dim = dy(total_h) - 14.0
        doc.line("LV_DIMENSIONS", cls.FRAME_L, y_dim, cls.FRAME_R, y_dim)
        for x in (cls.FRAME_L, cls.FRAME_R):
            doc.line("LV_DIMENSIONS", x, y_dim - 3.0, x, y_dim + 3.0)
        doc.text("LV_DIMENSIONS", (cls.FRAME_L + cls.FRAME_R) / 2.0, y_dim - 5.0, 3.5,
                 f"{cls.FRAME_R - cls.FRAME_L:.0f} mm", center=True)
        x_dim = cls.FRAME_L - 14.0
        doc.line("LV_DIMENSIONS", x_dim, dy(cls.FRAME_TOP), x_dim, dy(total_h - cls.FRAME_BOT))
        for y_svg in (cls.FRAME_TOP, total_h - cls.FRAME_BOT):
            doc.line("LV_DIMENSIONS", x_dim - 3.0, dy(y_svg), x_dim + 3.0, dy(y_svg))

    @classmethod
    def _draw_iec60617_symbol(cls, doc: _DxfDoc, kind: str, cx: float, cy: float) -> Tuple[float, float]:
        """
        ترسیم نماد استاندارد IEC 60617 برای هر تجهیز در مختصات (cx, cy) و بازگرداندن
        نقاط اتصال چپ و راست (x_left_pin, x_right_pin) جهت قطع صحیح خط سیم در داخل قطعه.
        """
        half_w = 12.0
        x_left = cx - half_w
        x_right = cx + half_w

        if kind == "no":
            # کنتاکت باز (Normally Open - IEC 60617): دو پایه و تیغه مایل باز در بالا
            doc.circle("LV_DEVICES", x_left, cy, 1.2)
            doc.circle("LV_DEVICES", x_right, cy, 1.2)
            doc.line("LV_DEVICES", x_left, cy, x_right - 2.0, cy + 7.5)
        elif kind == "nc":
            # کنتاکت بسته (Normally Closed - IEC 60617): دو پایه، خط عمودی ضامن و تیغه بسته
            doc.circle("LV_DEVICES", x_left, cy, 1.2)
            doc.circle("LV_DEVICES", x_right, cy, 1.2)
            doc.line("LV_DEVICES", x_right, cy, x_right, cy + 7.0)
            doc.line("LV_DEVICES", x_left, cy, x_right + 2.0, cy + 5.5)
        elif kind == "coil":
            # بوبین کنتاکتور/رله (Coil A1-A2 - IEC 60617): مستطیل استاندارد 24x14 با خطوط اتصال جانبی
            doc.rect("LV_DEVICES", x_left, cy - 7.0, x_right, cy + 7.0)
            doc.line("LV_DEVICES", cx - 4.0, cy - 7.0, cx + 4.0, cy + 7.0)
        elif kind == "lamp":
            # چراغ سیگنال (Indicator Lamp X1-X2 - IEC 60617): دایره با ضربدر داخلی (X)
            r = 8.5
            x_left, x_right = cx - r, cx + r
            doc.circle("LV_DEVICES", cx, cy, r)
            d = r * 0.7071
            doc.line("LV_DEVICES", cx - d, cy - d, cx + d, cy + d)
            doc.line("LV_DEVICES", cx - d, cy + d, cx + d, cy - d)
        else:
            # المان حفاظتی / ورودی-خروجی (Fuse / Breaker / IO - IEC 60617)
            doc.rect("LV_DEVICES", x_left, cy - 6.0, x_right, cy + 6.0)
            doc.line("LV_DEVICES", x_left, cy, x_right, cy)

        return x_left, x_right

    @classmethod
    def generate(cls, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput) -> str:
        specs = ControlCircuitGenerator.rung_specs(project, feeders)
        total_h = 194.0 + sum(32.0 + 52.0 * len(rungs) for kind, _, _, _, rungs in specs if kind == "feeder") + 34.0
        wires_all = ControlCircuitGenerator.build_all_wires(project, feeders, summary)
        doc = _DxfDoc()

        def dy(svg_y: float) -> float:
            return total_h - svg_y

        # قاب و عنوان
        doc.rect("LV_ENCLOSURE", cls.FRAME_L, dy(total_h - cls.FRAME_BOT), cls.FRAME_R, dy(cls.FRAME_TOP))
        doc.text("LV_TEXT_TAGS", 30.0, dy(38.0), 7.0, f"CONTROL CIRCUIT - {project.project_name} ({project.panel_tag})")
        doc.text("LV_TEXT_TAGS", 30.0, dy(54.0), 4.0, f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | 24VDC per IEC 60204-1 & IEC 60617")
        # ریل‌های تغذیه L+/M روی لایه شینه
        doc.line("LV_BUSBAR", cls.RAIL_X_L, dy(62.0), cls.RAIL_X_L, dy(total_h - 22.0))
        doc.line("LV_BUSBAR", cls.RAIL_X_R, dy(62.0), cls.RAIL_X_R, dy(total_h - 22.0))
        doc.text("LV_TEXT_TAGS", cls.RAIL_X_L - 14.0, dy(62.0), 4.0, "L+")
        doc.text("LV_TEXT_TAGS", cls.RAIL_X_R + 8.0, dy(62.0), 4.0, "M")

        y = 64.0
        for kind, title, wno, color, rungs in specs:
            if kind == "common":
                doc.rect("LV_WIRING_DUCT", 24.0, dy(y - 16.0), 976.0, dy(y + 114.0))
                doc.text("LV_TEXT_TAGS", 32.0, dy(y - 6.0), 5.0, title)
                y += 22
                cls._draw_rung(doc, rungs[0], wno, y, total_h)
                y += 52
                cls._draw_rung(doc, rungs[1], wno, y, total_h)
                y += 56
            else:
                block_h = 52.0 * len(rungs) + 30.0
                doc.rect("LV_WIRING_DUCT", 24.0, dy(y - 14.0), 976.0, dy(y + block_h - 14.0))
                doc.text("LV_TEXT_TAGS", 32.0, dy(y - 6.0), 5.0, title)
                y += 20
                for rung in rungs:
                    cls._draw_rung(doc, rung, wno, y, total_h)
                    y += 52
                y += 12

        doc.text("LV_TEXT_TAGS", 30.0, dy(y + 10.0), 4.0,
                 f"Wires: {len(wires_all)} | Scale 1:1 (mm) | IEC 60617 Symbols | LV-PanelAssist")
        cls._add_dimensions(doc, total_h)
        return doc.render()

    @classmethod
    def _draw_rung(cls, doc: _DxfDoc, devices: List[Tuple[str, str, str]], wno: str, y: float, total_h: float) -> None:
        def dy(svg_y: float) -> float:
            return total_h - svg_y

        ry = dy(y)
        doc.text("LV_TEXT_TAGS", cls.RAIL_X_L + 12.0, ry + 3.0, 3.0, wno)

        n = len(devices)
        span = cls.RAIL_X_R - cls.RAIL_X_L - 100.0
        wire_start_x = cls.RAIL_X_L

        for i, (tag, terms, kind) in enumerate(devices):
            cx = cls.RAIL_X_L + 70.0 + span * (i + 0.5) / max(n, 1)
            pin_l, pin_r = cls._draw_iec60617_symbol(doc, kind, cx, ry)

            # ترسیم سیم فقط از نقطه قبلی تا پین چپ تجهیز (عدم عبور خط از روی نماد و متون)
            if pin_l > wire_start_x:
                doc.line("LV_WIRES", wire_start_x, ry, pin_l, ry)
            wire_start_x = pin_r

            # درج تگ تجهیز در بالای نماد و شماره ترمینال‌ها در پایین نماد با تراز دقیق مرکزی
            doc.text("LV_TEXT_TAGS", cx, ry + 11.5, 3.2, tag, center=True)
            doc.text("LV_TEXT_TAGS", cx, ry - 12.5, 2.5, terms, center=True)

        # اتصال پین راست آخرین تجهیز به شینه M در سمت راست
        if wire_start_x < cls.RAIL_X_R:
            doc.line("LV_WIRES", wire_start_x, ry, cls.RAIL_X_R, ry)

    @classmethod
    def export_file(cls, filepath: str, project: ProjectSpec, feeders: List[FeederCalcOutput], summary: PanelSummaryOutput) -> None:
        with open(filepath, "w", encoding="ascii", errors="replace") as fh:
            fh.write(cls.generate(project, feeders, summary))