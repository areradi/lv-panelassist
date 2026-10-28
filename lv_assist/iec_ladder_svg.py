# -*- coding: utf-8 -*-
"""
LV-PanelAssist Dynamic IEC 60617 / EPLAN Multi-Line & Ladder Control Schematic Generator
100% Data-Driven per Feeder (DOL, Star-Delta, VFD, Sub-Feeder/Socket).
Includes:
  - Dynamic Wire Numbers in Blue Ovals (e.g. -101, -102, -201...)
  - Pin Numbers (1-2, 3-4, 5-6, 13-14, 11-12, 95-96, 97-98, A1-A2, LI1/LI2)
  - Terminal Strip (-X_CTRL) & Multi-core Field Control Cable (-W_CTRL)
  - Yellow EPLAN Coil Highlight Circles & Bottom Contact Mirror Cross-References
"""

import html
from typing import List, Dict
from pydantic import BaseModel


class LadderWireRowDTO(BaseModel):
    wire_no: str
    feeder_id: str
    potential_role: str
    from_pin: str
    to_pin: str
    wire_spec: str = "1x1.5 mm² Cu (Dark Blue 24VDC)"


class LadderTerminalRowDTO(BaseModel):
    feeder_id: str
    terminal_strip: str
    terminal_pin: str
    internal_wire_no: str
    internal_target: str
    cable_tag: str
    cable_spec: str
    cable_core: str
    external_location: str
    external_target: str


class FeederLadderDTO(BaseModel):
    feeder_index: int
    sheet_no: int
    project_name: str
    panel_tag: str
    feeder_id: str
    func_tag: str
    loc_tag: str
    description: str
    load_type: str
    power_kw: float
    ib_a: float
    delta_current_a: float = 0.0
    star_current_a: float = 0.0
    prot_tag: str
    prot_part: str
    prot_in_a: float
    km_tag: str = ""
    km_part: str = ""
    kd_tag: str = ""
    kd_part: str = ""
    ky_tag: str = ""
    ky_part: str = ""
    bimetal_tag: str = ""
    bimetal_part: str = ""
    timer_tag: str = ""
    timer_part: str = ""
    vfd_tag: str = ""
    vfd_part: str = ""
    power_cable_str: str = ""
    psu_part: str = ""


class IECLadderSvgGenerator:
    """تولیدکننده پویا نقشه مدار فرمان کارگاهی و لیست سیم‌کشی (From-To Wire & Terminal Schedule)"""

    @classmethod
    def build_feeder_wires_and_terminals(
        cls, d: FeederLadderDTO
    ) -> Dict[str, List[dict]]:
        idx = d.feeder_index
        w_base = idx * 100
        x_strip = f"-X{idx + 1}"
        w_cable = f"-W{idx}01"
        ext_loc = f"{d.func_tag}+FIELD"

        wires = [
            LadderWireRowDTO(
                wire_no=f"-{w_base + 1}", feeder_id=d.feeder_id,
                potential_role="24VDC Fused Feeder Control Supply (L+)",
                from_pin=f"-F0:OUT{min(4, idx)}",
                to_pin=f"{d.prot_tag}:95 / {d.prot_tag}:13 / -K{idx}OFF:11"
            ),
            LadderWireRowDTO(
                wire_no=f"-{w_base + 2}", feeder_id=d.feeder_id,
                potential_role="Thermal Overload Healthy Signal",
                from_pin=f"{d.bimetal_tag or d.prot_tag}:96",
                to_pin=f"{x_strip}:01 (To Field E-Stop)"
            ),
            LadderWireRowDTO(
                wire_no=f"-{w_base + 3}", feeder_id=d.feeder_id,
                potential_role="E-Stop Return / Ready to Start",
                from_pin=f"{x_strip}:02",
                to_pin=f"-S{idx}M_0_A:11 (Hand/Off/Auto Selector)"
            ),
            LadderWireRowDTO(
                wire_no=f"-{w_base + 4}", feeder_id=d.feeder_id,
                potential_role="Manual Start Branch",
                from_pin=f"-S{idx}M_0_A:14(M)",
                to_pin=f"{x_strip}:03 / -S{idx}START:13"
            ),
            LadderWireRowDTO(
                wire_no=f"-{w_base + 5}", feeder_id=d.feeder_id,
                potential_role="Auto PLC Start Branch",
                from_pin=f"-S{idx}M_0_A:24(A)",
                to_pin=f"-K_DO{idx}:11 (PLC Command Relay)"
            ),
            LadderWireRowDTO(
                wire_no=f"-{w_base + 6}", feeder_id=d.feeder_id,
                potential_role="Main Contactor / Drive Run Command",
                from_pin=f"-S{idx}START:14 / -K_DO{idx}:14",
                to_pin=f"{d.vfd_tag + ':LI1' if d.vfd_part else (d.km_tag or '-K' + str(idx)) + ':A1'}"
            ),
            LadderWireRowDTO(
                wire_no=f"-{w_base + 7}", feeder_id=d.feeder_id,
                potential_role="Run Status Feedback (NO Aux -> PLC DI & Lamp)",
                from_pin=f"{d.vfd_tag + ':R1A' if d.vfd_part else (d.km_tag or '-K' + str(idx)) + ':14'}",
                to_pin=f"-H{idx}ON:X1 / PLC_DI:%I{idx // 8}.{(idx * 2) % 8}"
            ),
            LadderWireRowDTO(
                wire_no=f"-{w_base + 8}", feeder_id=d.feeder_id,
                potential_role="Fault / Trip Status Feedback (97-98 -> PLC DI & Trip Lamp)",
                from_pin=f"{d.bimetal_tag or d.prot_tag}:98",
                to_pin=f"-H{idx}TRIP:X1 / PLC_DI:%I{idx // 8}.{(idx * 2 + 1) % 8}"
            ),
        ]

        if d.load_type == "MOTOR_STAR_DELTA":
            wires.extend([
                LadderWireRowDTO(
                    wire_no=f"-{w_base + 9}", feeder_id=d.feeder_id,
                    potential_role="Star Contactor Coil Command (via Timer 15-16 & KD NC 21-22)",
                    from_pin=f"{d.timer_tag}:16",
                    to_pin=f"{d.kd_tag}:21 -> {d.ky_tag}:A1"
                ),
                LadderWireRowDTO(
                    wire_no=f"-{w_base + 10}", feeder_id=d.feeder_id,
                    potential_role="Delta Contactor Coil Command (via Timer 15-18 & KY NC 21-22)",
                    from_pin=f"{d.timer_tag}:18",
                    to_pin=f"{d.ky_tag}:21 -> {d.kd_tag}:A1"
                ),
            ])

        terminals = [
            LadderTerminalRowDTO(
                feeder_id=d.feeder_id, terminal_strip=x_strip, terminal_pin=":01",
                internal_wire_no=f"-{w_base + 2}", internal_target=f"{d.bimetal_tag or d.prot_tag}:96",
                cable_tag=w_cable, cable_spec="Control 7x1.5 mm² Cu", cable_core="Core 1",
                external_location=ext_loc, external_target=f"-S{idx}ESTOP:11"
            ),
            LadderTerminalRowDTO(
                feeder_id=d.feeder_id, terminal_strip=x_strip, terminal_pin=":02",
                internal_wire_no=f"-{w_base + 3}", internal_target=f"-S{idx}M_0_A:11",
                cable_tag=w_cable, cable_spec="Control 7x1.5 mm² Cu", cable_core="Core 2",
                external_location=ext_loc, external_target=f"-S{idx}ESTOP:12"
            ),
            LadderTerminalRowDTO(
                feeder_id=d.feeder_id, terminal_strip=x_strip, terminal_pin=":03",
                internal_wire_no=f"-{w_base + 4}", internal_target=f"-S{idx}M_0_A:14(M)",
                cable_tag=w_cable, cable_spec="Control 7x1.5 mm² Cu", cable_core="Core 3",
                external_location=ext_loc, external_target=f"-S{idx}START_LOCAL:13"
            ),
            LadderTerminalRowDTO(
                feeder_id=d.feeder_id, terminal_strip=x_strip, terminal_pin=":04",
                internal_wire_no=f"-{w_base + 6}", internal_target=f"{d.km_tag or d.vfd_tag or '-K' + str(idx)}:A1/LI1",
                cable_tag=w_cable, cable_spec="Control 7x1.5 mm² Cu", cable_core="Core 4",
                external_location=ext_loc, external_target=f"-S{idx}START_LOCAL:14"
            ),
        ]

        return {
            "wires": [w.model_dump() for w in wires],
            "terminals": [t.model_dump() for t in terminals],
        }

    @classmethod
    def render_feeder_ladder_svg(cls, d: FeederLadderDTO) -> str:
        """
        تولید نقشه اجرایی قدرت و فرمان به ازای هر فیدر (با شماره سیم‌های پویا در بیضی آبی،
        ترمینال‌های -X، کابل فرمان -W، متعلقات کلید و جدول آینه کنتاکت‌ها)
        """
        esc = lambda s: html.escape(str(s or ""))
        idx = d.feeder_index
        w_base = idx * 100
        pg = d.sheet_no
        x_strip = f"-X{idx + 1}"
        w_cable = f"-W{idx}01"
        ext_loc = f"{d.func_tag}+FIELD"

        # Dynamic Coils & Switching labels based on actual feeder load_type
        if d.load_type == "MOTOR_STAR_DELTA":
            coil_1_tag = d.km_tag or f"-K{idx}M"
            coil_1_part = d.km_part
            coil_2_tag = d.kd_tag or f"-K{idx}D"
            coil_2_part = d.kd_part
            coil_3_tag = d.ky_tag or f"-K{idx}Y"
            coil_3_part = d.ky_part
            mode_badge = f"STAR-DELTA (Y-Δ) | Ib={d.ib_a}A | IΔ={d.delta_current_a}A | IY={d.star_current_a}A"
        elif d.load_type == "MOTOR_VFD":
            coil_1_tag = d.vfd_tag or f"-U{idx}"
            coil_1_part = d.vfd_part
            coil_2_tag = f"-K{idx}EN"
            coil_2_part = "VFD Enable / LI1"
            coil_3_tag = f"-K{idx}RST"
            coil_3_part = "Fault Reset / LI2"
            mode_badge = f"VFD DRIVE CONTROL | P={d.power_kw}kW | Ib={d.ib_a}A | VFD={d.vfd_part}"
        else:
            coil_1_tag = d.km_tag or f"-K{idx}M"
            coil_1_part = d.km_part or d.prot_part
            coil_2_tag = f"-K{idx}OFF"
            coil_2_part = "Aux Status Relay"
            coil_3_tag = f"-K{idx}SD"
            coil_3_part = "Fault Trip Relay"
            mode_badge = f"{d.load_type} | P={d.power_kw}kW | Ib={d.ib_a}A | Prot={d.prot_part}"

        ol_tag = d.bimetal_tag if d.bimetal_part else d.prot_tag
        ol_part = d.bimetal_part if d.bimetal_part else f"{d.prot_part} (Int. Trip)"

        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1260 820" width="100%" height="740"
             style="background:#FAFAFA; border:2px solid #1F4E78; font-family:Consolas,Calibri,sans-serif;">
            <!-- EPLAN Sheet Header & Column Grid (1..10) -->
            <rect x="0" y="0" width="1260" height="28" fill="#1F4E78"/>
            <text x="20" y="18" fill="#FFFFFF" font-size="12" font-weight="bold">
                SHEET {pg:02d} | FEEDER {esc(d.feeder_id)} ({esc(d.func_tag)}{esc(d.loc_tag)}): {esc(d.description)} — {esc(mode_badge)}
            </text>
            <text x="760" y="18" fill="#AED6F1" font-size="11">1        2        3        4        5        6        7        8        9        10</text>

            <!-- Left 3-Phase Power Branch (-1L1, -1L2, -1L3, PE) -->
            <text x="55" y="48" fill="#1F4E78" font-size="11" font-weight="bold">L1</text>
            <text x="85" y="48" fill="#1F4E78" font-size="11" font-weight="bold">L2</text>
            <text x="115" y="48" fill="#1F4E78" font-size="11" font-weight="bold">L3</text>
            <line x1="60" y1="55" x2="60" y2="380" stroke="#E74C3C" stroke-width="2"/>
            <line x1="90" y1="55" x2="90" y2="380" stroke="#E74C3C" stroke-width="2"/>
            <line x1="120" y1="55" x2="120" y2="380" stroke="#E74C3C" stroke-width="2"/>
            <line x1="60" y1="450" x2="60" y2="710" stroke="#E74C3C" stroke-width="2"/>
            <line x1="90" y1="450" x2="90" y2="710" stroke="#E74C3C" stroke-width="2"/>
            <line x1="120" y1="450" x2="120" y2="710" stroke="#E74C3C" stroke-width="2"/>

            <!-- Dashed Apparatus Box for Feeder Breaker & Aux Contacts -->
            <rect x="42" y="365" width="320" height="105" fill="none" stroke="#34568B" stroke-width="1.4" stroke-dasharray="6,4"/>
            <text x="48" y="358" fill="#1F4E78" font-size="11" font-weight="bold">{esc(d.prot_tag)} ({esc(d.prot_part)} | In={esc(d.prot_in_a)}A)</text>
            <text x="51" y="382" fill="#1F4E78" font-size="9">1</text><text x="51" y="462" fill="#1F4E78" font-size="9">2</text>
            <text x="81" y="382" fill="#1F4E78" font-size="9">3</text><text x="81" y="462" fill="#1F4E78" font-size="9">4</text>
            <text x="111" y="382" fill="#1F4E78" font-size="9">5</text><text x="111" y="462" fill="#1F4E78" font-size="9">6</text>
            <line x1="60" y1="380" x2="50" y2="440" stroke="#1F4E78" stroke-width="2"/>
            <line x1="90" y1="380" x2="80" y2="440" stroke="#1F4E78" stroke-width="2"/>
            <line x1="120" y1="380" x2="110" y2="440" stroke="#1F4E78" stroke-width="2"/>
            <line x1="55" y1="415" x2="340" y2="415" stroke="#34568B" stroke-width="1.2" stroke-dasharray="4,4"/>

            <!-- Outgoing Power Cable & Motor/Load Symbol -->
            <line x1="50" y1="600" x2="135" y2="585" stroke="#16A085" stroke-width="1.8"/>
            <text x="142" y="592" fill="#0F766E" font-size="10" font-weight="bold">-W{idx} ({esc(d.power_cable_str)})</text>
            <circle cx="90" cy="735" r="24" fill="#F0FDF4" stroke="#15803D" stroke-width="2"/>
            <text x="90" y="733" fill="#15803D" font-size="11" font-weight="bold" text-anchor="middle">{esc(d.feeder_id)}</text>
            <text x="90" y="747" fill="#15803D" font-size="9.5" text-anchor="middle">{esc(d.power_kw)}kW</text>

            <!-- =================================================================== -->
            <!-- 24VDC PELV CONTROL RAILS (Top L+ Rail & Bottom M 0V Rail)           -->
            <!-- =================================================================== -->
            <line x1="230" y1="95" x2="1200" y2="95" stroke="#C0392B" stroke-width="2"/>
            <text x="235" y="84" fill="#C0392B" font-size="11" font-weight="bold">
                L+ (+24VDC from {esc(d.psu_part)} / -F0:OUT{min(4, idx)})
            </text>
            <!-- Wire Oval -(w_base+1) -->
            <ellipse cx="395" cy="87" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="395" y="91" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 1}</text>

            <!-- Bottom 0VDC Return Rail -->
            <line x1="230" y1="675" x2="1200" y2="675" stroke="#1F618D" stroke-width="2"/>
            <text x="235" y="692" fill="#1F618D" font-size="11" font-weight="bold">M (0VDC Common Return — Grounded to PE Bar)</text>

            <!-- =================================================================== -->
            <!-- RUNG 1 & 2: Aux Contacts Inside Breaker (13-14 Status & 97-98 Trip) -->
            <!-- =================================================================== -->
            <line x1="260" y1="95" x2="260" y2="390" stroke="#E74C3C" stroke-width="1.6"/>
            <text x="250" y="388" fill="#1F4E78" font-size="9">13</text>
            <line x1="260" y1="390" x2="248" y2="435" stroke="#1F4E78" stroke-width="1.8"/>
            <text x="250" y="450" fill="#1F4E78" font-size="9">14</text>
            <line x1="260" y1="438" x2="260" y2="590" stroke="#E74C3C" stroke-width="1.6"/>

            <line x1="335" y1="95" x2="335" y2="390" stroke="#E74C3C" stroke-width="1.6"/>
            <text x="322" y="388" fill="#C0392B" font-size="9">97</text>
            <line x1="335" y1="390" x2="323" y2="435" stroke="#C0392B" stroke-width="1.8"/>
            <text x="322" y="450" fill="#C0392B" font-size="9">98</text>
            <line x1="335" y1="438" x2="335" y2="590" stroke="#E74C3C" stroke-width="1.6"/>

            <!-- =================================================================== -->
            <!-- RUNG 3: Overload 95-96 -> Terminal -X:01/:02 -> Field Cable -W      -->
            <!-- =================================================================== -->
            <line x1="510" y1="95" x2="510" y2="145" stroke="#E74C3C" stroke-width="1.6"/>
            <text x="498" y="142" fill="#1F4E78" font-size="9.5">95</text>
            <line x1="510" y1="145" x2="498" y2="180" stroke="#1F4E78" stroke-width="2"/>
            <text x="498" y="192" fill="#1F4E78" font-size="9.5">96</text>
            <text x="488" y="165" fill="#1F4E78" font-size="10.5" font-weight="bold" text-anchor="end">{esc(ol_tag)}</text>
            <text x="488" y="178" fill="#4B5563" font-size="9" text-anchor="end">{esc(ol_part)}</text>

            <line x1="510" y1="182" x2="510" y2="235" stroke="#E74C3C" stroke-width="1.6"/>
            <!-- Wire Oval -(w_base+2) -->
            <ellipse cx="482" cy="208" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="482" y="212" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 2}</text>

            <!-- Terminal Strip Pin :01 & Multi-core Cable Slash Core 1 -->
            <circle cx="510" cy="235" r="4" fill="#FFF" stroke="#8E244D" stroke-width="1.8"/>
            <text x="498" y="238" fill="#8E244D" font-size="10" font-weight="bold" text-anchor="end">{esc(x_strip)}</text>
            <text x="518" y="238" fill="#8E244D" font-size="10">:01</text>
            <line x1="502" y1="255" x2="518" y2="245" stroke="#8E244D" stroke-width="1.6"/>
            <text x="495" y="255" fill="#8E244D" font-size="10.5" font-weight="bold" text-anchor="end">{esc(w_cable)}</text>
            <text x="524" y="255" fill="#8E244D" font-size="9.5" font-weight="bold">Core 1</text>

            <!-- Dashed External Field Box (+FIELD E-Stop) -->
            <rect x="445" y="265" width="130" height="82" fill="none" stroke="#8E244D" stroke-width="1.3" stroke-dasharray="5,3"/>
            <text x="582" y="310" fill="#8E244D" font-size="11" font-weight="bold">{esc(ext_loc)}</text>
            <line x1="510" y1="239" x2="510" y2="288" stroke="#E74C3C" stroke-width="1.6"/>
            <text x="498" y="286" fill="#C0392B" font-size="9">11</text>
            <line x1="510" y1="288" x2="498" y2="320" stroke="#C0392B" stroke-width="2"/>
            <text x="498" y="332" fill="#C0392B" font-size="9">12</text>
            <text x="490" y="308" fill="#C0392B" font-size="10" font-weight="bold" text-anchor="end">-S{idx}ESTOP</text>
            <line x1="510" y1="322" x2="510" y2="365" stroke="#E74C3C" stroke-width="1.6"/>

            <!-- Return Terminal :02 & Core 2 -->
            <line x1="502" y1="360" x2="518" y2="350" stroke="#8E244D" stroke-width="1.6"/>
            <text x="524" y="358" fill="#8E244D" font-size="9.5" font-weight="bold">Core 2</text>
            <circle cx="510" cy="372" r="4" fill="#FFF" stroke="#8E244D" stroke-width="1.8"/>
            <text x="498" y="375" fill="#8E244D" font-size="10" font-weight="bold" text-anchor="end">{esc(x_strip)}</text>
            <text x="518" y="375" fill="#8E244D" font-size="10">:02</text>

            <!-- Wire Oval -(w_base+3) to Hand-Off-Auto Selector -->
            <line x1="510" y1="376" x2="510" y2="415" stroke="#E74C3C" stroke-width="1.6"/>
            <line x1="510" y1="415" x2="680" y2="415" stroke="#E74C3C" stroke-width="1.6"/>
            <ellipse cx="595" cy="405" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="595" y="409" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 3}</text>

            <!-- Selector Switch -S{idx}M-0-A (Manual vs Auto PLC) -->
            <text x="435" y="452" fill="#1F4E78" font-size="10.5" font-weight="bold">-S{idx}M-0-A</text>
            <text x="502" y="438" fill="#1F4E78" font-size="10" font-weight="bold">M</text>
            <text x="592" y="438" fill="#1F4E78" font-size="10" font-weight="bold">0</text>
            <text x="672" y="438" fill="#1F4E78" font-size="10" font-weight="bold">A</text>
            <line x1="510" y1="415" x2="510" y2="442" stroke="#E74C3C" stroke-width="1.6"/>
            <line x1="510" y1="442" x2="498" y2="472" stroke="#1F4E78" stroke-width="1.8"/>
            <line x1="680" y1="415" x2="680" y2="442" stroke="#E74C3C" stroke-width="1.6"/>
            <line x1="680" y1="442" x2="668" y2="472" stroke="#1F4E78" stroke-width="1.8"/>
            <line x1="504" y1="456" x2="674" y2="456" stroke="#34568B" stroke-width="1.2" stroke-dasharray="4,4"/>

            <!-- Manual Start Pushbutton (-S_START) & Auto PLC Relay Contact (-K_DO) -->
            <line x1="510" y1="474" x2="510" y2="515" stroke="#E74C3C" stroke-width="1.6"/>
            <ellipse cx="482" cy="495" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="482" y="499" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 4}</text>
            <line x1="510" y1="515" x2="498" y2="545" stroke="#1F4E78" stroke-width="1.8"/>
            <text x="490" y="535" fill="#1F4E78" font-size="10" font-weight="bold" text-anchor="end">-S{idx}START</text>
            <line x1="510" y1="547" x2="510" y2="575" stroke="#E74C3C" stroke-width="1.6"/>

            <line x1="680" y1="474" x2="680" y2="515" stroke="#E74C3C" stroke-width="1.6"/>
            <ellipse cx="712" cy="495" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="712" y="499" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 5}</text>
            <line x1="680" y1="515" x2="668" y2="545" stroke="#1E8449" stroke-width="2"/>
            <text x="662" y="532" fill="#1E8449" font-size="10" font-weight="bold" text-anchor="end">-K_DO{idx} (11-14)</text>
            <text x="662" y="545" fill="#1E8449" font-size="9" text-anchor="end">/PLC.%Q0.{idx}</text>
            <line x1="680" y1="547" x2="680" y2="575" stroke="#E74C3C" stroke-width="1.6"/>

            <!-- Join Manual & Auto Branches -> Wire -(w_base+6) to Main Coil -->
            <line x1="510" y1="575" x2="830" y2="575" stroke="#E74C3C" stroke-width="1.6"/>
            <line x1="595" y1="575" x2="595" y2="600" stroke="#E74C3C" stroke-width="1.6"/>
            <ellipse cx="600" cy="563" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="600" y="567" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 6}</text>

            <!-- =================================================================== -->
            <!-- RUNG 6 & 7: Status Feedbacks to Lamps & PLC DI (Wires +7 & +8)      -->
            <!-- =================================================================== -->
            <line x1="980" y1="95" x2="980" y2="260" stroke="#E74C3C" stroke-width="1.6"/>
            <text x="970" y="255" fill="#1F4E78" font-size="9">13</text>
            <line x1="980" y1="260" x2="968" y2="295" stroke="#1F4E78" stroke-width="1.8"/>
            <text x="970" y="308" fill="#1F4E78" font-size="9">14</text>
            <text x="960" y="280" fill="#1F4E78" font-size="10" font-weight="bold" text-anchor="end">{esc(coil_1_tag)}</text>
            <text x="960" y="293" fill="#1E8449" font-size="9" text-anchor="end">/{pg:02d}.5:C</text>
            <line x1="980" y1="298" x2="980" y2="600" stroke="#E74C3C" stroke-width="1.6"/>
            <ellipse cx="980" cy="425" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="980" y="429" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 7}</text>

            <line x1="1120" y1="95" x2="1120" y2="260" stroke="#E74C3C" stroke-width="1.6"/>
            <text x="1110" y="255" fill="#C0392B" font-size="9">97</text>
            <line x1="1120" y1="260" x2="1108" y2="295" stroke="#C0392B" stroke-width="1.8"/>
            <text x="1110" y="308" fill="#C0392B" font-size="9">98</text>
            <text x="1100" y="280" fill="#C0392B" font-size="10" font-weight="bold" text-anchor="end">{esc(ol_tag)}</text>
            <line x1="1120" y1="298" x2="1120" y2="600" stroke="#E74C3C" stroke-width="1.6"/>
            <ellipse cx="1120" cy="425" rx="22" ry="10" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="1120" y="429" fill="#000" font-size="10.5" font-weight="bold" text-anchor="middle">-{w_base + 8}</text>

            <!-- =================================================================== -->
            <!-- BOTTOM COILS & LAMPS ROW (With EPLAN Yellow Highlight Circles)      -->
            <!-- =================================================================== -->
            <!-- Aux Status Coil 2 -->
            <circle cx="260" cy="625" r="34" fill="#F1C40F" opacity="0.85"/>
            <rect x="244" y="614" width="32" height="22" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="238" y="628" fill="#000" font-size="10" font-weight="bold" text-anchor="end">{esc(coil_2_tag)}</text>
            <text x="263" y="611" fill="#000" font-size="8.5">A1</text><text x="263" y="648" fill="#000" font-size="8.5">A2</text>
            <line x1="260" y1="636" x2="260" y2="675" stroke="#1F618D" stroke-width="1.6"/>

            <!-- Aux Trip Coil 3 -->
            <circle cx="335" cy="625" r="34" fill="#F1C40F" opacity="0.85"/>
            <rect x="319" y="614" width="32" height="22" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="313" y="628" fill="#000" font-size="10" font-weight="bold" text-anchor="end">{esc(coil_3_tag)}</text>
            <text x="338" y="611" fill="#000" font-size="8.5">A1</text><text x="338" y="648" fill="#000" font-size="8.5">A2</text>
            <line x1="335" y1="636" x2="335" y2="675" stroke="#1F618D" stroke-width="1.6"/>

            <!-- Main Contactor / VFD Command Coil 1 -->
            <circle cx="595" cy="625" r="38" fill="#F1C40F" opacity="0.88"/>
            <rect x="576" y="614" width="38" height="22" fill="#FFF" stroke="#1F4E78" stroke-width="1.8"/>
            <text x="570" y="625" fill="#000" font-size="10.5" font-weight="bold" text-anchor="end">{esc(coil_1_tag)}</text>
            <text x="570" y="638" fill="#1F4E78" font-size="8.5" text-anchor="end">{esc(coil_1_part)}</text>
            <text x="598" y="611" fill="#000" font-size="8.5">A1</text><text x="598" y="648" fill="#000" font-size="8.5">A2</text>
            <line x1="595" y1="636" x2="595" y2="675" stroke="#1F618D" stroke-width="1.6"/>

            <!-- Star-Delta Timer / Secondary Branch at X=830 -->
            <line x1="830" y1="575" x2="830" y2="614" stroke="#E74C3C" stroke-width="1.6"/>
            <circle cx="830" cy="625" r="34" fill="#F1C40F" opacity="0.85"/>
            <rect x="814" y="614" width="32" height="22" fill="#FFF" stroke="#1F4E78" stroke-width="1.5"/>
            <text x="808" y="628" fill="#000" font-size="10" font-weight="bold" text-anchor="end">{esc(d.timer_tag or f"-KT{idx}")}</text>
            <line x1="830" y1="636" x2="830" y2="675" stroke="#1F618D" stroke-width="1.6"/>

            <!-- Run Lamp & PLC DI -->
            <circle cx="980" cy="625" r="28" fill="#F1C40F" opacity="0.85"/>
            <circle cx="980" cy="625" r="11" fill="#E9F7EF" stroke="#1E8449" stroke-width="1.8"/>
            <text x="962" y="628" fill="#1E8449" font-size="9.5" font-weight="bold" text-anchor="end">-H{idx}ON (RUN)</text>
            <line x1="980" y1="636" x2="980" y2="675" stroke="#1F618D" stroke-width="1.6"/>

            <!-- Trip Lamp & PLC DI -->
            <circle cx="1120" cy="625" r="28" fill="#F1C40F" opacity="0.85"/>
            <circle cx="1120" cy="625" r="11" fill="#FDEDEC" stroke="#C0392B" stroke-width="1.8"/>
            <text x="1102" y="628" fill="#C0392B" font-size="9.5" font-weight="bold" text-anchor="end">-H{idx}TRIP (FAULT)</text>
            <line x1="1120" y1="636" x2="1120" y2="675" stroke="#1F618D" stroke-width="1.6"/>

            <!-- =================================================================== -->
            <!-- CONTACT MIRROR TABLES AT BOTTOM (Cross-References per Coil)         -->
            <!-- =================================================================== -->
            <text x="565" y="725" fill="#1F4E78" font-size="9.5" font-weight="bold">1-2, 3-4, 5-6</text>
            <text x="640" y="725" fill="#1E8449" font-size="9.5">/{pg:02d}.1:B (Power)</text>
            <text x="565" y="740" fill="#1F4E78" font-size="9.5" font-weight="bold">13-14 (NO)</text>
            <text x="640" y="740" fill="#1E8449" font-size="9.5">/{pg:02d}.8:B (Run FB)</text>
            <text x="565" y="755" fill="#1F4E78" font-size="9.5" font-weight="bold">21-22 (NC)</text>
            <text x="640" y="755" fill="#1E8449" font-size="9.5">/{pg:02d}.6:B (Interlock)</text>
        </svg>
        """.strip()


def generate_ladder_svg(feeder_dto: FeederLadderDTO) -> str:
    """تابع استاندارد ورودی برای فراخوانی مستقیم از gui_output_bridge.py"""
    return IECLadderSvgGenerator.render_feeder_ladder_svg(feeder_dto)