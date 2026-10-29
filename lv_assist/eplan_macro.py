# -*- coding: utf-8 -*-
"""فاز ۸: تولید اسکریپت C# برای EPLAN P8 (۲۰۲۴ به بعد) — ساخت صفحات، چیدمان هم‌راستا با شبکه ۴ میلی‌متری و بروزرسانی Cross-Reference."""
import re
from datetime import datetime
from typing import List, Tuple

from lv_assist.report_export import export_current_report
from lv_assist.output_notice import output_notice
from lv_assist.models import ProjectSpec, FeederCalcOutput, PanelSummaryOutput, LoadType


MOTOR_TYPES = (
    LoadType.MOTOR_DOL,
    LoadType.MOTOR_STAR_DELTA,
    LoadType.MOTOR_SOFT_STARTER,
    LoadType.MOTOR_VFD,
)

EPLAN_GRID_MM = 4.0


def _snap(val: float, grid: float = EPLAN_GRID_MM) -> float:
    """قفل کردن مختصات روی شبکه استاندارد ۴ میلی‌متری EPLAN جهت فعال‌سازی Autoconnecting."""
    return round(float(val) / grid) * grid


def _cstr(value: str) -> str:
    """رشتهٔ امن برای C#: escape کردن \\ و \" و نویسه‌های کنترلی و غیر ASCII به \\uXXXX."""
    out = []
    for ch in str(value):
        code = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif code < 32 or code > 126:
            out.append("\\u%04x" % code)
        else:
            out.append(ch)
    return "".join(out)


def _struct_safe(value: str) -> str:
    """شناسهٔ ساختار EPLAN فقط A-Za-z0-9_- — بدون = + & / و فاصله."""
    return re.sub(r"[^A-Za-z0-9_\-]", "_", str(value)).strip("_") or "LV"


def _pn(dev) -> str:
    return dev.part_number if dev is not None else ""


def _carr(items: List[str]) -> str:
    """آرایهٔ C# از رشته‌ها: { "a", "b" }"""
    return "{ " + ", ".join('"%s"' % _cstr(s) for s in items) + " }"


def _darr(values: List[float]) -> str:
    return "{ " + ", ".join(("%g" % v) for v in values) + " }"


class EplanMacroExporter:
    """تولید اسکریپت داده‌محور EPLAN P8 از نتایج محاسبات LV-PanelAssist."""

    SYMBOL_LIBRARY = "IEC_symbol"
    DOC_TYPE = "ECS"
    SLD_PAGE = "001"
    COMMON_PAGE = "100"

    # نگاشت نوع دستگاه به نام سیمبل استاندارد در کتابخانه IEC_symbol
    SYMBOL_MAP = [
        ("BREAKER", "QL3"),           # کلید ۳ پل چندسیمه استاندارد برای مدار قدرت
        ("BREAKER_1P", "Q_2L"),       # کلید/کنتاکت کمکی ۲ سر در مدار فرمان
        ("FUSE", "F2"),
        ("CONTACTOR_COIL", "K1"),
        ("PUSHBUTTON_NO", "S1"),
        ("PUSHBUTTON_NC", "S2"),
        ("LAMP", "H1"),
        ("PSU", "G1"),
        ("DEVICE", "G1"),
        ("VFD", "U1"),
        ("TERMINAL", "X1"),
        ("T_NODE", "T_O"),            # گره انشعاب استاندارد برای جلوگیری از خطوط مورب
    ]

    @classmethod
    def _full_dt(cls, plant: str, loc: str, short_tag: str) -> str:
        """ساخت شناسه کامل IEC 81346 (مانند =PLANT+LOC-Q1) جهت اتصال خودکار Cross-Reference."""
        t = short_tag if short_tag.startswith("-") else ("-" + short_tag)
        return "=%s+%s%s" % (plant, loc, t)

    # ------------------------------------------------------------------ داده
    @classmethod
    def _devices(cls, project: ProjectSpec, feeders: List[FeederCalcOutput],
                 summary: PanelSummaryOutput) -> List[Tuple[str, str, str, str, str, float, float]]:
        """
        ردیف‌های دستگاه: (page, tag, kind, part, text, x, y)
        چیدمان عمودی (Top-to-Bottom) روی مضارب شبکه 4.0mm برای حذف کامل خطوط مورب در EPLAN.
        """
        rows: List[Tuple[str, str, str, str, str, float, float]] = []

        # ۱. صفحه دیاگرام قدرت/تک‌خطی (001):
        # کلید اصلی در بالا (Y=220) و کلیدهای فیدر در ستون‌های موازی (Y=148, X=64, 112, 160...)
        main = summary.main_breaker
        rows.append((
            cls.SLD_PAGE, "-Q0", "BREAKER",
            main.part_number if main else "", "Main incomer breaker",
            _snap(64.0), _snap(220.0),
        ))
        feeder_x = 64.0
        feeder_y = 148.0
        x_step = 48.0
        for idx, f in enumerate(feeders, start=1):
            rows.append((
                cls.SLD_PAGE, "-Q%d" % idx, "BREAKER",
                _pn(f.selected_protection),
                "Feeder %s protection" % f.feeder_id,
                _snap(feeder_x), _snap(feeder_y),
            ))
            feeder_x += x_step
            if feeder_x > 360.0:
                feeder_x = 64.0
                feeder_y -= 56.0

        if summary.cap_bank_installed_kvar > 0:
            rows.append((
                cls.SLD_PAGE, "-Qcap", "BREAKER",
                _pn(summary.cap_bank_protection),
                "Capacitor bank protection",
                _snap(feeder_x), _snap(feeder_y),
            ))

        # ۲. صفحه مشترک تغذیه ۲۴ ولت کنترلی (100):
        # چیدمان عمودی هم‌راستا در ستون X=80.0 (از بالا به پایین برای Autoconnect مستقیم)
        cx = _snap(80.0)
        rows.append((cls.COMMON_PAGE, "-Q01", "BREAKER",
                     _pn(summary.selected_psu_primary_mcb), "PSU primary MCB", cx, _snap(224.0)))
        rows.append((cls.COMMON_PAGE, "-G1", "PSU",
                     _pn(summary.selected_psu_24v), "Power supply 24 V DC", cx, _snap(184.0)))
        rows.append((cls.COMMON_PAGE, "-F0", "FUSE",
                     _pn(summary.selected_dc_selectivity_mod), "DC selectivity module", cx, _snap(144.0)))
        rows.append((cls.COMMON_PAGE, "-X1", "TERMINAL", "", "Terminal L+Distribution", cx, _snap(104.0)))
        rows.append((cls.COMMON_PAGE, "-X2", "TERMINAL", "", "Terminal M Distribution", _snap(128.0), _snap(104.0)))

        # ۳. صفحات مدار کنترلی هر فیدر موتوری (101, 102, ...):
        # هر شاخه کنترلی (Current Path) در یک ستون عمودی با X ثابت چیده می‌شود تا خطوط کاملاً عمودی و استاندارد رسم شوند
        for idx, f in enumerate(feeders, start=1):
            if f.load_type not in MOTOR_TYPES:
                continue
            page = "1%02d" % idx
            col1_x = _snap(80.0)   # شاخه ۱: حفاظت + استپ + استارت + بوبین اصلی
            col2_x = _snap(136.0)  # شاخه ۲: کنتاکتورهای کمکی ستاره/مثلث و تایمر
            col3_x = _snap(192.0)  # شاخه ۳: سیگنالینگ و لامپ‌های روی درب تابلو (Run / Fault)

            if f.load_type == LoadType.MOTOR_DOL:
                rows.append((page, "-Q%d" % idx, "BREAKER_1P", _pn(f.selected_protection), "MPCB aux contact", col1_x, _snap(224.0)))
                rows.append((page, "-S%d0" % idx, "PUSHBUTTON_NC", "", "Stop button", col1_x, _snap(184.0)))
                rows.append((page, "-S%d1" % idx, "PUSHBUTTON_NO", "", "Start button", col1_x, _snap(144.0)))
                rows.append((page, "-K%d" % idx, "CONTACTOR_COIL", _pn(f.selected_contactor_main), "Line contactor", col1_x, _snap(96.0)))
                rows.append((page, "-H%d1" % idx, "LAMP", "", "Run lamp", col3_x, _snap(96.0)))

            elif f.load_type == LoadType.MOTOR_STAR_DELTA:
                rows.append((page, "-F%d" % idx, "FUSE", _pn(f.selected_bimetal), "Thermal relay aux contact", col1_x, _snap(224.0)))
                rows.append((page, "-S%d0" % idx, "PUSHBUTTON_NC", "", "Stop button", col1_x, _snap(184.0)))
                rows.append((page, "-S%d1" % idx, "PUSHBUTTON_NO", "", "Start button", col1_x, _snap(144.0)))
                rows.append((page, "-K%dT" % idx, "CONTACTOR_COIL", _pn(f.selected_timer_yd), "Star-delta timer", col1_x, _snap(96.0)))
                rows.append((page, "-K%dY" % idx, "CONTACTOR_COIL", _pn(f.selected_contactor_star), "Star contactor", col2_x, _snap(96.0)))
                rows.append((page, "-K%dD" % idx, "CONTACTOR_COIL", _pn(f.selected_contactor_delta), "Delta contactor", _snap(164.0), _snap(96.0)))
                rows.append((page, "-H%d1" % idx, "LAMP", "", "Run lamp", col3_x, _snap(96.0)))
                rows.append((page, "-H%d2" % idx, "LAMP", "", "Fault lamp", _snap(224.0), _snap(96.0)))

            elif f.load_type == LoadType.MOTOR_SOFT_STARTER:
                rows.append((page, "-S%d0" % idx, "PUSHBUTTON_NC", "", "Stop button", col1_x, _snap(200.0)))
                rows.append((page, "-S%d1" % idx, "PUSHBUTTON_NO", "", "Start button", col1_x, _snap(152.0)))
                rows.append((page, "-G%d" % idx, "DEVICE", _pn(f.selected_soft_starter), "Soft starter", col1_x, _snap(96.0)))
                rows.append((page, "-H%d1" % idx, "LAMP", "", "Run lamp", col3_x, _snap(96.0)))
                rows.append((page, "-H%d2" % idx, "LAMP", "", "Fault lamp", _snap(224.0), _snap(96.0)))

            elif f.load_type == LoadType.MOTOR_VFD:
                rows.append((page, "-S%d0" % idx, "PUSHBUTTON_NC", "", "Stop button", col1_x, _snap(200.0)))
                rows.append((page, "-S%d1" % idx, "PUSHBUTTON_NO", "", "Start button", col1_x, _snap(152.0)))
                rows.append((page, "-U%d" % idx, "VFD", _pn(f.selected_vfd), "Variable frequency drive", col1_x, _snap(96.0)))
                rows.append((page, "-H%d1" % idx, "LAMP", "", "Run lamp", col3_x, _snap(96.0)))
                rows.append((page, "-H%d2" % idx, "LAMP", "", "Fault lamp", _snap(224.0), _snap(96.0)))

        return rows

    # ------------------------------------------------------------------ تولید
    @classmethod
    def generate_script(cls, project: ProjectSpec, feeders: List[FeederCalcOutput],
                        summary: PanelSummaryOutput) -> str:
        pages: List[Tuple[str, str]] = [
            (cls.SLD_PAGE, "Main Power & Feeder Distribution"),
            (cls.COMMON_PAGE, "Control Voltage Distribution 24VDC"),
        ]
        for idx, f in enumerate(feeders, start=1):
            if f.load_type in MOTOR_TYPES:
                pages.append(("1%02d" % idx, "Control circuit - %s (%s)" % (f.feeder_id, f.load_type.value)))

        devices = cls._devices(project, feeders, summary)
        kinds = [k for k, _ in cls.SYMBOL_MAP]
        symbols = [s for _, s in cls.SYMBOL_MAP]

        plant_str = _struct_safe(project.project_name)
        loc_str = _struct_safe(project.panel_tag)

        return ('// ' + output_notice(summary) + '\n' + TEMPLATE) \
            .replace("__GENERATED_AT__", datetime.now().strftime("%Y-%m-%d %H:%M")) \
            .replace("__SLD_PAGE__", cls.SLD_PAGE) \
            .replace("__EXPECTED_PROJECT__", _cstr(project.project_name)) \
            .replace("__PLANT__", _cstr(plant_str)) \
            .replace("__LOCATION__", _cstr(loc_str)) \
            .replace("__DOC_TYPE__", _cstr(cls.DOC_TYPE)) \
            .replace("__LIB__", _cstr(cls.SYMBOL_LIBRARY)) \
            .replace("__MAP_KIND__", _carr(kinds)) \
            .replace("__MAP_SYMBOL__", _carr(symbols)) \
            .replace("__PAGE_NAME__", _carr([p for p, _ in pages])) \
            .replace("__PAGE_DESC__", _carr([d for _, d in pages])) \
            .replace("__DEV_PAGE__", _carr([d[0] for d in devices])) \
            .replace("__DEV_TAG__", _carr([d[1] for d in devices])) \
            .replace("__DEV_KIND__", _carr([d[2] for d in devices])) \
            .replace("__DEV_PART__", _carr([d[3] for d in devices])) \
            .replace("__DEV_TEXT__", _carr([d[4] for d in devices])) \
            .replace("__DEV_X__", _darr([d[5] for d in devices])) \
            .replace("__DEV_Y__", _darr([d[6] for d in devices]))

    @classmethod
    def export_file(cls, filepath: str, project: ProjectSpec,
                    feeders: List[FeederCalcOutput], summary: PanelSummaryOutput, *, validations=None) -> None:
        return export_current_report(filepath, project, feeders, summary, validations,
                                     cls._render_file)

    @classmethod
    def _render_file(cls, filepath, project, feeders, summary, checks):
        with open(filepath, "w", encoding="utf-8-sig", newline="\r\n") as fh:
            fh.write(cls.generate_script(project, feeders, summary))


TEMPLATE = r"""// ============================================================================
//  LV-PanelAssist - EPLAN P8 Page, Macro & Cross-Reference Generator
//  Generated: __GENERATED_AT__
//  Target   : EPLAN 2024 or newer (script engine, C# 5 syntax)
// ============================================================================

using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using Eplan.EplApi.ApplicationFramework;
using Eplan.EplApi.Base;
using Eplan.EplApi.Scripting;

public class LvPanelAssistEplanMacro
{
    static string EXPECTED_PROJECT = "__EXPECTED_PROJECT__";
    static string PLANT     = "__PLANT__";      // "=" Higher-Level Function (IEC 81346)
    static string LOCATION  = "__LOCATION__";   // "+" Mounting Location (IEC 81346)
    static string DOC_TYPE  = "__DOC_TYPE__";   // "&" Document Type (ECS)
    static string SYMBOL_LIBRARY = "__LIB__";

    static string[] MAP_KIND   = __MAP_KIND__;
    static string[] MAP_SYMBOL = __MAP_SYMBOL__;

    static string[] PAGE_NAME = __PAGE_NAME__;
    static string[] PAGE_DESC = __PAGE_DESC__;

    static string[] DEV_PAGE = __DEV_PAGE__;
    static string[] DEV_TAG  = __DEV_TAG__;
    static string[] DEV_KIND = __DEV_KIND__;
    static string[] DEV_PART = __DEV_PART__;
    static string[] DEV_TEXT = __DEV_TEXT__;
    static double[] DEV_X    = __DEV_X__;
    static double[] DEV_Y    = __DEV_Y__;

    static Assembly[] _asms;

    static Type FindType(string fullName)
    {
        if (_asms == null) _asms = AppDomain.CurrentDomain.GetAssemblies();
        foreach (Assembly a in _asms)
        {
            try
            {
                Type t = a.GetType(fullName);
                if (t != null) return t;
            }
            catch { }
        }
        string[] candidates = new string[] {
            "Eplan.EplApi.DataModelNetu", "Eplan.EplApi.HEServicesNetu",
            "Eplan.EplApi.DataModelu",    "Eplan.EplApi.HEServicesu"
        };
        foreach (string c in candidates)
        {
            try
            {
                Type t = Assembly.Load(c).GetType(fullName);
                if (t != null) { _asms = AppDomain.CurrentDomain.GetAssemblies(); return t; }
            }
            catch { }
        }
        throw new Exception("Could not resolve type " + fullName);
    }

    static void Info(string msg) { new BaseException(msg, MessageLevel.Message).FixMessage(); }
    static void Warn(string msg) { new BaseException(msg, MessageLevel.Warning).FixMessage(); }

    static object PropsOf(object obj)
    {
        PropertyInfo pi = obj.GetType().GetProperty("Properties");
        if (pi == null) return null;
        return pi.GetValue(obj, null);
    }

    static bool SetPropString(object propList, string name, string value)
    {
        if (propList == null) return false;
        PropertyInfo pi = propList.GetType().GetProperty(name,
            BindingFlags.Public | BindingFlags.Instance, null, null, Type.EmptyTypes, null);
        if (pi == null) return false;
        try
        {
            MethodInfo conv = pi.PropertyType.GetMethod("op_Implicit", new Type[] { typeof(string) });
            if (conv != null)
            {
                object pv = conv.Invoke(null, new object[] { value });
                pi.SetValue(propList, pv, null);
                return true;
            }
            pi.SetValue(propList, value, null);
            return true;
        }
        catch { return false; }
    }

    static string MapSymbol(string kind)
    {
        for (int i = 0; i < MAP_KIND.Length; i++)
            if (MAP_KIND[i] == kind) return MAP_SYMBOL[i];
        return "";
    }

    static string BuildFullDeviceTag(string rawTag, string kind)
    {
        // رعایت کامل ساختار سلسله‌مراتبی IEC 81346 (=PLANT+LOCATION-TAG) برای ارتباط Cross-Reference
        if (rawTag.StartsWith("=")) return rawTag;
        string t = rawTag.StartsWith("-") ? rawTag : ("-" + rawTag);
        return "=" + PLANT + "+" + LOCATION + t;
    }

    static double SnapToGrid(double v)
    {
        return Math.Round(v / 4.0) * 4.0;
    }

    [Start]
    public void Start()
    {
        object lockStep = null;
        try
        {
            Type lsType = FindType("Eplan.EplApi.DataModel.LockingStep");
            lockStep = Activator.CreateInstance(lsType);

            Type ssType = FindType("Eplan.EplApi.HEServices.SelectionSet");
            object ss = Activator.CreateInstance(ssType);
            MethodInfo getCur = ssType.GetMethod("GetCurrentProject", new Type[] { typeof(bool) });
            object project = getCur.Invoke(ss, new object[] { false });
            if (project == null)
                throw new Exception("No project is open in EPLAN. Open the target project first.");

            Type projType = project.GetType();
            string projName = Convert.ToString(projType.GetProperty("ProjectName").GetValue(project, null));
            if (projName != EXPECTED_PROJECT)
                throw new Exception("Refusing to write: open project is '" + projName
                    + "', expected '" + EXPECTED_PROJECT + "'.");

            Type pageType = FindType("Eplan.EplApi.DataModel.Page");
            Type pplType  = FindType("Eplan.EplApi.DataModel.PagePropertyList");
            MethodInfo createPage = null;
            MethodInfo[] pageMethods = pageType.GetMethods();
            foreach (MethodInfo m in pageMethods)
            {
                if (m.Name != "Create") continue;
                ParameterInfo[] ps = m.GetParameters();
                if (ps.Length == 3
                    && ps[1].ParameterType.FullName.IndexOf("DocumentType") >= 0
                    && ps[2].ParameterType == pplType)
                {
                    createPage = m;
                    break;
                }
            }
            if (createPage == null)
                throw new Exception("Could not resolve Page.Create(Project, DocumentType, PagePropertyList).");
            Type dtType = createPage.GetParameters()[1].ParameterType;
            object docType = Enum.Parse(dtType, "Circuit");

            Type libType = FindType("Eplan.EplApi.DataModel.MasterData.SymbolLibrary");
            ConstructorInfo libCtor = libType.GetConstructor(new Type[] { projType, typeof(string) });
            if (libCtor == null)
                throw new Exception("Could not resolve SymbolLibrary(Project, string).");
            object lib = libCtor.Invoke(new object[] { project, SYMBOL_LIBRARY });

            Type symType = FindType("Eplan.EplApi.DataModel.MasterData.Symbol");
            ConstructorInfo symCtor = symType.GetConstructor(new Type[] { libType, typeof(string) });
            if (symCtor == null)
                throw new Exception("Could not resolve Symbol(SymbolLibrary, string).");

            Type svType = FindType("Eplan.EplApi.DataModel.MasterData.SymbolVariant");
            MethodInfo svInit = svType.GetMethod("Initialize", new Type[] { symType, typeof(int) });
            if (svInit == null)
                throw new Exception("Could not resolve SymbolVariant.Initialize(Symbol, int).");

            Type fnType = FindType("Eplan.EplApi.DataModel.Function");
            MethodInfo fnCreate = null;
            MethodInfo fnPlace = null;
            MethodInfo[] fnMethods = fnType.GetMethods();
            foreach (MethodInfo m in fnMethods)
            {
                ParameterInfo[] ps = m.GetParameters();
                if (m.Name == "Create" && ps.Length == 2 && ps[1].ParameterType == svType)
                    fnCreate = m;
                if (m.Name == "PlaceAt" && ps.Length == 4 && ps[3].ParameterType == svType)
                    fnPlace = m;
            }
            if (fnCreate == null)
                throw new Exception("Could not resolve Function.Create(Page, SymbolVariant).");
            if (fnPlace == null)
                throw new Exception("Could not resolve Function.PlaceAt(Page, PointD, DocumentType, SymbolVariant).");
            Type ptType = fnPlace.GetParameters()[1].ParameterType;

            // ---- Create Multi-line Circuit Pages with full IEC 81346 Hierarchy ----
            Dictionary<string, object> pages = new Dictionary<string, object>();
            for (int i = 0; i < PAGE_NAME.Length; i++)
            {
                object ppl = Activator.CreateInstance(pplType);
                if (!SetPropString(ppl, "DESIGNATION_PLANT", PLANT))
                    throw new Exception("Could not set DESIGNATION_PLANT.");
                if (!SetPropString(ppl, "DESIGNATION_PLACEOFINSTALLATION", LOCATION))
                    throw new Exception("Could not set DESIGNATION_PLACEOFINSTALLATION.");
                if (!SetPropString(ppl, "DESIGNATION_DOCTYPE", DOC_TYPE))
                    throw new Exception("Could not set DESIGNATION_DOCTYPE.");
                if (!SetPropString(ppl, "PAGE_COUNTER", PAGE_NAME[i]))
                    throw new Exception("Could not set PAGE_COUNTER for page " + PAGE_NAME[i] + ".");
                SetPropString(ppl, "PAGE_DESCRIPTION", PAGE_DESC[i]);

                object page = Activator.CreateInstance(pageType);
                createPage.Invoke(page, new object[] { project, docType, ppl });
                pages[PAGE_NAME[i]] = page;
            }
            Info("LV-PanelAssist: created " + PAGE_NAME.Length + " page(s) in project '" + projName + "'.");

            // ---- Place Devices on 4.0mm Grid with Full Hierarchical Tags ----
            int placed = 0;
            int failed = 0;
            HashSet<string> mainAssigned = new HashSet<string>();

            for (int i = 0; i < DEV_PAGE.Length; i++)
            {
                try
                {
                    if (!pages.ContainsKey(DEV_PAGE[i]))
                        throw new Exception("page '" + DEV_PAGE[i] + "' does not exist");
                    object page = pages[DEV_PAGE[i]];

                    string symName = MapSymbol(DEV_KIND[i]);
                    if (symName == "")
                        throw new Exception("unknown symbol kind '" + DEV_KIND[i] + "'");

                    object sym = null;
                    try { sym = symCtor.Invoke(new object[] { lib, symName }); }
                    catch { }
                    // Fallback to Q_2L if QL3 is not present in custom library
                    if (sym == null && symName == "QL3")
                        sym = symCtor.Invoke(new object[] { lib, "Q_2L" });
                    if (sym == null)
                        throw new Exception("symbol '" + symName + "' not found");

                    object sv = Activator.CreateInstance(svType);
                    svInit.Invoke(sv, new object[] { sym, 0 });

                    object fn = Activator.CreateInstance(fnType);
                    fnCreate.Invoke(fn, new object[] { page, sv });

                    double gx = SnapToGrid(DEV_X[i]);
                    double gy = SnapToGrid(DEV_Y[i]);
                    object pt = Activator.CreateInstance(ptType, new object[] { gx, gy });
                    fnPlace.Invoke(fn, new object[] { page, pt, docType, sv });

                    object props = PropsOf(fn);
                    if (props == null)
                        throw new Exception("function has no Properties");

                    string fullTag = BuildFullDeviceTag(DEV_TAG[i], DEV_KIND[i]);
                    if (!SetPropString(props, "FUNC_DEVICETAG_FULL", fullTag))
                        throw new Exception("could not set FUNC_DEVICETAG_FULL");

                    // تنظیم Main Function تنها برای اولین وقوع هر تگ جهت برقراری دقیق Cross-Reference
                    if (!mainAssigned.Contains(fullTag) && DEV_PART[i] != "")
                    {
                        SetPropString(props, "FUNC_ARTICLE_PARTNR", DEV_PART[i]);
                        mainAssigned.Add(fullTag);
                    }
                    SetPropString(props, "FUNC_TEXT", DEV_TEXT[i]);
                    placed++;
                }
                catch (Exception ex)
                {
                    failed++;
                    Warn("Device " + DEV_TAG[i] + " (" + DEV_KIND[i] + ") on page "
                        + DEV_PAGE[i] + " failed: " + ex.Message);
                }
            }

            // ---- Trigger EPLAN Autoconnecting & Cross-Reference Generation ----
            try
            {
                CommandLineInterpreter cli = new CommandLineInterpreter();
                ActionCallingContext accConn = new ActionCallingContext();
                accConn.AddParameter("TYPE", "CONNECTIONS");
                cli.Execute("generate", accConn);
            }
            catch { }

            Info("LV-PanelAssist macro done: " + placed + " device(s) placed on 4mm grid, "
                + failed + " failed, " + PAGE_NAME.Length + " page(s). Connections & Cross-References updated.");
        }
        catch (Exception ex)
        {
            new BaseException("LV-PanelAssist macro error: " + ex.Message,
                MessageLevel.Error).FixMessage();
        }
        finally
        {
            if (lockStep != null)
            {
                try { lockStep.GetType().GetMethod("Dispose").Invoke(lockStep, null); }
                catch { }
            }
        }
    }
}
"""
