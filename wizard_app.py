# -*- coding: utf-8 -*-
"""
LV-PanelAssist Interactive Step-by-Step Engineering Wizard (v0.6.0-FieldReady)
Features:
  - 6-Step Guided Engineering Wizard (No pre-made Excel required!)
  - Interactive Prompting for Missing Data (cos_phi, efficiency, cable length, catalog items)
  - Full Instrumentation & PLC I/O Builder (Sensors DI/AI, Actuators Solenoid/AO)
  - IEC 81346 Structure Configurator (==, =, ++, +, -)
  - SQLite Catalog & Price Manager + Clear EPLAN P8 Import Guide
"""

import os
import sqlite3
import webbrowser
from typing import List
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk, simpledialog

from lv_assist.models import ProjectSpec, FeederInput, EarthingSystem, LoadType, ValidationStatus
from lv_assist.catalog import CatalogRepository
from lv_assist.engine import EngineeringEngine
from lv_assist.exporters import ExcelExporter, PrintableReportExporter
from lv_assist.field_wizard_engine import (
    AutomationSignalType,
    FieldInstrumentInput,
    IndustrialAutomationEngine,
)


class InteractiveEngineeringWizard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LV-PanelAssist v0.6.0 | ویزارد گام‌به‌گام طراحی تابلو فشار ضعیف، PLC و ابزار دقیق")
        self.geometry("1380x820")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.catalog = CatalogRepository.get_default_catalog()
        self.engine = EngineeringEngine(self.catalog)

        # Clean Field-Ready State (User builds step by step or imports Excel)
        self.feeders_list: List[FeederInput] = []
        self.instruments_list: List[FieldInstrumentInput] = []
        self.last_results = None
        self.last_auto_results = None

        self._build_wizard_layout()

    def _build_wizard_layout(self):
        # Top Wizard Navigation Bar
        nav_frame = ctk.CTkFrame(self, height=65, corner_radius=8)
        nav_frame.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            nav_frame,
            text="مسیر گام‌به‌گام طراحی مهندسی (Wizard):",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="right", padx=12)

        self.step_buttons = []
        steps = [
            (0, "گام ۱: ساختار IEC 81346 و شبکه"),
            (1, "گام ۲: افزودن فیدرهای قدرت/موتور"),
            (2, "گام ۳: سنسورها، عملگرها و PLC"),
            (3, "گام ۴: اجرای محاسبات و کنترل خطا"),
            (4, "گام ۵: مدار فرمان، TCC و خروجی EPLAN"),
            (5, "گام ۶: مدیریت کاتالوگ SQLite"),
        ]
        for idx, title in steps:
            btn = ctk.CTkButton(
                nav_frame, text=title, width=185, height=36,
                fg_color="#1F4E78" if idx == 0 else "#34495E",
                command=lambda i=idx: self.switch_step(i)
            )
            btn.pack(side="right", padx=4, pady=10)
            self.step_buttons.append(btn)

        # Main Content Container
        self.container = ctk.CTkFrame(self, corner_radius=8)
        self.container.pack(fill="both", expand=True, padx=12, pady=6)

        self.frames = [ctk.CTkFrame(self.container, fg_color="transparent") for _ in range(6)]
        self._build_step1_project_and_iec81346(self.frames[0])
        self._build_step2_power_feeders(self.frames[1])
        self._build_step3_plc_and_instruments(self.frames[2])
        self._build_step4_calculations_and_validation(self.frames[3])
        self._build_step5_control_schematic_and_eplan(self.frames[4])
        self._build_step6_sqlite_catalog(self.frames[5])

        self.switch_step(0)

    def switch_step(self, step_idx: int):
        for i, frame in enumerate(self.frames):
            frame.pack_forget()
            self.step_buttons[i].configure(fg_color="#2E86C1" if i == step_idx else "#34495E")
        self.frames[step_idx].pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------------------------------------------
    # STEP 1: Project Spec & IEC 81346 Structure
    # ------------------------------------------------------------------
    def _build_step1_project_and_iec81346(self, parent):
        guide = ctk.CTkLabel(
            parent,
            text="راهنمای گام ۱: مشخصات پایه تابلو، شرایط محیطی و ساختار کدگذاری استاندارد EPLAN (IEC 81346) را وارد کنید.\n"
                 "اگر فایل اکسل آماده دارید می‌توانید مستقیماً از دکمه پایین بارگذاری کنید، وگرنه روی «ادامه به گام ۲» کلیک کنید.",
            font=ctk.CTkFont(size=13), justify="right", text_color="#AED6F1"
        )
        guide.pack(anchor="e", padx=15, pady=8)

        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=15, pady=8)

        self.entries_step1 = {}
        fields = [
            ("project_name", "نام پروژه صنعتی:", "تابلوی برق و کنترل فرآیند"),
            ("higher_func", "کد سطح بالای فرآیند در EPLAN (==):", "==PROCESS"),
            ("install_site", "کد محل نصب در سایت (++):", "++EL_ROOM1"),
            ("panel_tag", "کد تابلو / Mounting Location (+):", "+MCC1"),
            ("nominal_voltage_v", "ولتاژ نامی خط به خط (V):", "400"),
            ("earthing_system", "نوع سیستم زمین (TN-S / TN-C-S / TT / IT):", "TN-S"),
            ("prospective_ik_ka", "جریان اتصال کوتاه سه‌فاز در محل تابلو Ik'' (kA):", "25.0"),
            ("ambient_temp_c", "دمای محیط بیرون تابلو (°C):", "40.0"),
            ("max_internal_temp_c", "حداکثر دمای مجاز داخل تابلو (°C):", "50.0"),
            ("target_ip", "درجه حفاظت مورد نیاز (IP54 / IP55 / IP65):", "IP54"),
            ("spare_factor", "ضریب رزرو و توسعه آتی (مثلاً 0.20 برای ۲۰٪):", "0.20"),
        ]
        for i, (key, label_txt, default_val) in enumerate(fields):
            r, c = divmod(i, 2)
            lbl = ctk.CTkLabel(form, text=label_txt, font=ctk.CTkFont(size=12))
            lbl.grid(row=r, column=c * 2 + 1, padx=10, pady=8, sticky="e")
            ent = ctk.CTkEntry(form, width=220)
            ent.insert(0, default_val)
            ent.grid(row=r, column=c * 2, padx=10, pady=8, sticky="w")
            self.entries_step1[key] = ent

        btn_bar = ctk.CTkFrame(parent, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(
            btn_bar, text="ادامه به گام ۲: تعریف مرحله‌ای بارها و موتورها ⬅",
            fg_color="#1E8449", height=40, command=lambda: self.switch_step(1)
        ).pack(side="left", padx=10)

    # ------------------------------------------------------------------
    # STEP 2: Interactive Step-by-Step Feeder Entry (Without Excel!)
    # ------------------------------------------------------------------
    def _build_step2_power_feeders(self, parent):
        ctk.CTkLabel(
            parent,
            text="گام ۲: تعریف فیدرهای قدرت و موتورها به صورت تعاملی (اگر ضریب توان، راندمان یا مقطع کابل را نمی‌دانید خالی بگذارید؛ برنامه از شما می‌پرسد یا محاسبه می‌کند).",
            font=ctk.CTkFont(size=13), text_color="#A9DFBF"
        ).pack(anchor="e", padx=12, pady=6)

        add_bar = ctk.CTkFrame(parent)
        add_bar.pack(fill="x", padx=12, pady=6)

        self.ent_f_id = ctk.CTkEntry(add_bar, placeholder_text="کد فیدر (مثلاً F01)", width=90)
        self.ent_f_id.pack(side="right", padx=4, pady=8)

        self.ent_f_func = ctk.CTkEntry(add_bar, placeholder_text="=Function (مثلاً =PUMP1)", width=120)
        self.ent_f_func.pack(side="right", padx=4, pady=8)

        self.ent_f_desc = ctk.CTkEntry(add_bar, placeholder_text="شرح بار (مثلاً پمپ تغذیه بویلر)", width=190)
        self.ent_f_desc.pack(side="right", padx=4, pady=8)

        self.cmb_f_type = ctk.CTkComboBox(
            add_bar, values=[t.value for t in LoadType], width=165
        )
        self.cmb_f_type.set("MOTOR_DOL")
        self.cmb_f_type.pack(side="right", padx=4, pady=8)

        self.ent_f_kw = ctk.CTkEntry(add_bar, placeholder_text="توان (kW)", width=85)
        self.ent_f_kw.pack(side="right", padx=4, pady=8)

        self.ent_f_len = ctk.CTkEntry(add_bar, placeholder_text="طول کابل (m)", width=95)
        self.ent_f_len.pack(side="right", padx=4, pady=8)

        self.ent_f_cosphi = ctk.CTkEntry(add_bar, placeholder_text="cos φ (اختیاری)", width=95)
        self.ent_f_cosphi.pack(side="right", padx=4, pady=8)

        ctk.CTkButton(
            add_bar, text="+ افزودن فیدر با پرسش تعاملی", fg_color="#2E86C1",
            command=self.action_add_feeder_interactively
        ).pack(side="left", padx=8, pady=8)

        # Treeview of added feeders
        cols = ("id", "func", "loc", "desc", "type", "kw", "cosphi", "eff", "len")
        self.tree_step2 = ttk.Treeview(parent, columns=cols, show="headings", height=12)
        for c, t, w in [
            ("id", "کد فیدر", 70), ("func", "=Function", 100), ("loc", "+Location", 100),
            ("desc", "شرح فیدر", 220), ("type", "نوع راه‌انداز", 140), ("kw", "توان (kW)", 85),
            ("cosphi", "ضریب توان", 85), ("eff", "راندمان", 85), ("len", "طول کابل (m)", 95)
        ]:
            self.tree_step2.heading(c, text=t)
            self.tree_step2.column(c, width=w, anchor="center")
        self.tree_step2.pack(fill="both", expand=True, padx=12, pady=8)

        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(
            nav, text="ادامه به گام ۳: سنسورها، عملگرها و PLC ⬅",
            fg_color="#1E8449", command=lambda: self.switch_step(2)
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            nav, text="حذف فیدر انتخاب‌شده", fg_color="#C0392B",
            command=self.action_remove_selected_feeder
        ).pack(side="right", padx=6)

    def action_add_feeder_interactively(self):
        f_id = self.ent_f_id.get().strip() or f"F{len(self.feeders_list)+1:02d}"
        func = self.ent_f_func.get().strip() or f"=M{len(self.feeders_list)+1}"
        if not func.startswith("="):
            func = "=" + func
        loc = self.entries_step1["panel_tag"].get().strip() or "+MCC1"
        desc = self.ent_f_desc.get().strip() or f"فیدر {f_id}"
        ltype = LoadType(self.cmb_f_type.get())

        kw_str = self.ent_f_kw.get().strip()
        if not kw_str:
            kw_str = simpledialog.askstring("ورود توان بار", f"لطفاً توان نامی فیدر {f_id} ({desc}) را بر حسب کیلووات وارد کنید:")
            if not kw_str:
                return
        power_kw = float(kw_str)

        len_str = self.ent_f_len.get().strip()
        if not len_str:
            len_str = simpledialog.askstring("طول کابل خروجی", f"طول تقریبی کابل از تابلو تا {desc} چند متر است؟ (برای محاسبه افت ولتاژ):", initialvalue="30")
        cable_len = float(len_str) if len_str else 30.0

        cosphi_str = self.ent_f_cosphi.get().strip()
        cos_phi = float(cosphi_str) if cosphi_str else None
        eff = None

        if ltype in (LoadType.MOTOR_DOL, LoadType.MOTOR_STAR_DELTA, LoadType.MOTOR_VFD) and cos_phi is None:
            ans = messagebox.askyesno(
                "تکمیل مشخصات پلاک موتور",
                f"برای موتور {desc} ({power_kw} kW) ضریب توان و راندمان وارد نشده است.\n"
                "آیا می‌خواهید الان مقادیر پلاک موتور را دستی وارد کنید؟\n"
                "(در صورت انتخاب No، مقادیر استاندارد IEC 60034 کلاس IE3 استفاده می‌شود)."
            )
            if ans:
                cp_in = simpledialog.askstring("ضریب توان موتور", "ضریب توان (cos φ) بین 0.5 تا 1.0:", initialvalue="0.86")
                ef_in = simpledialog.askstring("راندمان موتور", "راندمان موتور (η) بین 0.5 تا 1.0:", initialvalue="0.91")
                if cp_in:
                    cos_phi = float(cp_in)
                if ef_in:
                    eff = float(ef_in)

        feeder = FeederInput(
            feeder_id=f_id, func_tag=func, loc_tag=loc, description=desc,
            load_type=ltype, power_kw=power_kw, cos_phi=cos_phi, efficiency=eff,
            cable_length_m=cable_len
        )
        self.feeders_list.append(feeder)
        self.tree_step2.insert("", "end", values=(
            feeder.feeder_id, feeder.func_tag, feeder.loc_tag, feeder.description,
            feeder.load_type.value, feeder.power_kw,
            feeder.cos_phi if feeder.cos_phi else "IE3 Auto",
            feeder.efficiency if feeder.efficiency else "IE3 Auto",
            feeder.cable_length_m
        ))
        self.ent_f_id.delete(0, "end")
        self.ent_f_desc.delete(0, "end")
        self.ent_f_kw.delete(0, "end")

    def action_remove_selected_feeder(self):
        sel = self.tree_step2.selection()
        if not sel:
            return
        idx = self.tree_step2.index(sel[0])
        self.tree_step2.delete(sel[0])
        if 0 <= idx < len(self.feeders_list):
            self.feeders_list.pop(idx)

    # ------------------------------------------------------------------
    # STEP 3: Sensors, Actuators & PLC Configuration
    # ------------------------------------------------------------------
    def _build_step3_plc_and_instruments(self, parent):
        ctk.CTkLabel(
            parent,
            text="گام ۳: تعریف سنسورها (DI / AI 4-20mA) و عملگرها (شیر برقی ۲۴ ولت / شیر کنترلی) جهت محاسبه خودکار کارت‌های PLC، رله‌های واسط و ترمینال‌ها",
            font=ctk.CTkFont(size=13), text_color="#F9E79F"
        ).pack(anchor="e", padx=12, pady=6)

        bar = ctk.CTkFrame(parent)
        bar.pack(fill="x", padx=12, pady=6)

        self.ent_i_tag = ctk.CTkEntry(bar, placeholder_text="تگ ابزار دقیق (مثلاً PT-101)", width=140)
        self.ent_i_tag.pack(side="right", padx=4, pady=8)

        self.ent_i_desc = ctk.CTkEntry(bar, placeholder_text="شرح (مثلاً ترانسمیتر فشار خط اصلی)", width=230)
        self.ent_i_desc.pack(side="right", padx=4, pady=8)

        self.cmb_i_type = ctk.CTkComboBox(
            bar, values=[s.value for s in AutomationSignalType], width=210
        )
        self.cmb_i_type.set("SENSOR_AI_4_20MA")
        self.cmb_i_type.pack(side="right", padx=4, pady=8)

        self.ent_i_len = ctk.CTkEntry(bar, placeholder_text="طول کابل فیلد (m)", width=110)
        self.ent_i_len.pack(side="right", padx=4, pady=8)

        ctk.CTkButton(
            bar, text="+ افزودن سنسور / عملگر به پروژه", fg_color="#8E44AD",
            command=self.action_add_instrument
        ).pack(side="left", padx=8, pady=8)

        cols_i = ("tag", "desc", "sig", "len")
        self.tree_step3 = ttk.Treeview(parent, columns=cols_i, show="headings", height=11)
        for c, t, w in [
            ("tag", "تگ ابزار دقیق (Tag)", 140),
            ("desc", "شرح سنسور یا عملگر", 300),
            ("sig", "نوع سیگنال و تغذیه", 220),
            ("len", "طول کابل در سایت (m)", 140),
        ]:
            self.tree_step3.heading(c, text=t)
            self.tree_step3.column(c, width=w, anchor="center")
        self.tree_step3.pack(fill="both", expand=True, padx=12, pady=8)

        nav = ctk.CTkFrame(parent, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(
            nav, text="اجرای کامل محاسبات مهندسی و رفتن به گام ۴ ⬅",
            fg_color="#1E8449", height=40, command=self.action_execute_full_wizard_calc
        ).pack(side="left", padx=6)

    def action_add_instrument(self):
        tag = self.ent_i_tag.get().strip() or f"INST-{len(self.instruments_list)+1:02d}"
        desc = self.ent_i_desc.get().strip() or f"تجهیز ابزار دقیق {tag}"
        sig = AutomationSignalType(self.cmb_i_type.get())
        c_len = float(self.ent_i_len.get().strip() or 35.0)

        inst = FieldInstrumentInput(
            tag_id=tag,
            higher_func=self.entries_step1["higher_func"].get().strip() or "==PROCESS",
            func_group="=INST",
            install_site="++FIELD_AREA",
            mounting_loc="+FIELD",
            description=desc,
            signal_type=sig,
            cable_length_m=c_len
        )
        self.instruments_list.append(inst)
        self.tree_step3.insert("", "end", values=(inst.tag_id, inst.description, inst.signal_type.value, inst.cable_length_m))
        self.ent_i_tag.delete(0, "end")
        self.ent_i_desc.delete(0, "end")

    # ------------------------------------------------------------------
    # STEP 4: Results, PLC I/O Summary & Validation Log
    # ------------------------------------------------------------------
    def _build_step4_calculations_and_validation(self, parent):
        self.lbl_step4_summary = ctk.CTkLabel(
            parent, text="هنوز محاسبه‌ای اجرا نشده است.", font=ctk.CTkFont(size=13, weight="bold"),
            justify="right", text_color="#AED6F1"
        )
        self.lbl_step4_summary.pack(anchor="e", padx=12, pady=6)

        cols_v = ("status", "rule", "target", "desc", "evidence", "action")
        self.tree_step4_vals = ttk.Treeview(parent, columns=cols_v, show="headings", height=14)
        for c, t, w in [
            ("status", "وضعیت", 120), ("rule", "کد قاعده", 115), ("target", "بخش/فیدر", 90),
            ("desc", "شرح کنترل استاندارد", 280), ("evidence", "شواهد محاسباتی", 280), ("action", "اقدام پیشنهادی", 250)
        ]:
            self.tree_step4_vals.heading(c, text=t)
            self.tree_step4_vals.column(c, width=w, anchor="center")
        self.tree_step4_vals.pack(fill="both", expand=True, padx=12, pady=8)

        btn_bar = ctk.CTkFrame(parent, fg_color="transparent")
        btn_bar.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(
            btn_bar, text="صدور فایل Excel چهاربرگی و EPLAN BOM", fg_color="#C55A11",
            command=self.action_export_excel
        ).pack(side="right", padx=6)
        ctk.CTkButton(
            btn_bar, text="صدور و نمایش دفترچه محاسبات قابل چاپ (شامل مدار فرمان و TCC)",
            fg_color="#6C3483", command=self.action_export_printable_dossier
        ).pack(side="right", padx=6)

    def action_execute_full_wizard_calc(self):
        if not self.feeders_list:
            messagebox.showwarning(
                "لیست فیدرها خالی است",
                "لطفاً در گام ۲ حداقل یک فیدر قدرت یا موتور به پروژه اضافه کنید."
            )
            self.switch_step(1)
            return

        # Count motor types for PLC sizing
        dol_cnt = sum(1 for f in self.feeders_list if f.load_type == LoadType.MOTOR_DOL)
        yd_cnt = sum(1 for f in self.feeders_list if f.load_type == LoadType.MOTOR_STAR_DELTA)
        vfd_cnt = sum(1 for f in self.feeders_list if f.load_type == LoadType.MOTOR_VFD)

        panel_tag = self.entries_step1["panel_tag"].get().strip() or "+MCC1"
        inst_outs, plc_sum = IndustrialAutomationEngine.process_automation_and_plc(
            panel_tag=panel_tag,
            motor_dol_count=dol_cnt,
            motor_yd_count=yd_cnt,
            motor_vfd_count=vfd_cnt,
            instruments=self.instruments_list,
            spare_io_factor=float(self.entries_step1["spare_factor"].get() or 0.20)
        )
        self.last_auto_results = (inst_outs, plc_sum)

        project = ProjectSpec(
            project_name=self.entries_step1["project_name"].get().strip(),
            panel_tag=panel_tag,
            nominal_voltage_v=float(self.entries_step1["nominal_voltage_v"].get() or 400.0),
            earthing_system=EarthingSystem(self.entries_step1["earthing_system"].get().strip()),
            prospective_ik_ka=float(self.entries_step1["prospective_ik_ka"].get() or 25.0),
            ambient_temp_c=float(self.entries_step1["ambient_temp_c"].get() or 40.0),
            max_internal_temp_c=float(self.entries_step1["max_internal_temp_c"].get() or 50.0),
            target_ip=self.entries_step1["target_ip"].get().strip() or "IP54",
            spare_factor=float(self.entries_step1["spare_factor"].get() or 0.20),
            plc_hmi_24vdc_power_w=plc_sum.total_instrumentation_24v_w
        )

        f_outs, summary, validations = self.engine.process_project(project, self.feeders_list)
        self.current_project = project
        self.last_results = (f_outs, summary, validations)

        self.lbl_step4_summary.configure(
            text=f"جریان کل تابلو: {summary.design_main_current_a}A | کلید اصلی: {summary.main_breaker.part_number if summary.main_breaker else '-'} | "
                 f"تغذیه ۲۴ ولت (شامل PLC و سنسورها): {summary.ctrl_24v_total_continuous_w}W ({summary.selected_psu_24v.part_number if summary.selected_psu_24v else '-'}) | "
                 f"کانال‌های PLC (با رزرو): DI={plc_sum.required_di_with_spare}, DO={plc_sum.required_do_with_spare}, AI={plc_sum.required_ai_with_spare}, AO={plc_sum.required_ao_with_spare}"
        )

        for item in self.tree_step4_vals.get_children():
            self.tree_step4_vals.delete(item)
        for v in validations:
            self.tree_step4_vals.insert("", "end", values=(
                v.status.value, v.rule_id, v.feeder_id, v.description, v.supporting_evidence, v.recommended_action
            ))

        self.switch_step(3)

    # ------------------------------------------------------------------
    # STEP 5: EPLAN Guide, TCC Plain Explanation & Control Circuit Info
    # ------------------------------------------------------------------
    def _build_step5_control_schematic_and_eplan(self, parent):
        txt = ctk.CTkTextbox(parent, font=ctk.CTkFont(family="Tahoma", size=13), wrap="word")
        txt.pack(fill="both", expand=True, padx=12, pady=12)
        guide_content = (
            "📘 ۱. نحوه استفاده عملی از خروجی EPLAN Electric P8 (بدون نیاز به اسکریپت پیچیده):\n"
            "--------------------------------------------------------------------------------\n"
            "وقتی در گام ۴ روی دکمه «صدور فایل Excel چهاربرگی و EPLAN BOM» کلیک می‌کنید، شیت چهارم (04_BOM_and_EPLAN) دارای ستون‌های استاندارد زیر است:\n"
            "  • IEC81346_Full_DT (تگ کامل قطعه مثل ==PROCESS=PUMP1++EL_ROOM1+MCC1-Q1)\n"
            "  • =Function (عملکرد) | +Location (محل نصب: +MCC1.MP1 یا +DOOR یا +FIELD) | -BMK (شناسه تجهیز)\n"
            "  • Order_Code (پارت‌نامبر دقیق کاتالوگ زیمنس/ریتال/فونیکس)\n\n"
            "مراحل ایمپورت در EPLAN Electric P8 (نسخه‌های 2.9 تا 2026):\n"
            "  1) در EPLAN از منوی Project Data -> Pre-planning -> Navigator را باز کنید.\n"
            "  2) راست‌کلیک کرده و گزینه Import Pre-planning Data (یا در بخش Devices گزینه Import Devices) را انتخاب کنید.\n"
            "  3) فایل اکسل خروجی این برنامه را انتخاب کنید تا تمام درختواره ==، =، ++، + و قطعات داخل Navigator ساخته شوند و فقط آن‌ها را Drag & Drop کنید!\n\n"
            "💡 ۲. توضیح ساده منحنی TCC (هماهنگی کلیدها به زبان ساده):\n"
            "--------------------------------------------------------------------------------\n"
            "  • محور افقی شدت جریان اتصالی (آمپر) و محور عمودی زمان قطع کلید (ثانیه) را نشان می‌دهد.\n"
            "  • خط سبز (کلید فرعی موتور) باید کاملاً پایین‌تر و سمت چپ خط قرمز (کلید اصلی تابلو) باشد تا در زمان اتصالی، فقط کلید فرعی بپرد و کل کارخانه خاموش نشود.\n\n"
            "⚡ ۳. شماتیک مدار فرمان ۲۴ ولت و جدول ترمینال‌های سنسور/PLC:\n"
            "--------------------------------------------------------------------------------\n"
            "  • با کلیک روی دکمه «دفترچه محاسبات قابل چاپ» در گام ۴، نقشه گرافیکی مدار فرمان ۲۴ ولت (شامل کنتاکت 95-96 بی‌متال، استپ اضطراری، سلکتور Hand/Off/Auto، رله PLC و فیدبک‌های DI) به صورت вектор SVG در گزارش درج و نمایش داده می‌شود."
        )
        txt.insert("1.0", guide_content)

    # ------------------------------------------------------------------
    # STEP 6: SQLite Catalog Viewer & Quick Adder
    # ------------------------------------------------------------------
    def _build_step6_sqlite_catalog(self, parent):
        ctk.CTkLabel(
            parent, text="گام ۶: مشاهده و افزودن قطعه جدید به کاتالوگ پروژه (همگام با SQLite و موتور انتخاب)",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="e", padx=12, pady=6)

        cols_c = ("part", "mfg", "series", "type", "in_a", "kw", "icu", "loss")
        self.tree_cat = ttk.Treeview(parent, columns=cols_c, show="headings", height=15)
        for c, t, w in [
            ("part", "پارت‌نامبر (Order Code)", 170), ("mfg", "سازنده", 100), ("series", "سری محصول", 150),
            ("type", "نوع تجهیز", 120), ("in_a", "جریان نامی (A)", 100), ("kw", "توان موتور (kW)", 100),
            ("icu", "قدرت قطع (kA)", 100), ("loss", "تلفات حرارتی (W)", 110)
        ]:
            self.tree_cat.heading(c, text=t)
            self.tree_cat.column(c, width=w, anchor="center")
        self.tree_cat.pack(fill="both", expand=True, padx=12, pady=8)

        for d in self.catalog:
            self.tree_cat.insert("", "end", values=(
                d.part_number, d.manufacturer, d.series, d.device_type,
                d.rated_current_in_a, d.motor_kw_400v, d.icu_ka_400v, d.power_loss_w
            ))

    def action_export_excel(self):
        if not self.last_results:
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="LV_Panel_Field_Output.xlsx")
        if path:
            f_outs, summary, validations = self.last_results
            ExcelExporter.export_to_excel(path, self.current_project, f_outs, summary, validations)
            messagebox.showinfo("ذخیره شد", f"فایل اکسل مهندسی و EPLAN BOM در مسیر زیر ذخیره شد:\n{path}")

    def action_export_printable_dossier(self):
        if not self.last_results:
            return
        f_outs, summary, validations = self.last_results
        path = os.path.abspath("LV_Panel_Field_Engineering_Report.html")
        PrintableReportExporter.generate_html_report(path, self.current_project, f_outs, summary, validations)

        # Inject Control Circuit SVG, Plain TCC Guide & PLC/Instrumentation Table into HTML
        if self.last_auto_results:
            inst_outs, plc_sum = self.last_auto_results
            ctrl_svg = IndustrialAutomationEngine.generate_standard_control_circuit_svg(
                f"{self.feeders_list[0].func_tag}{self.current_project.panel_tag}"
            )
            tcc_guide = IndustrialAutomationEngine.get_plain_language_tcc_guide_html()

            inst_rows = "".join(
                f"<tr><td><b>{i.tag_id}</b></td><td dir='ltr'>{i.iec81346_field_dt}</td>"
                f"<td dir='ltr'>{i.iec81346_terminal_dt}</td><td dir='ltr'><b>{i.plc_channel_address}</b></td>"
                f"<td>{i.description}</td><td>{i.signal_type.value}</td><td dir='ltr'>{i.recommended_cable}</td>"
                f"<td dir='ltr'>{i.interface_device_part}</td></tr>"
                for i in inst_outs
            )
            extra_html = f"""
            {tcc_guide}
            <h2>۵. شماتیک استاندارد مدار فرمان ۲۴ ولت صنعتی (IEC 60204-1) و اینترفیس PLC</h2>
            {ctrl_svg}
            <h2>۶. جدول ابزار دقیق سایت (Sensors & Actuators)، ترمینال‌بندی و تخصیص کارت‌های PLC ({plc_sum.selected_cpu_part})</h2>
            <p><b>خلاصه کانال‌های PLC (با احتساب ۲۰٪ رزرو):</b> DI = {plc_sum.required_di_with_spare} ({plc_sum.selected_di_cards_qty}x 16Ch) | DO = {plc_sum.required_do_with_spare} ({plc_sum.selected_do_cards_qty}x 16Ch + {plc_sum.total_interposing_relays_qty} Relays) | AI = {plc_sum.required_ai_with_spare} ({plc_sum.selected_ai_cards_qty}x 8Ch) | AO = {plc_sum.required_ao_with_spare} ({plc_sum.selected_ao_cards_qty}x 4Ch)</p>
            <table>
                <thead><tr><th>تگ</th><th>کد کامل فیلد (IEC 81346)</th><th>ترمینال تابلو</th><th>آدرس PLC</th><th>شرح</th><th>نوع سیگنال</th><th>کابل</th><th>رله واسط / ایزولاتور</th></tr></thead>
                <tbody>{inst_rows}</tbody>
            </table>
            """
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace('<div class="disclaimer">', extra_html + '<div class="disclaimer">')
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        webbrowser.open(f"file://{path}")


if __name__ == "__main__":
    app = InteractiveEngineeringWizard()
    app.mainloop()