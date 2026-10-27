# -*- coding: utf-8 -*-
"""
LV-PanelAssist Field & Industrial Automation Module (v0.6.0-FieldReady)
Covers:
  1. IEC 81346 Full Structure Designation (==FuncAssign, =Function, ++Site, +Location, -BMK)
  2. Instrumentation & Control (PLC, Sensors DI/AI 4-20mA, Actuators Solenoid/MOV/Control Valve)
  3. Automatic PLC I/O Sizing (Siemens SIMATIC ET 200SP / S7-1200 with 20% Spare)
  4. Standard Industrial 24VDC Control Circuit Schematic SVG Generator
  5. Plain-Language TCC Curve Guide & Interactive Missing-Data Detector
"""

import math
from enum import Enum
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field


class AutomationSignalType(str, Enum):
    SENSOR_DI_24V = "SENSOR_DI_24V"                 # سنسور دیجیتال ۲۴ ولت (پراکسیمیتی، لیمیت سوئیچ، پرشر سوئیچ)
    SENSOR_AI_4_20MA = "SENSOR_AI_4_20MA"           # ترانسمیتر آنالوگ 4-20mA (فشار، دما، سطح، دبی)
    ACTUATOR_SOLENOID_24V = "ACTUATOR_SOLENOID_24V" # شیر برقی ۲۴ ولت (Solenoid Valve)
    ACTUATOR_AO_4_20MA = "ACTUATOR_AO_4_20MA"       # شیر کنترلی تدریجی (Control Valve Positioner 4-20mA)


class FieldInstrumentInput(BaseModel):
    tag_id: str = Field(..., min_length=1, description="مثلاً PT-101 یا XV-201")
    higher_func: str = Field(default="==PROCESS", description="IEC 81346 (==)")
    func_group: str = Field(default="=INST", description="IEC 81346 (=)")
    install_site: str = Field(default="++HALL1", description="IEC 81346 (++)")
    mounting_loc: str = Field(default="+FIELD", description="IEC 81346 (+)")
    description: str
    signal_type: AutomationSignalType
    power_consumption_24v_w: Optional[float] = Field(default=None, ge=0.0)
    cable_length_m: float = Field(default=30.0, gt=0)


class InstrumentCalcOutput(BaseModel):
    tag_id: str
    iec81346_field_dt: str
    iec81346_terminal_dt: str
    iec81346_relay_or_isolator_dt: str
    plc_channel_address: str
    description: str
    signal_type: AutomationSignalType
    power_24v_w: float
    recommended_cable: str
    terminal_type: str
    interface_device_part: str


class PLCSummaryOutput(BaseModel):
    raw_di_count: int
    raw_do_count: int
    raw_ai_count: int
    raw_ao_count: int
    required_di_with_spare: int
    required_do_with_spare: int
    required_ai_with_spare: int
    required_ao_with_spare: int
    selected_cpu_part: str
    selected_di_cards_qty: int
    selected_do_cards_qty: int
    selected_ai_cards_qty: int
    selected_ao_cards_qty: int
    total_interposing_relays_qty: int
    total_signal_isolators_qty: int
    total_instrumentation_24v_w: float


class IndustrialAutomationEngine:
    """
    موتور محاسبات ابزار دقیق، کارت‌های PLC زیمنس (ET 200SP / S7-1200)،
    ترمینال‌بندی و کدگذاری استاندارد IEC 81346 برای استفاده میدانی
    """

    @staticmethod
    def get_iec81346_bmk_prefix(signal_type: AutomationSignalType) -> str:
        if signal_type in (AutomationSignalType.SENSOR_DI_24V, AutomationSignalType.SENSOR_AI_4_20MA):
            return "-B"  # IEC 81346-2 Code for Sensors / Transducers
        return "-Y"      # IEC 81346-2 Code for Electrically operated valves / Actuators

    @classmethod
    def process_automation_and_plc(
        cls,
        panel_tag: str,
        motor_dol_count: int,
        motor_yd_count: int,
        motor_vfd_count: int,
        instruments: List[FieldInstrumentInput],
        spare_io_factor: float = 0.20
    ) -> Tuple[List[InstrumentCalcOutput], PLCSummaryOutput]:
        """
        محاسبه کانال‌های PLC ناشی از فیدرهای موتوری تابلو + سنسورها و عملگرهای سایت
        - هر موتور DOL یا ستاره-مثلث: 3x DI (Run, Trip, Auto/Remote) + 1x DO (Start/Stop Command)
        - هر موتور VFD: 3x DI + 1x DO + 1x AI (Speed Feedback) + 1x AO (Speed Setpoint)
        """
        inst_outputs: List[InstrumentCalcOutput] = []

        # Base I/O from MCC motor feeders
        di_cnt = (motor_dol_count + motor_yd_count + motor_vfd_count) * 3
        do_cnt = (motor_dol_count + motor_yd_count + motor_vfd_count) * 1
        ai_cnt = motor_vfd_count * 1
        ao_cnt = motor_vfd_count * 1

        total_inst_24v_w = 0.0
        relay_cnt = do_cnt  # One interposing relay per motor DO command
        isolator_cnt = 0

        for idx, inst in enumerate(instruments, start=1):
            bmk_prefix = cls.get_iec81346_bmk_prefix(inst.signal_type)
            field_dt = f"{inst.higher_func}{inst.func_group}{inst.install_site}{inst.mounting_loc}{bmk_prefix}{idx}_{inst.tag_id}"

            if inst.signal_type == AutomationSignalType.SENSOR_DI_24V:
                di_cnt += 1
                pwr_w = inst.power_consumption_24v_w if inst.power_consumption_24v_w is not None else 1.2
                term_dt = f"{inst.higher_func}{inst.func_group}++EL_ROOM{panel_tag}.MP1-X_DI:{idx}"
                rel_dt = "-"
                plc_addr = f"%I{di_cnt // 8}.{di_cnt % 8}"
                cable_str = "3x0.75 mm² Cu (LiYY Unshielded)"
                term_type = "Phoenix Contact PTI 2.5-PE/L/NT (3-Level Sensor Terminal)"
                iface_part = "Direct to 24VDC DI Module"

            elif inst.signal_type == AutomationSignalType.SENSOR_AI_4_20MA:
                ai_cnt += 1
                isolator_cnt += 1
                pwr_w = inst.power_consumption_24v_w if inst.power_consumption_24v_w is not None else 1.5
                term_dt = f"{inst.higher_func}{inst.func_group}++EL_ROOM{panel_tag}.MP1-X_AI:{idx}"
                rel_dt = f"{inst.higher_func}{inst.func_group}++EL_ROOM{panel_tag}.MP1-T_AI{ai_cnt}"
                plc_addr = f"%IW{64 + ai_cnt * 2}"
                cable_str = "2x2x0.75 mm² Cu Shielded (LiYCY Twisted Pair)"
                term_type = "Phoenix Contact UT 2.5-MT (Knife Disconnect + Shield Clamp)"
                iface_part = "Phoenix MINI MCR-2-UI-I (Signal Isolator)"

            elif inst.signal_type == AutomationSignalType.ACTUATOR_SOLENOID_24V:
                do_cnt += 1
                relay_cnt += 1
                pwr_w = inst.power_consumption_24v_w if inst.power_consumption_24v_w is not None else 8.5
                term_dt = f"{inst.higher_func}{inst.func_group}++EL_ROOM{panel_tag}.MP1-X_DO:{idx}"
                rel_dt = f"{inst.higher_func}{inst.func_group}++EL_ROOM{panel_tag}.MP1-K_DO{do_cnt}"
                plc_addr = f"%Q{do_cnt // 8}.{do_cnt % 8}"
                cable_str = "3x1.5 mm² Cu (24VDC Solenoid + PE)"
                term_type = "Phoenix Contact UT 2.5 + LED Fuse Terminal"
                iface_part = "Phoenix PLC-RSC-24DC/21 (6.2mm Coupling Relay + Flyback Diode)"

            else:  # ACTUATOR_AO_4_20MA
                ao_cnt += 1
                isolator_cnt += 1
                pwr_w = inst.power_consumption_24v_w if inst.power_consumption_24v_w is not None else 2.0
                term_dt = f"{inst.higher_func}{inst.func_group}++EL_ROOM{panel_tag}.MP1-X_AO:{idx}"
                rel_dt = f"{inst.higher_func}{inst.func_group}++EL_ROOM{panel_tag}.MP1-T_AO{ao_cnt}"
                plc_addr = f"%QW{128 + ao_cnt * 2}"
                cable_str = "2x2x0.75 mm² Cu Shielded (LiYCY)"
                term_type = "Phoenix Contact UT 2.5-MT (Knife Disconnect)"
                iface_part = "Phoenix MINI MCR-2-I-I (Output Isolator)"

            total_inst_24v_w += pwr_w
            inst_outputs.append(InstrumentCalcOutput(
                tag_id=inst.tag_id,
                iec81346_field_dt=field_dt,
                iec81346_terminal_dt=term_dt,
                iec81346_relay_or_isolator_dt=rel_dt,
                plc_channel_address=plc_addr,
                description=inst.description,
                signal_type=inst.signal_type,
                power_24v_w=round(pwr_w, 1),
                recommended_cable=cable_str,
                terminal_type=term_type,
                interface_device_part=iface_part
            ))

        req_di = math.ceil(di_cnt * (1.0 + spare_io_factor))
        req_do = math.ceil(do_cnt * (1.0 + spare_io_factor))
        req_ai = math.ceil(ai_cnt * (1.0 + spare_io_factor))
        req_ao = math.ceil(ao_cnt * (1.0 + spare_io_factor))

        # Siemens ET 200SP Card Sizing (16ch DI, 16ch DQ, 8ch AI, 4ch AQ)
        di_cards = max(1, math.ceil(req_di / 16)) if req_di > 0 else 0
        do_cards = max(1, math.ceil(req_do / 16)) if req_do > 0 else 0
        ai_cards = math.ceil(req_ai / 8) if req_ai > 0 else 0
        ao_cards = math.ceil(req_ao / 4) if req_ao > 0 else 0

        # Add PLC & I/O modules internal 24VDC power (~18W base CPU + 2.5W per card)
        plc_self_power_w = 18.0 + (di_cards + do_cards + ai_cards + ao_cards) * 2.5
        total_inst_24v_w = round(total_inst_24v_w + plc_self_power_w, 1)

        plc_summary = PLCSummaryOutput(
            raw_di_count=di_cnt,
            raw_do_count=do_cnt,
            raw_ai_count=ai_cnt,
            raw_ao_count=ao_cnt,
            required_di_with_spare=req_di,
            required_do_with_spare=req_do,
            required_ai_with_spare=req_ai,
            required_ao_with_spare=req_ao,
            selected_cpu_part="Siemens CPU 1510SP-1 PN (6ES7510-1DJ01-0AB0)",
            selected_di_cards_qty=di_cards,
            selected_do_cards_qty=do_cards,
            selected_ai_cards_qty=ai_cards,
            selected_ao_cards_qty=ao_cards,
            total_interposing_relays_qty=relay_cnt,
            total_signal_isolators_qty=isolator_cnt,
            total_instrumentation_24v_w=total_inst_24v_w
        )
        return inst_outputs, plc_summary

    @staticmethod
    def generate_standard_control_circuit_svg(feeder_tag: str = "=PUMP1+MCC1") -> str:
        """
        تولید نقشه شماتیک استاندارد مدار فرمان ۲۴ ولت صنعتی (IEC 60204-1)
        شامل شینه +24VDC، کنتاکت بی‌متال 95-96، استپ اضطراری، سلکتور Local/Remote،
        کنتاکت رله PLC، بوبین کنتاکتور -K1M (A1/A2) و فیدبک Run/Trip به کارت DI پی‌ال‌سی
        """
        return f"""
        <svg viewBox="0 0 780 360" width="100%" height="340" style="background:#FFFFFF; border:1px solid #1F4E78; border-radius:6px; font-family:Calibri,sans-serif;">
            <!-- Top +24VDC Rail & Bottom 0VDC (M) Rail -->
            <line x1="30" y1="35" x2="750" y2="35" stroke="#C0392B" stroke-width="3"/>
            <text x="35" y="25" fill="#C0392B" font-size="12" font-weight="bold">L+ (+24V DC PELV — Protected by SITOP SEL1200 -F0)</text>

            <line x1="30" y1="325" x2="750" y2="325" stroke="#1F618D" stroke-width="3"/>
            <text x="35" y="345" fill="#1F618D" font-size="12" font-weight="bold">M (0V DC — Grounded to PE Bar per IEC 60204-1 Clause 9.4.2.1)</text>

            <!-- PATH 1: Main Contactor Coil Command (Local / PLC Auto) -->
            <line x1="120" y1="35" x2="120" y2="75" stroke="#000" stroke-width="1.8"/>
            <!-- 95-96 Overload NC Contact -->
            <line x1="120" y1="75" x2="108" y2="105" stroke="#000" stroke-width="2"/>
            <circle cx="120" cy="75" r="3" fill="#000"/><circle cx="120" cy="108" r="3" fill="#000"/>
            <text x="130" y="95" fill="#1F4E78" font-size="11" font-weight="bold">{feeder_tag}-Q1 / -F1 (95-96 NC Trip)</text>

            <!-- E-Stop NC Contact -->
            <line x1="120" y1="108" x2="120" y2="140" stroke="#000" stroke-width="1.8"/>
            <line x1="120" y1="140" x2="108" y2="168" stroke="#C0392B" stroke-width="2"/>
            <text x="130" y="158" fill="#C0392B" font-size="11" font-weight="bold">+DOOR-S0 (E-Stop NC)</text>

            <!-- Local / Remote Selector Split -->
            <line x1="120" y1="170" x2="120" y2="195" stroke="#000" stroke-width="1.8"/>
            <line x1="80" y1="195" x2="160" y2="195" stroke="#000" stroke-width="1.8"/>
            <text x="170" y="198" fill="#000" font-size="11" font-weight="bold">+DOOR-S1 (1-0-2 Hand/Off/Auto)</text>

            <!-- Left Branch: Local Start + Self-Hold 13-14 -->
            <line x1="80" y1="195" x2="80" y2="225" stroke="#000" stroke-width="1.5"/>
            <line x1="80" y1="225" x2="70" y2="250" stroke="#000" stroke-width="1.8"/>
            <text x="22" y="242" fill="#000" font-size="10">-S2 Start</text>
            <line x1="80" y1="252" x2="80" y2="270" stroke="#000" stroke-width="1.5"/>

            <!-- Right Branch: PLC Coupling Relay Contact -K_DO -->
            <line x1="160" y1="195" x2="160" y2="225" stroke="#000" stroke-width="1.5"/>
            <line x1="160" y1="225" x2="150" y2="250" stroke="#1E8449" stroke-width="2"/>
            <text x="168" y="242" fill="#1E8449" font-size="10" font-weight="bold">-K_DO1 (11-14 PLC Cmd)</text>
            <line x1="160" y1="252" x2="160" y2="270" stroke="#000" stroke-width="1.5"/>

            <!-- Rejoin to Contactor Coil -K1M (A1/A2) -->
            <line x1="80" y1="270" x2="160" y2="270" stroke="#000" stroke-width="1.8"/>
            <line x1="120" y1="270" x2="120" y2="282" stroke="#000" stroke-width="1.8"/>
            <rect x="98" y="282" width="44" height="28" fill="#EBF5FB" stroke="#1F4E78" stroke-width="2"/>
            <text x="120" y="300" fill="#1F4E78" font-size="11" font-weight="bold" text-anchor="middle">-K1M</text>
            <text x="82" y="288" fill="#555" font-size="9">A1</text>
            <text x="82" y="318" fill="#555" font-size="9">A2</text>
            <line x1="120" y1="310" x2="120" y2="325" stroke="#000" stroke-width="1.8"/>

            <!-- PATH 2: Run Feedback to PLC DI (%I0.0) & Green Lamp -H1 -->
            <line x1="390" y1="35" x2="390" y2="130" stroke="#000" stroke-width="1.8"/>
            <line x1="390" y1="130" x2="378" y2="160" stroke="#000" stroke-width="2"/>
            <text x="400" y="150" fill="#1F4E78" font-size="11" font-weight="bold">{feeder_tag}-K1M (13-14 NO Aux)</text>
            <line x1="390" y1="162" x2="390" y2="282" stroke="#000" stroke-width="1.8"/>
            <rect x="345" y="282" width="90" height="28" fill="#E9F7EF" stroke="#1E8449" stroke-width="2"/>
            <text x="390" y="300" fill="#1E8449" font-size="11" font-weight="bold" text-anchor="middle">PLC DI: RUN</text>
            <line x1="390" y1="310" x2="390" y2="325" stroke="#000" stroke-width="1.8"/>

            <!-- PATH 3: Trip/Fault Feedback to PLC DI (%I0.1) & Red Lamp -H2 -->
            <line x1="600" y1="35" x2="600" y2="130" stroke="#000" stroke-width="1.8"/>
            <line x1="600" y1="130" x2="588" y2="160" stroke="#C0392B" stroke-width="2"/>
            <text x="610" y="150" fill="#C0392B" font-size="11" font-weight="bold">{feeder_tag}-Q1 / -F1 (97-98 NO Trip)</text>
            <line x1="600" y1="162" x2="600" y2="282" stroke="#000" stroke-width="1.8"/>
            <rect x="555" y="282" width="90" height="28" fill="#FDEDEC" stroke="#C0392B" stroke-width="2"/>
            <text x="600" y="300" fill="#C0392B" font-size="11" font-weight="bold" text-anchor="middle">PLC DI: TRIP</text>
            <line x1="600" y1="310" x2="600" y2="325" stroke="#000" stroke-width="1.8"/>
        </svg>
        """.strip()

    @staticmethod
    def get_plain_language_tcc_guide_html() -> str:
        return """
        <div style="background:#FEF9E7; border-right:5px solid #F39C12; padding:12px; margin:10px 0; font-size:12px; line-height:1.7;">
            <b>📘 راهنمای ساده خواندن نمودار هماهنگی کلیدها (منحنی TCC به زبان ساده):</b><br>
            • <b>هدف این نمودار چیست؟</b> اطمینان از اینکه اگر در یکی از موتورها یا سنسورها اتصالی رخ داد، <b>فقط کلیدِ همان خط (منحنی سبز)</b> بپرد و کلید اصلی کل تابلو (منحنی قرمز) قطع نشود.<br>
            • <b>محور افقی (جریان):</b> هرچه به سمت راست برویم، شدت جریان اتصالی بیشتر است. | <b>محور عمودی (زمان):</b> هرچه بالاتر باشیم، کلید دیرتر قطع می‌کند.<br>
            • <b>دو بخش منحنی:</b> قسمت شیب‌دارِ بالا مربوط به <b>اضافه‌بار خفیف (بخش حرارتی)</b> است که کلید چند ثانیه صبر می‌کند؛ قسمت پله‌ایِ پایین مربوط به <b>اتصال کوتاه شدید (بخش مغناطیسی)</b> است که کلید در کسری از ثانیه می‌پرد.<br>
            • <b>شرط درستی طراحی:</b> تا زمانی که خط سبزِ کلید فرعی کاملاً زیرِ خط قرمزِ کلید اصلی قرار دارد و با هم تقاطع ندارند، هماهنگی (سلکتیویته) کامل برقرار است.
        </div>
        """.strip()