# -*- coding: utf-8 -*-
# IEC 60617 / EPLAN-style Single-Line Diagram (SLD) + engineering tables (dynamic v2)

FONT = "Segoe UI, Tahoma, sans-serif"

MARGIN_L = 60
MARGIN_R = 60
MIN_PAGE_W = 1180
MIN_SLOT_W = 168
MAX_SLOT_W = 260
BUS_LEFT_EXTRA = 112
BUS_RIGHT_EXTRA = 96

TITLE_Y = 40
RULE_Y = 50
SUPPLY_Y = 66
INC_LABEL_Y = 118
INC_BRK_Y = 162
BUS_Y = 212
BRK_Y = 256
CT_Y = 304
CABLE_TOP = 328
CABLE_H = 30
LOAD_Y = 430
PE_Y = 486
SPD_Y = 268
SPD_EARTH_Y = 312
TABLE_START_Y = 548
ROW_H = 20
HEAD_H = 22
TABLE_GAP = 26


def _attr(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get(obj, *keys, default=None):
    for k in keys:
        v = _attr(obj, k, None)
        if v is not None and v != "":
            return v
    return default


def _str(v):
    if v is None:
        return ""
    return str(v)


def _num(v, d=1):
    try:
        x = float(v)
        if abs(x - round(x)) < 1e-9:
            return str(int(round(x)))
        return f"{x:.{d}f}"
    except Exception:
        return _str(v)


def _clip(s, n):
    s = _str(s)
    n = int(n)
    if n <= 3:
        return s[:n]
    return s if len(s) <= n else s[: n - 3] + "..."


def _wv(x, y1, y2, w=1.2):
    return f"<line x1='{x}' y1='{y1}' x2='{x}' y2='{y2}' stroke='#000' stroke-width='{w}'/>"


def _wh(x1, x2, y, w=1.2):
    return f"<line x1='{x1}' y1='{y}' x2='{x2}' y2='{y}' stroke='#000' stroke-width='{w}'/>"


def _dot(x, y, r=2.4):
    return f"<circle cx='{x}' cy='{y}' r='{r}' fill='#000'/>"


def _txt(x, y, s, size=8.5, anchor="start", bold=False, color="#000"):
    b = " font-weight='bold'" if bold else ""
    return (
        f"<text x='{x}' y='{y}' font-size='{size}' fill='{color}' "
        f"text-anchor='{anchor}'{b} font-family='{FONT}'>{_str(s)}</text>"
    )


def _rect(x, y, w, h, fill="#fff", stroke="#000", sw=1.2, dash=None):
    d = f" stroke-dasharray='{dash}'" if dash else ""
    return (
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' "
        f"stroke='{stroke}' stroke-width='{sw}'{d}/>"
    )


def _earth(x, y):
    s = _wv(x, y, y + 8)
    s += _wh(x - 9, x + 9, y + 8)
    s += _wh(x - 6, x + 6, y + 12)
    s += _wh(x - 3, x + 3, y + 16)
    return s


def _breaker(x, y, tag, in_a, sub=""):
    s = _dot(x, y - 12) + _dot(x, y + 12)
    s += f"<line x1='{x - 7}' y1='{y + 7}' x2='{x + 7}' y2='{y - 7}' stroke='#000' stroke-width='1.6'/>"
    s += _rect(x - 16, y - 6, 9, 12, fill="#fff", sw=1.2)
    s += _txt(x - 19, y + 3, "TRIP", 6, anchor="end", color="#444")
    s += _txt(x + 11, y - 2, tag, 9, bold=True)
    s += _txt(x + 11, y + 9, f"{_num(in_a, 0)} A", 8)
    if sub:
        s += _txt(x + 11, y + 19, sub, 7, color="#555")
    return s


def _fuse(x, y, tag, in_a):
    s = _dot(x, y - 12) + _dot(x, y + 12)
    s += _rect(x - 4, y - 10, 8, 20, fill="#fff", sw=1.3)
    s += _wv(x, y - 10, y + 10, 1.0)
    s += _txt(x + 9, y - 2, tag, 9, bold=True)
    s += _txt(x + 9, y + 9, f"{_num(in_a, 0)} A", 8)
    return s


def _ct(x, y, tag):
    s = f"<circle cx='{x}' cy='{y}' r='8.5' fill='#fff' stroke='#000' stroke-width='1.3'/>"
    s += _wh(x - 8, x + 8, y, 1.0)
    s += _txt(x + 11, y + 3, tag, 8.5, bold=True)
    return s


def _load(x, y, kind, kw, tag, desc):
    kind = _str(kind).upper()
    kw_txt = _num(kw, 1)

    if kind in ("MOTOR_DOL", "MOTOR_STAR_DELTA", "MOTOR_SOFT"):
        s = f"<circle cx='{x}' cy='{y}' r='14' fill='#fff' stroke='#000' stroke-width='1.5'/>"
        s += _txt(x, y + 4, "M", 12, anchor="middle", bold=True)
        s += _txt(x, y + 26, "3~", 8, anchor="middle")
        s += _txt(x, y - 20, f"{kw_txt} kW", 8, anchor="middle", color="#333")

    elif kind == "MOTOR_VFD":
        s = _rect(x - 16, y - 50, 32, 22, fill="#fff", sw=1.3)
        s += _txt(x, y - 36, "VFD", 8, anchor="middle", bold=True)
        s += _wv(x, y - 28, y - 14)
        s += f"<circle cx='{x}' cy='{y}' r='14' fill='#fff' stroke='#000' stroke-width='1.5'/>"
        s += _txt(x, y + 4, "M", 12, anchor="middle", bold=True)
        s += _txt(x, y + 26, "3~", 8, anchor="middle")
        s += _txt(x, y - 56, f"{kw_txt} kW", 8, anchor="middle", color="#333")

    elif kind == "LIGHTING":
        s = f"<circle cx='{x}' cy='{y}' r='12' fill='#fff' stroke='#000' stroke-width='1.5'/>"
        s += f"<line x1='{x - 8}' y1='{y - 8}' x2='{x + 8}' y2='{y + 8}' stroke='#000' stroke-width='1.2'/>"
        s += f"<line x1='{x - 8}' y1='{y + 8}' x2='{x + 8}' y2='{y - 8}' stroke='#000' stroke-width='1.2'/>"
        s += _txt(x, y + 24, f"{kw_txt} kW", 8, anchor="middle", color="#333")

    elif kind == "CAP_BANK":
        s = _rect(x - 14, y - 12, 28, 24, fill="#fff", sw=1.5)
        s += _wh(x - 8, x + 8, y - 4, 1.4)
        s += _wh(x - 8, x + 8, y + 4, 1.4)
        s += _txt(x, y + 26, f"{kw_txt} kvar", 8, anchor="middle", color="#333")

    else:
        s = _rect(x - 16, y - 12, 32, 24, fill="#fff", sw=1.4)
        s += _txt(x, y + 4, "LOAD", 8, anchor="middle", bold=True)

    s += _txt(x - 18, y + 3, tag, 9, anchor="end", bold=True)
    s += _txt(x, y + 40, _clip(desc, 22), 7.5, anchor="middle", color="#555")
    return s


def _spd(x, y, cls, up):
    s = _rect(x - 13, y - 9, 26, 18, fill="#fff", sw=1.4)
    s += _txt(x, y + 3, "SPD", 8, anchor="middle", bold=True)
    s += f"<line x1='{x + 9}' y1='{y - 6}' x2='{x + 16}' y2='{y + 2}' stroke='#000' stroke-width='1.2'/>"
    s += _txt(x + 18, y + 3, cls, 8, bold=True)
    s += _txt(x, y - 14, f"Up {up}", 7.5, anchor="middle", color="#333")
    return s


def _signal_kind(sig):
    s = _str(sig).upper()
    if "AO" in s:
        return "AO"
    if "AI" in s:
        return "AI"
    if "DO" in s or "SOLENOID" in s or ("ACTUATOR" in s and "AO" not in s):
        return "DO"
    if "DI" in s or "SENSOR" in s:
        return "DI"
    return "DI"


def _addr_di(i):
    return f"%I{i // 8}.{i % 8}"


def _addr_do(i):
    return f"%Q{i // 8}.{i % 8}"


def _addr_ai(i):
    return f"%IW{64 + i * 2}"


def _addr_ao(i):
    return f"%QW{128 + i * 2}"


def _load_kind(value):
    s = _str(value).upper()
    if "VFD" in s or "DRIVE" in s or "INVERTER" in s:
        return "MOTOR_VFD"
    if "STAR" in s or "DELTA" in s or "YD" in s:
        return "MOTOR_STAR_DELTA"
    if "SOFT" in s:
        return "MOTOR_SOFT"
    if "MOTOR" in s or "DOL" in s or "PUMP" in s or "FAN" in s or "COMPRESSOR" in s:
        return "MOTOR_DOL"
    if "LIGHT" in s:
        return "LIGHTING"
    if "CAP" in s or "KVAR" in s or "PF" in s:
        return "CAP_BANK"
    return "OTHER"


def _feeder_view(f, i):
    load_raw = _get(f, "load_type", "load", "device_type", default="")
    kind = _load_kind(load_raw)

    dev_raw = _str(_get(f, "device_type", "dev", default="BREAKER")).upper()
    dev = "FUSE" if "FUSE" in dev_raw else "BREAKER"

    tag = _get(f, "tag", "feeder_id", "part_number", default=f"-Q{i + 2}")
    desc = _get(f, "description", "desc", default=tag)

    return {
        "tag": tag,
        "in_a": _get(f, "rated_current_a", "in_a", "breaker_current_a", "design_current_a", default=0),
        "kw": _get(f, "power_kw", "kw", "motor_kw", default=0),
        "cable": _get(f, "cable_cross_section_mm2", "cable", "recommended_cable", default=""),
        "len_m": _get(f, "cable_length_m", "len_m", default=0),
        "du": _get(f, "voltage_drop_percent", "du", default=0),
        "desc": desc,
        "ref": _get(f, "func_tag", "ref", "function", default=f"=FEEDER{i + 1}"),
        "load": kind,
        "dev": dev,
        "ct": _get(f, "ct_tag", default=f"-TA{i + 1}"),
    }


def build_plc_io_rows(feeders=None, instruments=None, plc_summary=None):
    rows = []
    di = do = ai = ao = 0

    for i, f in enumerate(feeders or []):
        load = _str(_get(f, "load_type", "load", "device_type", default="")).upper()
        tag = _get(f, "tag", "feeder_id", "part_number", default=f"-Q{i + 2}")
        desc = _get(f, "description", "desc", default=tag)

        is_motor = any(x in load for x in ("MOTOR", "DOL", "STAR", "SOFT", "VFD", "PUMP", "FAN", "COMPRESSOR"))
        if not is_motor:
            continue

        for suffix, d in (
            ("RUN", "Contactor run feedback"),
            ("TRIP", "Overload trip feedback"),
            ("REM", "Hand/off/auto remote status"),
        ):
            rows.append((_addr_di(di), "DI", f"{tag} {suffix}", d, "-A1.1 DI16", ""))
            di += 1

        rows.append((_addr_do(do), "DO", f"{tag} START", "Contactor start command", "-A1.1 DQ16", ""))
        do += 1

        if "VFD" in load:
            rows.append((_addr_ai(ai), "AI", f"{tag} SPEED FB", "Drive speed feedback", "-A1.1 AI8", ""))
            ai += 1
            rows.append((_addr_ao(ao), "AO", f"{tag} SPEED SP", "Drive speed setpoint", "-A1.1 AQ4", ""))
            ao += 1

    for inst in instruments or []:
        sig = _get(inst, "signal_type", "type", default="")
        kind = _signal_kind(sig)
        tag = _get(inst, "tag_id", "tag", default="")
        desc = _get(inst, "description", "desc", default=tag)
        addr = _get(inst, "plc_channel_address", "address", default="")

        if not addr:
            if kind == "DI":
                addr = _addr_di(di)
                di += 1
            elif kind == "DO":
                addr = _addr_do(do)
                do += 1
            elif kind == "AI":
                addr = _addr_ai(ai)
                ai += 1
            else:
                addr = _addr_ao(ao)
                ao += 1

        term = _get(inst, "iec81346_terminal_dt", "terminal", default="")
        card = f"-A1.1 {kind}" + ("16" if kind in ("DI", "DO") else "8" if kind == "AI" else "4")
        rows.append((str(addr), kind, f"{tag} {_clip(desc, 18)}", desc, card, _str(term)))

    return rows


def build_terminal_rows(project=None, feeders=None, instruments=None, plc_summary=None):
    rows = []
    panel = _get(project, "panel_tag", "ref", default="+MCC1")
    vk = _num(_get(project, "nominal_voltage_v", "vk_v", default=400), 0)

    rows.extend(
        [
            ("X1:1", f"{panel}-L1", f"L1 ({vk} V)", "BUSBAR", "-Q1 /1", "feeders /1", "Phase bar"),
            ("X1:2", f"{panel}-L2", f"L2 ({vk} V)", "BUSBAR", "-Q1 /3", "feeders /3", ""),
            ("X1:3", f"{panel}-L3", f"L3 ({vk} V)", "BUSBAR", "-Q1 /5", "feeders /5", ""),
            ("X1:4", f"{panel}-N", "N", "BUSBAR", "-Q1 /N", "feeders /N", "Neutral bar"),
            ("X1:5", f"{panel}-PE", "PE", "6 mm2 Cu", "Main PE", "doors/frames", "Bonding"),
            ("X2:1", f"{panel}-L+CTRL", "+24 V DC", "0.75 mm2", "-G1 L+", "control devices", "PELV"),
            ("X2:2", f"{panel}-MCTRL", "0 V DC (M)", "0.75 mm2", "-G1 M", "control devices", ""),
        ]
    )

    for i, f in enumerate(feeders or [], start=1):
        v = _feeder_view(f, i - 1)
        cable = _str(v["cable"])
        wire = f"{cable} mm2 L={_num(v['len_m'], 0)} m" if cable else f"L={_num(v['len_m'], 0)} m"
        rows.append(
            (
                f"X1:{20 + i}",
                f"{panel}{v['tag']}-OUT",
                "Feeder load side",
                wire,
                f"{v['tag']} load",
                "Field device",
                f"dU={_num(v['du'], 1)}%",
            )
        )

    for inst in instruments or []:
        term_dt = _str(_get(inst, "iec81346_terminal_dt", "terminal", default=""))
        term = term_dt.rsplit("-", 1)[-1] if "-" in term_dt else ""
        kind = _signal_kind(_get(inst, "signal_type", "type", default=""))
        wire = _str(_get(inst, "recommended_cable", default=""))
        frm = _str(_get(inst, "tag_id", "tag", default=""))
        to = _str(_get(inst, "plc_channel_address", "address", default=""))
        note = _str(_get(inst, "interface_device_part", default=""))
        rows.append((term, term_dt, kind, wire, frm, to, note))

    return rows


def _to_tuple(row, keys):
    if isinstance(row, dict):
        out = []
        for k in keys:
            if k in row:
                out.append(_str(row[k]))
            elif k == "no" and "term" in row:
                out.append(_str(row["term"]))
            elif k == "addr" and "address" in row:
                out.append(_str(row["address"]))
            elif k == "tag" and "tag_id" in row:
                out.append(_str(row["tag_id"]))
            elif k == "desc" and "description" in row:
                out.append(_str(row["description"]))
            else:
                out.append("")
        return tuple(out)

    if isinstance(row, (list, tuple)):
        vals = [_str(x) for x in row]
        if len(vals) < len(keys):
            vals += [""] * (len(keys) - len(vals))
        return tuple(vals[: len(keys)])

    return tuple(_str(_attr(row, k, "")) for k in keys)


def _svg_table(x, y, widths, headers, rows, title, keys):
    rows = [_to_tuple(r, keys) for r in (rows or [])]
    tw = sum(widths)

    p = [_txt(x, y - 6, title, 9.5, bold=True)]
    p.append(_rect(x, y, tw, HEAD_H, fill="#eef3f8", sw=1.0))

    cx = x
    for i, h in enumerate(headers):
        p.append(_txt(cx + 4, y + 15, _clip(h, widths[i] // 5), 8, bold=True))
        cx += widths[i]

    cx = x
    for w in widths[:-1]:
        cx += w
        p.append(_wv(cx, y, y + HEAD_H, 0.8))

    yy = y + HEAD_H
    for r in rows:
        p.append(_rect(x, yy, tw, ROW_H, fill="#fff", sw=0.6))
        cx = x
        for i, cell in enumerate(r):
            p.append(_txt(cx + 4, yy + 14, _clip(cell, widths[i] // 5), 8))
            cx += widths[i]

        cx = x
        for w in widths[:-1]:
            cx += w
            p.append(_wv(cx, yy, yy + ROW_H, 0.6))

        yy += ROW_H

    p.append(_rect(x, y, tw, yy - y, fill="none", sw=1.0))
    return "".join(p), yy


def render_single_line_diagram(
    project,
    feeders,
    plc=None,
    terminals=None,
    instruments=None,
    plc_rows=None,
    terminal_rows=None,
):
    feeders = feeders or []
    n = len(feeders)

    fixed = MARGIN_L + BUS_LEFT_EXTRA + BUS_RIGHT_EXTRA + MARGIN_R + 40
    if n > 0:
        slot = int((MIN_PAGE_W - fixed) / n) if MIN_PAGE_W > fixed else MIN_SLOT_W
        slot = max(MIN_SLOT_W, min(MAX_SLOT_W, slot))
    else:
        slot = MIN_SLOT_W

    x_in = MARGIN_L + 60
    bus_l = x_in
    feed_l = bus_l + BUS_LEFT_EXTRA
    bus_r = feed_l + n * slot + BUS_RIGHT_EXTRA
    page_w = max(MIN_PAGE_W, bus_r + MARGIN_R + 40)

    p = []

    name = _get(project, "project_name", "name", default="LV Panel")
    ref = _get(project, "iec81346_ref", "ref", "panel_tag", default="")
    p.append(_txt(MARGIN_L, TITLE_Y, f"{name} - Single-Line Diagram / Einpoliger Schaltplan (IEC 60617)", 12, bold=True))
    p.append(_txt(page_w - MARGIN_R, TITLE_Y, f"Ref: {ref} | LV-PanelAssist", 8.5, anchor="end", color="#555"))
    p.append(_wh(MARGIN_L, page_w - MARGIN_R, RULE_Y, 0.8))

    vk = _num(_get(project, "nominal_voltage_v", "vk_v", default=400), 0)
    ik = _num(_get(project, "prospective_ik_ka", "ik_ka", default=25), 1)
    bus_in = _num(_get(project, "busbar_current_a", "bus_in", "design_main_current_a", default=630), 0)
    bus_ic = _num(_get(project, "busbar_ic_ka", "bus_ic", default=50), 0)

    p.append(
        _txt(
            MARGIN_L,
            SUPPLY_Y,
            f"Supply: 3~ {vk} V 50 Hz | Ik'' = {ik} kA | Bus: {bus_in} A / {bus_ic} kA",
            9,
        )
    )

    main_tag = _get(project, "main_breaker_tag", "main_tag", default="-Q1")
    main_in = _num(_get(project, "main_breaker_current_a", "main_in", default=bus_in), 0)

    p.append(_txt(x_in, INC_LABEL_Y, f"3~ {vk} V", 9, anchor="middle", bold=True))
    p.append(_wv(x_in, INC_LABEL_Y + 4, INC_BRK_Y - 12))
    p.append(_breaker(x_in, INC_BRK_Y, main_tag, main_in, "MAIN"))
    p.append(_wv(x_in, INC_BRK_Y + 12, BUS_Y))
    p.append(_dot(x_in, BUS_Y))

    p.append(_wh(bus_l, bus_r, BUS_Y, 3.0))
    p.append(_txt(bus_r, BUS_Y - 6, f"~BU {bus_in} A", 8.5, anchor="end", color="#1F4E78"))

    spd_cls = _get(project, "spd_class", "spd_cls", default="T2")
    spd_up = _get(project, "spd_up_kv", "spd_up", default="1.5 kV")
    xs = bus_r - 36
    p.append(_wv(xs, BUS_Y, SPD_Y - 9))
    p.append(_dot(xs, BUS_Y))
    p.append(_spd(xs, SPD_Y, spd_cls, spd_up))
    p.append(_wv(xs, SPD_Y + 9, SPD_EARTH_Y))
    p.append(_earth(xs, SPD_EARTH_Y))

    p.append(_wv(x_in, BUS_Y, PE_Y))
    p.append(_earth(x_in, PE_Y))
    p.append(_txt(x_in + 14, PE_Y + 12, "PE", 8, color="#333"))

    for i, f in enumerate(feeders):
        v = _feeder_view(f, i)
        x = int(feed_l + slot * (i + 0.5))

        p.append(_wv(x, BUS_Y, BRK_Y - 12))
        p.append(_dot(x, BUS_Y))

        if v["dev"] == "FUSE":
            p.append(_fuse(x, BRK_Y, v["tag"], v["in_a"]))
        else:
            p.append(_breaker(x, BRK_Y, v["tag"], v["in_a"]))

        p.append(_wv(x, BRK_Y + 12, CT_Y - 9))
        p.append(_ct(x, CT_Y, v["ct"]))
        p.append(_wv(x, CT_Y + 9, CABLE_TOP))

        cw = max(90, slot - 28)
        p.append(_rect(x - cw // 2, CABLE_TOP, cw, CABLE_H, fill="#fbfbfb", sw=0.9))

        cable_txt = f"{v['cable']} mm2  L={_num(v['len_m'], 0)} m" if v["cable"] else f"L={_num(v['len_m'], 0)} m"
        p.append(_txt(x, CABLE_TOP + 12, _clip(cable_txt, cw // 6), 7.5, anchor="middle"))
        p.append(_txt(x, CABLE_TOP + 24, f"dU = {_num(v['du'], 1)} %", 7.5, anchor="middle", color="#333"))

        p.append(_wv(x, CABLE_TOP + CABLE_H, LOAD_Y - 14))
        p.append(_load(x, LOAD_Y, v["load"], v["kw"], v["tag"], v["desc"]))
        p.append(_txt(x, LOAD_Y + 52, _clip(v["ref"], 24), 7.5, anchor="middle", color="#1F4E78"))

    diag = "".join(p)

    if terminal_rows is None:
        if terminals is not None:
            terminal_rows = terminals
        else:
            terminal_rows = build_terminal_rows(project, feeders, instruments, plc)

    if plc_rows is None:
        plc_rows = build_plc_io_rows(feeders, instruments, plc)

    tp = []
    cur_y = TABLE_START_Y

    if terminal_rows:
        th = ["Term", "IEC 81346 Designation (DT)", "Potential / Function", "Cable / Size", "From", "To", "Note"]
        tw = [46, 220, 110, 96, 76, 96, 92]
        keys = ["no", "dt", "pot", "wire", "frm", "to", "note"]
        s, cur_y = _svg_table(
            MARGIN_L,
            cur_y,
            tw,
            th,
            terminal_rows,
            "TABLE 1 - Terminal Schedule (Klemmenplan) per IEC 81346",
            keys,
        )
        tp.append(s)
        cur_y += TABLE_GAP

    if plc_rows or plc:
        ph = ["Address", "Type", "Tag (IEC 81346)", "Description", "Card / Module", "Terminal"]
        pw = [76, 58, 154, 220, 126, 90]
        keys = ["addr", "type", "tag", "desc", "card", "term"]

        cpu = _get(plc, "selected_cpu_part", "cpu", default="")
        di = _get(plc, "required_di_with_spare", "di", default=None)
        do = _get(plc, "required_do_with_spare", "do", default=None)
        ai = _get(plc, "required_ai_with_spare", "ai", default=None)
        ao = _get(plc, "required_ao_with_spare", "ao", default=None)
        relays = _get(plc, "total_interposing_relays_qty", "relays", default=0)
        isolators = _get(plc, "total_signal_isolators_qty", "isolators", default=0)
        pwr = _get(plc, "total_instrumentation_24v_w", "pwr_w", default=0)

        if di is None:
            di = sum(1 for r in plc_rows if _to_tuple(r, keys)[1] == "DI")
        if do is None:
            do = sum(1 for r in plc_rows if _to_tuple(r, keys)[1] == "DO")
        if ai is None:
            ai = sum(1 for r in plc_rows if _to_tuple(r, keys)[1] == "AI")
        if ao is None:
            ao = sum(1 for r in plc_rows if _to_tuple(r, keys)[1] == "AO")

        title = (
            f"TABLE 2 - PLC I/O Allocation | {cpu} | "
            f"DI={_num(di, 0)} DO={_num(do, 0)} AI={_num(ai, 0)} AO={_num(ao, 0)} | "
            f"Relays={_num(relays, 0)} Isolators={_num(isolators, 0)} 24V={_num(pwr, 1)} W"
        )

        s, cur_y = _svg_table(MARGIN_L, cur_y, pw, ph, plc_rows, title, keys)
        tp.append(s)
        cur_y += 18

    notes = _txt(
        MARGIN_L,
        cur_y,
        "Wire types: power = LiYY / control = LiY 0.75 mm2 / AI-AO = LiYCY 2x2x0.75 shielded (one-side PE). "
        "Coil side to M rail per IEC 60204-1 9.4.2.1.",
        7.5,
        color="#555",
    )

    page_h = cur_y + 34
    body = diag + "".join(tp) + notes

    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {page_w} {page_h}' "
        f"width='{page_w}' height='{page_h}'>"
        f"<rect x='0' y='0' width='{page_w}' height='{page_h}' fill='#ffffff'/>"
        f"{body}</svg>"
    )


def build_demo_inputs():
    project = {
        "name": "Demo Pump Skid - MCC",
        "vk_v": 400,
        "ik_ka": 25,
        "bus_in": 630,
        "bus_ic": 50,
        "main_tag": "-Q1",
        "main_in": 800,
        "ref": "==PROCESS =PUMP1 ++EL_ROOM +MCC1",
        "spd_cls": "T2",
        "spd_up": "1.5 kV",
    }

    feeders = [
        {
            "ref": "=FEEDER1",
            "tag": "-Q2",
            "desc": "Feed pump P-101",
            "load": "MOTOR_DOL",
            "in_a": 32,
            "kw": 11,
            "cable": "4x10",
            "len_m": 45,
            "du": 1.7,
            "dev": "BREAKER",
        },
        {
            "ref": "=FEEDER2",
            "tag": "-Q3",
            "desc": "ID fan F-201",
            "load": "MOTOR_VFD",
            "in_a": 16,
            "kw": 4,
            "cable": "4x4",
            "len_m": 30,
            "du": 1.2,
            "dev": "BREAKER",
        },
        {
            "ref": "=FEEDER3",
            "tag": "-Q4",
            "desc": "Workshop lighting",
            "load": "LIGHTING",
            "in_a": 10,
            "kw": 2,
            "cable": "5x2.5",
            "len_m": 60,
            "du": 2.4,
            "dev": "FUSE",
        },
        {
            "ref": "=FEEDER4",
            "tag": "-Q5",
            "desc": "PF capacitor bank",
            "load": "CAP_BANK",
            "in_a": 63,
            "kw": 50,
            "cable": "4x25",
            "len_m": 8,
            "du": 0.6,
            "dev": "BREAKER",
        },
        {
            "ref": "=FEEDER5",
            "tag": "-Q6",
            "desc": "Compressor C-301",
            "load": "MOTOR_DOL",
            "in_a": 80,
            "kw": 30,
            "cable": "4x35",
            "len_m": 70,
            "du": 2.1,
            "dev": "BREAKER",
        },
    ]

    plc = {
        "cpu": "Siemens CPU 1510SP-1 PN",
        "di": 18,
        "do": 12,
        "ai": 4,
        "ao": 2,
        "relays": 12,
        "isolators": 4,
        "pwr_w": 128.5,
    }

    terminals = [
        {"no": "X1:1", "dt": "=INCOMING+MCC1-L1", "pot": "L1 (400 V)", "wire": "BUSBAR 63x10", "frm": "-Q1 /1", "to": "-Q2..-Q6 /1", "note": "Phase bar"},
        {"no": "X1:2", "dt": "=INCOMING+MCC1-L2", "pot": "L2", "wire": "BUSBAR 63x10", "frm": "-Q1 /3", "to": "feeders /3", "note": ""},
        {"no": "X1:3", "dt": "=INCOMING+MCC1-L3", "pot": "L3", "wire": "BUSBAR 63x10", "frm": "-Q1 /5", "to": "feeders /5", "note": ""},
        {"no": "X1:4", "dt": "=INCOMING+MCC1-N", "pot": "N", "wire": "BUSBAR 63x5", "frm": "-Q1 /N", "to": "-Q2.. /N", "note": "Neutral bar"},
        {"no": "X1:5", "dt": "=INCOMING+MCC1-PE", "pot": "PE", "wire": "6 mm2 Cu", "frm": "Main PE", "to": "doors/frames", "note": "Bonding"},
        {"no": "X2:1", "dt": "=PUMP1+MCC1-X1:1", "pot": "+24 V DC", "wire": "0.75 mm2", "frm": "-G1 L+", "to": "-K1M A1", "note": "Control"},
        {"no": "X2:2", "dt": "=PUMP1+MCC1-X1:2", "pot": "0 V DC (M)", "wire": "0.75 mm2", "frm": "-G1 M", "to": "-K1M A2", "note": ""},
        {"no": "X3:1", "dt": "=PUMP1+FIELD-B1", "pot": "AI 4-20 mA", "wire": "2x2x0.75 SH", "frm": "PT-101", "to": "-A1.1 X_AI:1", "note": "Shield->PE 1 side"},
    ]

    return project, feeders, plc, terminals