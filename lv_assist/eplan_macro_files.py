# -*- coding: utf-8 -*-
"""فاز ۹: تولید ماکروهای واقعی EPLAN P8 (.ema) — کتابخانهٔ نقطهٔ اتصال (interruption point).

فایل‌های .ema ساختار PXF (EPLAN eXchange Format) دارند: XML ساده با ریشهٔ EplanPxfRoot.
این ماژول بر اساس الگوهای تأییدشدهٔ فایل‌های واقعی EPLAN (نسخه‌های 1.9 تا 2.7) کار می‌کند:
- O4  = صفحهٔ ماکرو (پنجره)
- O70 = نقطهٔ اتصال دستگاه (DT از طریق P144/P150 با شناسهٔ 20013،
        شمارهٔ قطعه 20100 و متن عملکرد 20011 در P11)
- O30 = پتانسیل نام‌گذاری‌شده (ریل)، O31 = اتصال پتانسیل (خط ریل)
- O37 = قاب ماکرو (macro box) با ارجاع S109x692 به همهٔ فرزندان

محدودیت صادقانه: سیمبل‌های گرافیکی (O17) با کدهای عددی داخلی EPLAN ذخیره می‌شوند و از
بیرون قابل بازتولید نیستند؛ به همین دلیل دستگاه‌ها به‌صورت نقطهٔ اتصال تولید می‌شوند —
روش استاندارد EPLAN (Insert > Interruption point). DT و شمارهٔ قطعه و متن عملکرد،
دادهٔ واقعی پروژه است و پس از درگ‌اند‌دراپ ماکرو در پروژه حاضر است.
"""
import os
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from lv_assist.eplan_macro import EplanMacroExporter, MOTOR_TYPES
from lv_assist.models import FeederCalcOutput, LoadType, PanelSummaryOutput, ProjectSpec

Row = Tuple[str, str, str, str, str, float, float]

VERSION = "2.4.8366"
PXF_VERSION = "1.23"
SCHEMA_VERSION = "1.7.8366"
BUILD = "8366"

CONTROL_FILES = {
    LoadType.MOTOR_DOL: "LV_Control_DOL",
    LoadType.MOTOR_STAR_DELTA: "LV_Control_StarDelta",
    LoadType.MOTOR_SOFT_STARTER: "LV_Control_SoftStarter",
    LoadType.MOTOR_VFD: "LV_Control_VFD",
}

# نام عناصر مجاز در خروجی — فقط الگوهای تأییدشده از نمونه‌های واقعی EPLAN.
ELEMENT_WHITELIST = frozenset({
    "EplanPxfRoot", "MacroVariant", "O4", "O70", "O30", "O31", "O37",
    "P11", "P144", "P150", "S40x1201", "S39x761", "S53x5", "S54x505",
    "S109x692", "S89x5", "EplPxfDir", "EplPxfDirEntry", "ESymLib",
    "O14", "O6", "P49",
})


def _fmt(value) -> str:
    if isinstance(value, float):
        return "%g" % value
    return str(value)


def _el(tag: str, attrs: Dict[str, object]) -> ET.Element:
    return ET.Element(tag, {k: _fmt(v) for k, v in attrs.items()})


def _sub(parent: ET.Element, tag: str, attrs: Dict[str, object]) -> ET.Element:
    child = _el(tag, attrs)
    parent.append(child)
    return child


# ---------------------------------------------------------------- بلوک‌های سازنده
def _o4(ts: int) -> ET.Element:
    """صفحهٔ ماکرو — کپی عینی از O4 در 3pol.ema"""
    return _el("O4", {
        "A1": "4/1", "A3": "0", "A13": "0", "A14": "0", "A47": "1",
        "A48": ts, "A50": "0", "A59": "1", "A404": "1", "A405": "64",
        "A406": "0", "A431": "1", "A1101": "", "A1102": "",
    })


def _o70(obj_id: str, row: Row) -> ET.Element:
    """نقطهٔ اتصال سه‌قطبی — کپی عینی از O70 در 3pol.ema با دادهٔ واقعی پروژه."""
    page, tag, kind, part, text, x, y = row
    o70 = _el("O70", {
        "A1": obj_id, "A3": "3", "A13": "0", "A14": "0", "A141": "40",
        "A142": "8", "A145": "<20013>", "A148": "1", "A404": "5",
        "A405": "64", "A406": "0", "A792": "-128", "A793": "0",
        "A1101": "", "A1102": "", "A1261": "0", "A1262": "8",
        "A1263": "0", "A1301": "100", "A1302": "1",
    })
    pos = _sub(o70, "S40x1201", {"A762": "%s/%s" % (_fmt(x), _fmt(y))})
    _sub(pos, "S39x761", {"A751": "1", "A752": "0", "A753": "0", "A754": "1"})
    _sub(o70, "P144", {"P20013": tag})
    _sub(o70, "P150", {"P20013": tag})
    if text or part:
        p11 = {"P20011": text}
        if part:
            p11.update({"P20100_1": part, "P20101_1": "1", "P20102_1": "1"})
        _sub(o70, "P11", p11)
    poles = [
        (1, "403", "2/1.5", "64", "20010", None, "4"),
        (2, "442", "-2/1.5", "68", "24350", None, "6"),
        (3, "442", "-6.5/0", "66", "24300", obj_id + "/2", "6"),
    ]
    for nr, a411, a501, a503, a771, a502, a966 in poles:
        attrs = {
            "A3": "0", "A4": str(nr), "R7": obj_id, "A13": "0", "A14": "0",
            "A404": "1", "A405": "64", "A406": "0", "A411": a411,
            "A412": "L", "A413": "L", "A414": "L", "A415": "L", "A416": "0",
            "A501": a501, "A503": a503, "A504": "0", "A506": "0",
            "A771": a771, "A772": "0", "A773": "0", "A774": "0",
            "A951": "15", "A952": "0", "A953": "0", "A954": "0",
        }
        if a502:
            attrs["A502"] = a502
        pole = _sub(o70, "S53x5", attrs)
        _sub(pole, "S54x505", {
            "A961": "L", "A962": "0", "A963": "0", "A964": "L", "A965": "0",
            "A966": a966, "A967": "0", "A968": "0", "A969": "0",
            "A4000": "L", "A4001": "L",
        })
    return o70


def _o30(obj_id: str, name: str, x: float, y: float) -> ET.Element:
    """پتانسیل نام‌گذاری‌شده — کپی عینی از O30 در DIP.ema"""
    o30 = _el("O30", {
        "Build": BUILD, "A1": obj_id, "A3": "0", "A13": "0", "A14": "0",
        "A404": "1", "A405": "64", "A406": "0", "A407": "0", "A411": "108",
        "A412": "L", "A413": "L", "A414": "L", "A415": "L", "A416": "0",
        "A501": "%s/%s" % (_fmt(x), _fmt(y)), "A503": "0", "A506": "0",
        "A511": "??_??@%s;" % name,
    })
    _sub(o30, "S54x505", {
        "A961": name, "A962": "L", "A963": "0", "A964": "L", "A965": "2048",
        "A966": "6", "A967": "0", "A968": "0", "A969": "1",
        "A4000": "L", "A4001": "L", "A4013": "0",
    })
    return o30


def _o31(obj_id: str, x1: float, y1: float, x2: float, y2: float) -> ET.Element:
    """اتصال پتانسیل (خط ریل) — کپی عینی از O31 در DIP.ema"""
    return _el("O31", {
        "Build": BUILD, "A1": obj_id, "A3": "0", "A13": "0", "A14": "0",
        "A404": "1", "A405": "64", "A406": "0", "A407": "0", "A411": "100",
        "A412": "L", "A413": "L", "A414": "0.13", "A415": "L", "A416": "0",
        "A531": "%s/%s" % (_fmt(x1), _fmt(y1)),
        "A532": "%s/%s" % (_fmt(x2), _fmt(y2)),
    })


def _o37(box_id: str, child_ids: List[str], pos: Tuple[float, float],
         dims: Tuple[str, str]) -> ET.Element:
    """قاب ماکرو — کپی عینی از O37 در DIP.ema"""
    a1631, a1632 = dims
    o37 = _el("O37", {
        "Build": BUILD, "A1": box_id, "A3": "1", "A13": "0", "A14": "0",
        "A404": "1", "A405": "64", "A406": "0", "A407": "0", "A682": "1",
        "A683": ";".join(child_ids), "A684": "0", "A687": "8", "A688": "2",
        "A689": "-1", "A690": "-1", "A691": "0", "A693": "1", "A792": "0",
        "A793": "0", "A794": "0", "A1261": "0", "A1262": "44", "A1263": "0",
        "A1631": a1631, "A1632": a1632,
    })
    for cid in child_ids:
        _sub(o37, "S109x692", {"Build": BUILD, "A3": "0", "A13": "0",
                               "A14": "0", "R1906": cid})
    pos_el = _sub(o37, "S40x1201",
                  {"A762": "%s/%s" % (_fmt(pos[0]), _fmt(pos[1]))})
    _sub(pos_el, "S39x761", {"A751": "1", "A752": "0", "A753": "0", "A754": "1"})
    _sub(o37, "S89x5", {
        "Build": BUILD, "A3": "0", "A4": "1", "R7": box_id, "A13": "0",
        "A14": "0", "A404": "9", "A405": "64", "A406": "0", "A411": "308",
        "A412": "L", "A413": "L", "A414": "L", "A415": "L", "A416": "0",
        "A1651": a1631, "A1652": a1632, "A1653": "0", "A1654": "0",
        "A1655": "0", "A1656": "0", "A1657": "0",
    })
    return o37


# ------------------------------------------------------------------- ساخت ماکرو
def _build_macro(name: str, description: str, potential_names: List[str],
                 rows: List[Row]) -> str:
    """ساخت متن XML یک فایل .ema از ردیف‌های دستگاه."""
    root = _el("EplanPxfRoot", {
        "Name": name, "Type": "WindowMacro", "Version": VERSION,
        "PxfVersion": PXF_VERSION, "SchemaVersion": SCHEMA_VERSION,
        "Source": "", "SourceProject": "", "Description": description,
        "ConfigurationFlags": "0", "NumMainObjects": "0",
        "NumProjectSteps": "0", "NumMDSteps": "0",
        "Custompagescaleused": "true",
    })

    xs = [r[5] for r in rows]
    ys = [r[6] for r in rows]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    ref = "%s/%s/0" % (_fmt(min_x), _fmt(min_y))
    sel = "%s/%s/%s/%s" % (_fmt(min_x - 8), _fmt(max_y + 16),
                           _fmt(max_x + 8), _fmt(min_y - 8))
    variant = _sub(root, "MacroVariant", {
        "MacroFuncType": "1", "VariantId": "0", "ReferencePoint": ref,
        "Version": VERSION, "PxfVersion": PXF_VERSION,
        "SchemaVersion": SCHEMA_VERSION, "Source": "", "SourceProject": "",
        "Description": "", "ConfigurationFlags": "0", "DocumentType": "1",
        "SelectionArea": sel, "Customgost": "0",
    })
    page = _o4(int(time.time()))
    variant.append(page)

    child_ids: List[str] = []
    n30 = n31 = n70 = 0

    rail_x = min_x - 24.0
    top_y, bottom_y = max_y + 6.0, min_y - 6.0
    for name in potential_names:
        n30 += 1
        page.append(_o30("30/%d" % n30, name, rail_x, top_y + 3.0))
        child_ids.append("30/%d" % n30)
        n31 += 1
        page.append(_o31("31/%d" % n31, rail_x, top_y, rail_x, bottom_y))
        child_ids.append("31/%d" % n31)
        rail_x += 8.0

    for row in rows:
        n70 += 1
        page.append(_o70("70/%d" % n70, row))
        child_ids.append("70/%d" % n70)

    box_pos = (min_x - 4.0, max_y + 8.0)
    dims = ("0/-16", "%s/%s" % (_fmt(max_x - min_x + 12.0),
                                _fmt(min_y - max_y + 16.0)))
    page.append(_o37("37/1", child_ids, box_pos, dims))

    body = ET.tostring(root, encoding="unicode")
    if hasattr(ET, "indent"):
        ET.indent(root, space="  ")
        body = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" ?>\n' + body + "\n"


# ------------------------------------------------------------------------ خروجی
class EplanMacroFileExporter:
    """تولید کتابخانهٔ ماکرو .ema از نتایج محاسبات LV-PanelAssist."""

    SLD_NAME = "LV_SLD_Main"
    PSU_NAME = "LV_Control_PSU"
    SLD_POTENTIALS = ["L1", "L2", "L3", "N", "PE"]
    CONTROL_POTENTIALS = ["L+", "M"]

    @classmethod
    def _rows_by_group(cls, project: ProjectSpec, feeders: List[FeederCalcOutput],
                       summary: PanelSummaryOutput):
        rows = EplanMacroExporter._devices(project, feeders, summary)
        page_type: Dict[str, LoadType] = {}
        for idx, f in enumerate(feeders, start=1):
            if f.load_type in MOTOR_TYPES:
                page_type["1%02d" % idx] = f.load_type

        groups: List[Tuple[str, List[str], List[Row]]] = [
            (cls.SLD_NAME, cls.SLD_POTENTIALS,
             [r for r in rows if r[0] == EplanMacroExporter.SLD_PAGE]),
            (cls.PSU_NAME, cls.CONTROL_POTENTIALS,
             [r for r in rows if r[0] == EplanMacroExporter.COMMON_PAGE]),
        ]
        for load_type, fname in CONTROL_FILES.items():
            type_rows = [r for r in rows if page_type.get(r[0]) == load_type]
            if not type_rows:
                continue
            order: Dict[str, int] = {}
            offset_rows: List[Row] = []
            for r in type_rows:
                if r[0] not in order:
                    order[r[0]] = len(order) + 1
                k = order[r[0]]
                offset_rows.append((r[0], r[1], r[2], r[3], r[4], r[5],
                                    r[6] - (k - 1) * 80.0))
            groups.append((fname, cls.CONTROL_POTENTIALS, offset_rows))
        return groups

    @classmethod
    def export_library(cls, folder: str, project: ProjectSpec,
                       feeders: List[FeederCalcOutput],
                       summary: PanelSummaryOutput) -> List[str]:
        """نوشتن همهٔ فایل‌های .ema در پوشهٔ خروجی و برگرداندن مسیرهای نوشته‌شده."""
        os.makedirs(folder, exist_ok=True)
        written: List[str] = []
        for name, potentials, rows in cls._rows_by_group(project, feeders, summary):
            if not rows:
                continue
            xml_text = _build_macro(
                name, "LV-PanelAssist - %s (interruption points)" % name,
                potentials, rows)
            path = os.path.join(folder, name + ".ema")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(xml_text)
            written.append(path)
        return written


# ====================================================== فاز ۱۰: ماکرو صفحه .emp
# ساختار تأییدشده از نمونه واقعی EPLAN 2024 (macroGıdaSogutma.emp):
# ریشه EplanPxfRoot با Type="PageMacro" و StreamSchema؛ EplPxfDir/EplPxfDirEntry؛
# MacroVariant بدون ویژگی حاوی ESymLibها و O14 (سربرگ پروژه) و O6 (گروه‌های ساختار)
# و O4 (صفحه)؛ صفحه مدار A47="1" با A699/A700 و نام صفحه در A1101 و P49 (P11012).
# دستگاه‌ها به‌سبک نمونه 2024 نقطه اتصال تک‌تک‌قطبی O70 با P20013 (DT) و P20014
# (شماره پل) هستند؛ پتانسیل‌ها جفت چپ/راست (A792=9 منبع / 0 هدف) مانند صفحه‌های واقعی.
# سیمبل O17 با کد عددی داخلی EPLAN از بیرون بازتولیدشدنی نیست (محدودیت فاز ۹).

EMP_VERSION = "2024.0.21408"
EMP_PXF_VERSION = "1.23"
EMP_SCHEMA_VERSION = "1.7.21408"
EMP_BUILD = "21408"
EMP_CONFIGURATION_FLAGS = "74241"

# StreamSchema عینی از نمونه 2024 — فهرست کلاس‌های استریم PXF.
STREAM_SCHEMA = (
    "EBitmap, ,2,1,2;EPosition3D, ,0,3,2;ERay3D, ,0,4,2;EStreamableVector, ,0,5,2;"
    "BaseTextLine@W3D, ,2,9,2;Box3d@W3D, ,0,10,2;DMNCDataSet, ,1,12,2;"
    "DMNCDataSetVector, ,1,13,2;Linetype@W3D, ,0,15,2;Color@W3D, ,0,16,2;"
    "Material@W3D, ,3,17,2;Mesh3d@W3D, ,8,19,2;Mesh3dX@W3D, ,2,20,2;"
    "MeshBox@W3D, ,5,21,2;MeshEdge3d@W3D, ,0,22,2;MeshFace3d@W3D, ,2,23,2;"
    "MeshPoint3d@W3D, ,1,24,2;MeshPolygon3d@W3D, ,1,25,2;"
    "MeshSimpleTextureTriangle3d@W3D, ,2,26,2;MeshSimpleTriangle3d@W3D, ,1,27,2;"
    "MeshText3dX@W3D, ,0,28,2;MeshTriangle3d@W3D, ,2,29,2;"
    "MeshTriangleFace3d@W3D, ,0,30,2;MeshTriangleFaceEdge3D@W3D, ,0,31,2;"
    "CTexture@W3D,W3dBaseGeometry,0,37,2;MeshMate@W3D,W3dMeshModeller,7,38,2;"
    "MeshMateFace@W3D,W3dMeshModeller,1,39,2;MeshMateGrid@W3D,W3dMeshModeller,8,40,2;"
    "MeshMateGridLine@W3D,W3dMeshModeller,1,41,2;"
    "MeshMateLine@W3D,W3dMeshModeller,1,42,2"
)

# دستگاه‌های سه‌قطبی (سه نقطه اتصال با P20014=1..3) — بقیه تک‌قطبی.
THREE_POLE_KINDS = frozenset({"BREAKER", "FUSE", "CONTACTOR_COIL", "VFD", "DEVICE"})

# ریل‌های پتانسیل صفحه به‌سبک نمونه 2024: (نام، شماره پل یا None، y)
POWER_RAILS = [("L", 1, 272.0), ("L", 2, 264.0), ("L", 3, 256.0),
               ("N", None, 248.0), ("PE", None, 240.0)]
CONTROL_RAILS = [("L+", None, 268.0), ("M", None, 260.0)]
RAIL_LEFT_X = 28.0
RAIL_RIGHT_X = 392.0

_O14_P11_BASE = {
    "P10000": "LV_PANELASSIST",
    "P10002": "<1100><1101><1102><1103><1104><1105><1106><1107><1108><1109>",
    "P10004": "<1200><1201><1202><1203><1204><1205><1206><1207><1208><1209>",
    "P10006": "<1500>",
    "P10012": "0",
    "P10013": "LV_PANELASSIST",
    "P10014": "de_DE@EPLAN;en_US@EPLAN;",
    "P10018": "16\t==\t.\t=\t.\t++\t.\t+\t.\t\t\t&\t\t#\t#\t-\t-",
    "P10019": "16\t1\t1\t1\t1\t1\t1\t1\t1\t0\t0\t0\t0\t1\t0\t1\t0",
    "P10020": "LVAssist",
    "P10029": "4\t0\t0\t0\t0",
    "P10034": "de_DE@keine;en_US@None;",
    "P10050": "<10002><10004><10006><11012><11013>",
    "P10051": "<10002><20012><20013><20014><20015>",
    "P10072": "21408",
    "P10902": "1",
    "P10904": "0",
}


def _emp_o14(ts: int) -> ET.Element:
    """سربرگ پروژه — کپی عینی O14 از نمونه 2024 با مقادیر خنثی‌شده."""
    p11 = dict(_O14_P11_BASE)
    p11["P10021"] = ts
    o14 = _el("O14", {
        "Build": EMP_BUILD, "A1": "14/1", "A3": "0", "A13": "0", "A14": "0",
        "A133": "LV_PANELASSIST@%d" % ts, "A134": "2024.0.3.21408",
        "A135": "1",
    })
    _sub(o14, "P11", p11)
    return o14


def _emp_o6(a1: str, build: str, a81: str, a85: str) -> ET.Element:
    """گروه ساختار — کپی عینی O6 از نمونه 2024."""
    return _el("O6", {
        "Build": build, "A1": a1, "A3": "0", "A13": "0", "A14": "0",
        "A81": a81, "A82": "", "A83": "0", "A85": a85, "A86": "",
        "A4049": "0",
    })


def _emp_o4(page_name: str, description: str, ts: int) -> ET.Element:
    """صفحه ماکرو مدار — کپی عینی O4 از نمونه 2024 (A47="1" صفحه مدار)."""
    o4 = _el("O4", {
        "Build": EMP_BUILD, "A1": "4/1", "A3": "0", "A13": "0", "A14": "0",
        "A47": "1", "A48": ts, "A50": "0", "A59": "1", "A404": "1",
        "A405": "64", "A406": "0", "A407": "0", "A431": "1",
        "A699": "00000000000000000000000000000000",
        "A700": "00000000-0000-0000-0000-000000000000",
        "A1101": page_name, "A1102": "", "A1103": "", "A4043": "0",
        "A4049": "0",
    })
    _sub(o4, "P11", {
        "P10185": "LVASSIST01", "P11006": "0",
        "P11011": "??_??@%s;" % description,
        "P11020": "LVAssist", "P11021": ts, "P11022": "LVAssist",
        "P11024": ts, "P11037": "0", "P11048": "1", "P11050": "0",
        "P11051": "4",
    })
    _sub(o4, "P49", {"P11012": page_name})
    return o4


def _emp_o70_device(obj_id: str, tag: str, pole: Optional[int], x: float,
                    y: float, part: str, text: str) -> ET.Element:
    """نقطه اتصال دستگاه تک‌قطبی به‌سبک 2024؛ pole=None یعنی تک‌قطبی."""
    o70 = _el("O70", {
        "Build": EMP_BUILD, "A1": obj_id, "A3": "0", "A13": "0", "A14": "0",
        "A145": "<20013>" if pole is None else "<20013><20014>",
        "A148": "1", "A404": "5", "A405": "64", "A406": "0", "A407": "0",
        "A792": "9", "A793": "0", "A794": "0", "A1261": "0", "A1262": "8",
        "A1263": "0", "A1301": "100", "A4049": "0",
    })
    pos = _sub(o70, "S40x1201", {"A762": "%s/%s" % (_fmt(x), _fmt(y))})
    _sub(pos, "S39x761", {"A751": "1", "A752": "0", "A753": "0", "A754": "1"})
    p144 = {"P20013": tag}
    if pole is not None:
        p144["P20014"] = str(pole)
    _sub(o70, "P144", dict(p144))
    _sub(o70, "P150", dict(p144))
    if text or part:
        p11 = {"P20011": text}
        if part:
            p11.update({"P20100_1": part, "P20101_1": "1", "P20102_1": "1"})
        _sub(o70, "P11", p11)
    return o70


def _emp_o70_potential(obj_id: str, name: str, pole: Optional[int], x: float,
                       y: float, source: bool) -> ET.Element:
    """نقطه اتصال پتانسیل به‌سبک نمونه 2024 (منبع چپ A792=9، هدف راست A792=0)."""
    is_l = pole is not None
    o70 = _el("O70", {
        "Build": EMP_BUILD, "A1": obj_id, "A3": "0", "A13": "0", "A14": "0",
        "A145": "<20012><20013><20014>" if is_l else "<20013>",
        "A148": "1", "A404": "5", "A405": "64", "A406": "0", "A407": "0",
        "A792": "9" if source else "0", "A793": "0", "A794": "0",
        "A1261": "0", "A1262": "8", "A1263": "0", "A1301": "100",
        "A4049": "0",
    })
    pos = _sub(o70, "S40x1201", {"A762": "%s/%s" % (_fmt(x), _fmt(y))})
    _sub(pos, "S39x761", {"A751": "1", "A752": "0", "A753": "0", "A754": "1"})
    p144 = {"P20013": name}
    if is_l:
        p144.update({"P20012": "2", "P20014": str(pole)})
    _sub(o70, "P144", dict(p144))
    _sub(o70, "P150", dict(p144))
    return o70


def _build_page_macro(name: str, description: str, page_name: str,
                      rails: List[Tuple[str, Optional[int], float]],
                      rows: List[Row], ts: int) -> str:
    """ساخت متن XML یک فایل .emp از ردیف‌های دستگاه (الگوی تأییدشده 2024)."""
    root = _el("EplanPxfRoot", {
        "Name": name, "Type": "PageMacro", "Version": EMP_VERSION,
        "PxfVersion": EMP_PXF_VERSION, "SchemaVersion": EMP_SCHEMA_VERSION,
        "Source": "", "SourceProject": "", "Description": description,
        "ConfigurationFlags": EMP_CONFIGURATION_FLAGS,
        "NumMainObjects": "1", "NumProjectSteps": "1", "NumMDSteps": "0",
        "Customgost": "0", "StreamSchema": STREAM_SCHEMA,
    })
    pxf_dir = _sub(root, "EplPxfDir", {})
    _sub(pxf_dir, "EplPxfDirEntry", {"MacroFuncType": "-1", "VariantId": "-1"})

    variant = _sub(root, "MacroVariant", {})
    for lib_name, lib_id in (("SPECIAL", "0"), ("IEC_symbol", "1"),
                             ("IEC_single_symbol", "2"), ("GRAPHICS", "3"),
                             ("OS_SYM_ESS", "4")):
        _sub(variant, "ESymLib", {"Name": lib_name, "ID": lib_id})
    variant.append(_emp_o14(ts))
    variant.append(_emp_o6("6/1", "10354", "1100", "10002"))
    variant.append(_emp_o6("6/2", "10354", "1200", "10004"))
    variant.append(_emp_o6("6/3", "9205", "1500", "10006"))

    page = _emp_o4(page_name, description, ts)
    variant.append(page)

    n70 = 0
    for rail_name, pole, ry in rails:
        for source, rx in ((True, RAIL_LEFT_X), (False, RAIL_RIGHT_X)):
            n70 += 1
            page.append(_emp_o70_potential("70/%d" % n70, rail_name, pole,
                                           rx, ry, source))
    for row in rows:
        tag, kind, part, text = row[1], row[2], row[3], row[4]
        x, y = row[5], row[6]
        if kind in THREE_POLE_KINDS:
            for k, pole in enumerate((1, 2, 3)):
                n70 += 1
                page.append(_emp_o70_device(
                    "70/%d" % n70, tag, pole, x, y - (k * 8.0),
                    part if pole == 1 else "", text if pole == 1 else ""))
        else:
            n70 += 1
            page.append(_emp_o70_device("70/%d" % n70, tag, None, x, y,
                                        part, text))

    body = ET.tostring(root, encoding="unicode")
    if hasattr(ET, "indent"):
        ET.indent(root, space="  ")
        body = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="utf-8" ?>\n' + body + "\n"


class EplanPageMacroExporter:
    """تولید کتابخانه ماکرو صفحه .emp از نتایج محاسبات LV-PanelAssist (فاز ۱۰)."""

    SLD_NAME = "LV_SLD_Main"
    PSU_NAME = "LV_Control_PSU"

    @classmethod
    def _groups(cls, project: ProjectSpec, feeders: List[FeederCalcOutput],
                summary: PanelSummaryOutput):
        groups = EplanMacroFileExporter._rows_by_group(project, feeders, summary)
        out = []
        for name, _potentials, rows in groups:
            if not rows:
                continue
            rails = POWER_RAILS if name == cls.SLD_NAME else CONTROL_RAILS
            out.append((name, rows[0][0], rails, rows))
        return out

    @classmethod
    def export_library(cls, folder: str, project: ProjectSpec,
                       feeders: List[FeederCalcOutput],
                       summary: PanelSummaryOutput,
                       ts: Optional[int] = None) -> List[str]:
        """نوشتن همه فایل‌های .emp در پوشه خروجی و برگرداندن مسیرهای نوشته‌شده."""
        os.makedirs(folder, exist_ok=True)
        if ts is None:
            ts = int(time.time())
        written: List[str] = []
        for name, page_name, rails, rows in cls._groups(project, feeders, summary):
            xml_text = _build_page_macro(
                name, "LV-PanelAssist - %s (page macro)" % name,
                page_name, rails, rows, ts)
            path = os.path.join(folder, name + ".emp")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(xml_text)
            written.append(path)
        return written
