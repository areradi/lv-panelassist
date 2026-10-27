# -*- coding: utf-8 -*-
"""
IEC 60617 / EPLAN-style ladder control-circuit SVG renderer.
True ladder topology: potential rails, orthogonal rungs, standard symbols,
terminal numbers, device tags, junction dots, cross-references.
"""

PAGE_W, PAGE_H = 1040, 540
RAIL_TOP, RAIL_BOT = 90, 470
X0, X1 = 70, 1000
FONT = "Segoe UI, Tahoma, sans-serif"


def _wv(x, y1, y2, w=1.3):
    return f"<line x1='{x}' y1='{y1}' x2='{x}' y2='{y2}' stroke='#000' stroke-width='{w}'/>"


def _wh(x1, x2, y, w=1.3):
    return f"<line x1='{x1}' y1='{y}' x2='{x2}' y2='{y}' stroke='#000' stroke-width='{w}'/>"


def _dot(x, y):
    return f"<circle cx='{x}' cy='{y}' r='2.7' fill='#000'/>"


def _txt(x, y, s, size=9, anchor="start", bold=False, color="#000"):
    b = " font-weight='bold'" if bold else ""
    return (f"<text x='{x}' y='{y}' font-size='{size}' fill='{color}' "
            f"text-anchor='{anchor}'{b} font-family='{FONT}'>{s}</text>")


def contact(x, y, nc=False, act=None, t_top="", t_bot="", tag="", desc=""):
    """NO/NC contact on vertical wire. act: None|'pb'|'sel'|'em'."""
    s = _wh(x - 7, x + 7, y - 6, 1.7) + _wh(x - 7, x + 7, y + 6, 1.7)
    if nc:
        s += f"<line x1='{x - 9}' y1='{y + 9}' x2='{x + 9}' y2='{y - 9}' stroke='#000' stroke-width='1.4'/>"
    if act == "pb":
        s += f"<line x1='{x + 9}' y1='{y - 1}' x2='{x + 16}' y2='{y - 9}' stroke='#000' stroke-width='1.2'/>"
        s += _wh(x + 12, x + 20, y - 9, 1.2)
    elif act == "sel":
        s += f"<path d='M {x + 9} {y - 8} q 7 8 0 16' fill='none' stroke='#000' stroke-width='1.2'/>"
    elif act == "em":
        s += f"<path d='M {x + 9} {y - 6} a 6 6 0 0 1 0 12 z' fill='#000'/>"
    if t_top:
        s += _txt(x + 10, y - 9, t_top, 8)
    if t_bot:
        s += _txt(x + 10, y + 16, t_bot, 8)
    if tag:
        s += _txt(x - 12, y + 3, tag, 9.5, anchor="end", bold=True)
    if desc:
        s += _txt(x - 12, y + 14, desc, 7.5, anchor="end", color="#555")
    return s


def coil(x, y, tag="", desc=""):
    s = f"<rect x='{x - 11}' y='{y - 13}' width='22' height='26' fill='#fff' stroke='#000' stroke-width='1.7'/>"
    s += _txt(x + 14, y - 5, "A1", 8) + _txt(x + 14, y + 13, "A2", 8)
    if tag:
        s += _txt(x - 15, y + 3, tag, 9.5, anchor="end", bold=True)
    if desc:
        s += _txt(x - 15, y + 14, desc, 7.5, anchor="end", color="#555")
    return s


def lamp(x, y, tag="", color=""):
    s = f"<circle cx='{x}' cy='{y}' r='9.5' fill='#fff' stroke='#000' stroke-width='1.6'/>"
    s += f"<line x1='{x - 6.5}' y1='{y - 6.5}' x2='{x + 6.5}' y2='{y + 6.5}' stroke='#000' stroke-width='1.2'/>"
    s += f"<line x1='{x - 6.5}' y1='{y + 6.5}' x2='{x + 6.5}' y2='{y - 6.5}' stroke='#000' stroke-width='1.2'/>"
    if tag:
        s += _txt(x - 13, y + 3, tag, 9.5, anchor="end", bold=True)
    if color:
        s += _txt(x + 13, y + 3, color, 8, bold=True)
    return s


def xref_down(x, y, label):
    s = _wv(x, y, y + 12)
    s += f"<path d='M {x - 4.5} {y + 12} L {x + 4.5} {y + 12} L {x} {y + 21} Z' fill='#000'/>"
    s += _txt(x, y + 33, label, 8, anchor="middle", color="#1F4E78")
    return s


def xref_up(x, y, label):
    s = _wv(x, y - 12, y)
    s += f"<path d='M {x - 4.5} {y - 12} L {x + 4.5} {y - 12} L {x} {y - 21} Z' fill='#000'/>"
    s += _txt(x, y - 26, label, 8, anchor="middle", color="#1F4E78")
    return s


def render_control_circuit_ladder(feeder_tag="=PUMP1+MCC1", panel_tag="+MCC1", page_no="CC-01"):
    p = []
    # header
    p.append(_txt(X0, 34, f"{feeder_tag}  -  Control Circuit / Steuerstromkreis (IEC 60617-2, 24V DC PELV)", 12, bold=True))
    p.append(_txt(X1, 34, f"Page {page_no} | Scale NT | LV-PanelAssist", 9, anchor="end", color="#555"))
    p.append(_wh(X0, X1, 44, 0.8))
    # rails
    p.append(_wh(X0, X1, RAIL_TOP, 2.2))
    p.append(_wh(X0, X1, RAIL_BOT, 2.2))
    p.append(_txt(X0 + 60, RAIL_TOP - 8, "L+   +24 V DC (PELV)", 9.5, bold=True))
    p.append(_txt(X0, RAIL_BOT + 16, "M    0 V DC  (IEC 60204-1 9.4.2)", 9.5, bold=True))
    p.append(xref_up(X0 + 30, RAIL_TOP, "=CTRL" + panel_tag + " -F0 / 2.1"))
    # rung numbers
    for n, rx in enumerate([150, 690, 790, 890], start=1):
        p.append(_txt(rx - 10, RAIL_TOP + 14, str(n), 8.5, anchor="middle", color="#1F4E78", bold=True))

    # ---- rung 1: main command chain
    x = 150
    p.append(_wv(x, RAIL_TOP, 144)); p.append(_dot(x, RAIL_TOP))
    p.append(contact(x, 150, nc=True, t_top="95", t_bot="96", tag="-F1", desc="OL TRIP"))
    p.append(_wv(x, 156, 204))
    p.append(contact(x, 210, nc=True, act="em", t_top="11", t_bot="12", tag="-S0", desc="E-STOP"))
    p.append(_wv(x, 216, 250))
    p.append(_wh(x, 450, 250))
    p.append(_txt(x + 6, 246, "+1NW", 8, color="#1F4E78"))

    xh, xk, xa, xc = 250, 330, 450, 560
    # hand branch + start/hold parallel
    p.append(_wv(xh, 250, 284)); p.append(_dot(xh, 250))
    p.append(contact(xh, 290, act="sel", t_top="1", t_bot="2", tag="-S1", desc="HAND"))
    p.append(_wv(xh, 296, 330))
    p.append(_wh(xh, xk, 330))
    p.append(_wv(xh, 330, 354))
    p.append(contact(xh, 360, act="pb", t_top="13", t_bot="14", tag="-S2", desc="START"))
    p.append(_wv(xh, 366, 390)); p.append(_dot(xh, 390))
    p.append(_wv(xk, 330, 354)); p.append(_dot(xk, 330))
    p.append(contact(xk, 360, t_top="13", t_bot="14", tag="-K1M", desc="SELF-HOLD"))
    p.append(_wv(xk, 366, 390)); p.append(_dot(xk, 390))
    p.append(_wh(xh, xc, 390))
    # auto branch + PLC coupling relay
    p.append(_wv(xa, 250, 284))
    p.append(contact(xa, 290, act="sel", t_top="1", t_bot="4", tag="-S1", desc="AUTO"))
    p.append(_wv(xa, 296, 354))
    p.append(contact(xa, 360, t_top="13", t_bot="14", tag="-K_DO1", desc="PLC CMD"))
    p.append(_wv(xa, 366, 390)); p.append(_dot(xa, 390))
    p.append(f"<rect x='{xa - 26}' y='338' width='52' height='44' fill='none' stroke='#888' stroke-width='0.9' stroke-dasharray='4 3'/>")
    p.append(_txt(xa, 398, "=PLC COUPLING", 7, anchor="middle", color="#888"))
    # coil
    p.append(_wv(xc, 390, 407))
    p.append(coil(xc, 420, tag="-K1M", desc="MAIN CONTACTOR"))
    p.append(_wv(xc, 433, RAIL_BOT)); p.append(_dot(xc, RAIL_BOT))

    # ---- rung 2: run lamp
    x = 690
    p.append(_wv(x, RAIL_TOP, 154)); p.append(_dot(x, RAIL_TOP))
    p.append(contact(x, 160, t_top="13", t_bot="14", tag="-K1M", desc="AUX"))
    p.append(_wv(x, 166, 290.5))
    p.append(lamp(x, 300, tag="-H1", color="GN"))
    p.append(_wv(x, 309.5, RAIL_BOT)); p.append(_dot(x, RAIL_BOT))

    # ---- rung 3: run feedback to PLC
    x = 790
    p.append(_wv(x, RAIL_TOP, 154)); p.append(_dot(x, RAIL_TOP))
    p.append(contact(x, 160, t_top="23", t_bot="24", tag="-K1M", desc="AUX"))
    p.append(_wv(x, 166, 300))
    p.append(xref_down(x, 300, "=PLC -A1.1 / X_DI:2 (%I0.0)"))

    # ---- rung 4: trip lamp + tap to PLC
    x = 890
    p.append(_wv(x, RAIL_TOP, 154)); p.append(_dot(x, RAIL_TOP))
    p.append(contact(x, 160, t_top="97", t_bot="98", tag="-F1", desc="OL TRIP"))
    p.append(_wv(x, 166, 290.5))
    p.append(_dot(x, 240))
    p.append(_wh(x, 970, 240))
    p.append(lamp(x, 300, tag="-H2", color="RD"))
    p.append(_wv(x, 309.5, RAIL_BOT)); p.append(_dot(x, RAIL_BOT))
    x = 970
    p.append(_wv(x, 240, 300))
    p.append(xref_down(x, 300, "=PLC -A1.1 / X_DI:3 (%I0.1)"))

    # footer notes
    p.append(_txt(X0, RAIL_BOT + 34, "-W1..: field wiring LiYY 3x0.75 mm2 / LiYCY 2x2x0.75 mm2 (AI) - see terminal schedule", 8, color="#555"))
    p.append(_txt(X0, RAIL_BOT + 46, "Coil side connected to M rail per IEC 60204-1 9.4.2.1", 8, color="#555"))

    body = "".join(p)
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {PAGE_W} {PAGE_H}' "
            f"width='{PAGE_W}' height='{PAGE_H}'>"
            f"<rect x='0' y='0' width='{PAGE_W}' height='{PAGE_H}' fill='#ffffff'/>"
            f"{body}</svg>")
