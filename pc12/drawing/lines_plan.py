"""
Sheet L1 -- fuselage LINES PLAN, drawn from the loft parameters of model/fuselage.py (control-line knot
tables + section law), never from the mesh.

    python3 -m drawing.master L1          (or: python3 -m drawing.lines_plan)

Views (first-angle arrangement): profile seen from port (1:20) with the station grid at the frames,
crown / keel / max-breadth WL and buttock lines; half-breadth plan below it (1:20) with waterlines; body
plan (1:10) with the forward sections seen from ahead on the left and the aft sections seen from aft on
the right, at the frames.  Tables: control-line knots, deviations of the loft from the registered
Pilatus drawing (our numbers, from drawing/lines_fit.py), cabin numbers for Stage 3.  The overlay variant
adds the Pilatus drawing in red (refs/cache/overlays/L1_overlay.*).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, GRID, MUTED, W_OBJ, W_FINE, W_GRID, CHAIN, callout, grid_lines,  # noqa: E402
                            station_grid, table, notes, scale_bar, view_title, side_view, plan_view,
                            front_view, aft_view)
from model import fuselage as F  # noqa: E402

SHEET = dict(id="L1", title="LINES PLAN", subtitle="FUSELAGE LINES PLAN", size="A1", scale="AS SHOWN",
             rev="A", order=10)

LINE_INK = "#34434B"                        # buttocks / waterlines
FWD_FRAMES = ("EF1", "EF2", "FR10", "FR12", "FR14", "FR16")
AFT_FRAMES = ("FR30", "FR33", "FR36", "FR38", "FR40")
GRID_FRAMES = ("EF1", "EF2", "FR10", "FR12", "FR14", "FR16", "FR19", "FR21", "FR23", "FR25", "FR27", "FR29",
               "FR30", "FR31", "FR33", "FR36", "FR38", "FR40")
BUTTOCKS = (0.2, 0.4, 0.6, 0.8)
WATERLINES = (1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6)
# previous model (rev A, before the Stage-2 refit) for the change call-outs
REV_A = dict(crown=2.630, keel=0.800, hw11=0.740, tail_end=14.36, spinner_r=0.29, cowl_front=0.95)
# cabin (Stage 3): published 5.16 x 1.52 x 1.47 m, floor 1.30 m; lining allowances as in model/interior.py
CABIN_X = 6.0
CROWN_ALLOW, SIDE_ALLOW = 0.040, 0.085


def spinner_profile(n=60):
    """Spinner meridian (powerplant part, shown for reference): tip STA 390, base radius SPINNER_R at the cowl
    front, profile law F.SPINNER_SHAPE (the views draw it about the tilted / yawed thrust line,
    powerplant.spinner_silhouette)."""
    x0, x1, R = F.STA["spinner_tip"], F.STA["cowl_front"], F.SPINNER_R
    a, b = F.SPINNER_SHAPE
    t = np.linspace(0, 1, n)
    r = R * (1 - (1 - t) ** a) ** b
    return x0 + (x1 - x0) * t, r


def cabin_numbers():
    c = F.cabin_numbers(CABIN_X, 1.30, SIDE_ALLOW)
    floor = c["crown"] - CROWN_ALLOW - 1.47
    c["floor"] = floor
    c["ceiling"] = c["crown"] - CROWN_ALLOW
    c["oml_width_at_floor"] = 2 * float(F.side_y(CABIN_X, floor))
    c["floor_width_avail"] = c["oml_width_at_floor"] - 2 * SIDE_ALLOW
    c["inner_max_width"] = 2 * float(F.half_w(CABIN_X)) - 2 * SIDE_ALLOW
    return c


# ============================================================================================ views
def draw_profile(ds, v, xs):
    cv = ds.cv
    x0, x1 = F.STA["cowl_front"], F.STA["tail_end"]
    # grids
    grid_lines(ds, v, "b", (1.0, 1.5, 2.0, 2.5, 3.0), 0.30, 13.80,
               labels=[f"WL {z * 1000:.0f}" for z in (1.0, 1.5, 2.0, 2.5, 3.0)], where=("start", "end"))
    # buttock lines (upper and lower halves)
    for yb in BUTTOCKS:
        ok = F.half_w(xs) > yb + 1e-4
        for up in (True, False):
            z = F.z_at(xs, np.full_like(xs, yb), up)
            for seg in _runs(ok):
                cv.path(v.pts(np.c_[xs[seg], z[seg]]), W_FINE, color=LINE_INK)
        # label at the upper buttock's aft end
        k = np.where(ok)[0][-1]
        X, Y = v.pt(xs[k], float(F.z_at(xs[k], yb, True)))
        ds.text(X + 1.0, Y - 1.0, f"BL {yb * 1000:.0f}", 2.1, "mono", "start", fill=LINE_INK, tag="bl")
    # max-breadth water line
    cv.path(v.pts(np.c_[xs, F.z_mw(xs)]), W_FINE, CHAIN, color=LINE_INK)
    X, Y = v.pt(7.6, float(F.z_mw(7.6)))
    ds.text(X, Y - 1.2, "MAX-BREADTH WL", 2.1, "label", "middle", fill=LINE_INK, tag="lbl")
    # crown and keel, ends
    cv.path(v.pts(np.c_[xs, F.z_top(xs)]), W_OBJ)
    cv.path(v.pts(np.c_[xs, F.z_bot(xs)]), W_OBJ)
    for x in (x0, x1):
        cv.line(v.pt(x, float(F.z_bot(x))), v.pt(x, float(F.z_top(x))), W_OBJ)
    # spinner (reference) on the thrust line: 2 deg nose-down, WL 1655 at the disc (model/powerplant.py THRUST_*)
    from model import powerplant as PP
    cv.path(v.pts(PP.spinner_silhouette("side")), W_FINE, (2.0, 0.8), color=MUTED)
    ax_ = PP.axis_point(np.array([0.25, 1.5]))
    cv.line(v.pt(ax_[0, 0], ax_[0, 2]), v.pt(ax_[1, 0], ax_[1, 2]), W_GRID, CHAIN, color=MUTED)
    X, Y = v.pt(0.36, float(ax_[0, 2]))                   # ahead of the spinner tip, clear of its outline
    ds.text(X - 0.5, Y - 1.2, f"THRUST LINE {PP.THRUST_TILT_DEG:.0f}° DN", 2.0, "label", "end", fill=MUTED, tag="lbl")
    # cabin floor (Stage 3 proposal)
    c = cabin_numbers()
    cv.line(v.pt(4.40, c["floor"]), v.pt(9.85, c["floor"]), W_FINE, (3.0, 1.2), color=MUTED)
    X, Y = v.pt(8.3, c["floor"])
    ds.text(X, Y - 1.0, f"CABIN FLOOR WL {c['floor'] * 1000:.0f} (STAGE 3)", 2.1, "label", "middle", fill=MUTED,
            tag="lbl")


def draw_key_stations(ds, v, zlo, zhi):
    keys = [("COWL FRONT", F.STA["cowl_front"]), ("FIREWALL", F.STA["firewall"]),
            ("CABIN CROWN FLAT", 4.40), ("APB", F.STA["aft_pressure_bulkhead"]), ("TAIL END", F.STA["tail_end"])]
    for i, (name, x) in enumerate(keys):
        p, q = v.pt(x, zlo), v.pt(x, zhi)
        ds.cv.line(p, q, W_GRID, (5.0, 1.0, 0.8, 1.0), color=MUTED)
        dy = 3.2 if i % 2 == 0 else 7.4
        ds.text(p[0], p[1] + dy, f"{name} {x * 1000:.0f}", 2.1, "label", "middle", fill=MUTED, tag="key")


def draw_halfbreadth(ds, v, xs):
    cv = ds.cv
    grid_lines(ds, v, "b", BUTTOCKS, 0.30, 13.80, labels=[f"BL {y * 1000:.0f}" for y in BUTTOCKS],
               where=("start", "end"))
    cv.line(v.pt(0.25, 0.0), v.pt(13.9, 0.0), W_FINE, CHAIN)
    X, Y = v.pt(0.25, 0.0)
    ds.text(X - 1.5, Y, "CL", 2.4, "label", "end", vcenter=True, weight=600, tag="cl")
    # waterlines
    placed, anchors = [], []
    for z in WATERLINES:
        inside = (F.z_top(xs) > z) & (F.z_bot(xs) < z)
        y = F.side_y(xs, np.full_like(xs, z))
        for seg in _runs(inside):
            P = np.c_[xs[seg], y[seg]]
            # close the waterline onto the centre line where it enters / leaves the body
            cv.path(v.pts(P), W_FINE, color=LINE_INK)
        segs = _runs(inside)
        if segs:
            k = segs[-1][-1]
            anchors.append((*v.pt(xs[k], y[k]), f"WL {z * 1000:.0f}"))
    cv.path(v.pts(np.c_[xs, F.half_w(xs)]), W_OBJ)
    x0, x1 = F.STA["cowl_front"], F.STA["tail_end"]
    for x in (x0, x1):
        cv.line(v.pt(x, 0.0), v.pt(x, float(F.half_w(x))), W_OBJ)
    _, Ycl = v.pt(0.0, 0.0)
    for X, Y, s_ in anchors:                            # after the lines: labels go on clear paper
        _place_label(ds, X + 0.8, Y - 0.8, s_, 1.9, placed, below=Ycl + 2.8)
    from model import powerplant as PP                  # spinner (reference) on the yawed thrust line
    S_ = PP.spinner_silhouette("plan")
    cv.path(v.pts(S_[: len(S_) // 2]), W_FINE, (2.0, 0.8), color=MUTED)
    X, Y = v.pt(12.2, 0.62)
    ds.text(X, Y, "WATERLINES WL 1000 - 2600 (LABELLED AT THEIR AFT ENDS)", 2.1, "label", "middle",
            fill=LINE_INK, tag="lbl")


def _place_label(ds, x, y, s, size, placed, step=2.4, below=None):
    """Small mono label; moved up in steps while it overlaps one placed before or a drawn line crosses it; if no
    clear spot is found above (and `below` is given), stacked downward from sheet y `below` instead."""
    from drawing.canvas import text_width
    w, h = text_width(s, size, "mono"), 0.8 * size

    def free(yy, lines=True):
        box = (x, yy - h, x + w, yy + 0.2 * size)
        if any(b[0] < box[2] and box[0] < b[2] and b[1] < box[3] and box[1] < b[3] for b in placed):
            return False
        return not lines or ds.line_length_in_box((x + 0.1 * size, yy - 0.62 * size, x + w - 0.1 * size,
                                                    yy - 0.1 * size)) < 0.3
    cands = [y - k * step for k in range(4)] + ([below + k * step for k in range(8)] if below is not None else [])
    y_ = next((c for c in cands if free(c)), None)
    if y_ is None:                                      # fall back to the old rule (label overlaps only)
        y_ = next((y - k * step for k in range(12) if free(y - k * step, lines=False)), y)
    placed.append((x, y_ - h, x + w, y_ + 0.2 * size))
    ds.text(x, y_, s, size, "mono", "start", fill=LINE_INK, tag="wl")


def half_section(x, n=721):
    t = np.linspace(0, 0.5, n)
    P = F.section(np.full_like(t, x), t)
    return P[:, 1:]                             # (y >= 0, z) crown -> keel


def draw_body_plan(ds, vf, va, zlo=0.80, zhi=2.90, ymax=0.95):
    cv = ds.cv
    wls = np.round(np.arange(1.0, 2.81, 0.2), 3)
    for v, side in ((vf, "start"), (va, "end")):
        grid_lines(ds, v, "b", wls, 0.0, ymax, labels=[f"{z * 1000:.0f}" for z in wls],
                   where=("end",))
        grid_lines(ds, v, "a", (0.2, 0.4, 0.6, 0.8), zlo, zhi,
                   labels=[f"{y * 1000:.0f}" for y in (0.2, 0.4, 0.6, 0.8)], where=("start",))
    cv.line(vf.pt(0.0, zlo - 0.03), vf.pt(0.0, zhi + 0.03), W_FINE, CHAIN)
    X, Y = vf.pt(0.0, zlo - 0.03)
    ds.text(X, Y + 3.2, "CL", 2.4, "label", "middle", weight=600, tag="cl")
    X, Y = vf.pt(ymax, zlo)
    ds.text(X, Y + 7.4, "BL", 2.1, "label", "middle", fill=GRID, tag="grid")
    X, Y = va.pt(ymax, zlo)
    ds.text(X, Y + 7.4, "BL", 2.1, "label", "middle", fill=GRID, tag="grid")
    X, Y = vf.pt(ymax, zhi)
    ds.text(X - 2.0, Y - 2.2, "WL", 2.1, "label", "end", fill=GRID, tag="grid")
    X, Y = va.pt(ymax, zhi)
    ds.text(X + 2.0, Y - 2.2, "WL", 2.1, "label", "start", fill=GRID, tag="grid")
    # spinner base circle (cowl front) on the forward side
    P = half_section(F.STA["cowl_front"])
    cv.path(vf.pts(P), W_FINE, (2.0, 0.8), color=MUTED)
    # forward sections (labels just above the crown, left of the CL)
    for name in FWD_FRAMES:
        x = F.FRAMES[name]
        P = half_section(x)
        cv.path(vf.pts(P), W_OBJ)
        X, Y = vf.pt(0.0, P[0, 1])
        lab = name if name != "FR16" else "FR16-FR30"
        ds.text(X - 1.2, Y - 0.9, lab, 2.3, "label", "end", weight=600, tag="sec")
    # aft sections (labels just below the keel, right of the CL)
    aft = [(n, F.FRAMES[n]) for n in AFT_FRAMES] + [("STA 12650", 12.65)]
    for name, x in aft:
        P = half_section(x)
        cv.path(va.pts(P), W_OBJ if name.startswith("FR") else W_FINE,
                None if name.startswith("FR") else (2.5, 1.0))
        X, Y = va.pt(0.0, P[-1, 1])
        if name == "FR30":
            continue                           # same section as FR16 (labelled on the forward side)
        ds.text(X + 1.2, Y + 3.0, name, 2.3, "label", "start", weight=600, tag="sec")
    # cabin envelope (Stage 3 check): floor 1.30 wide, headroom 1.47, max inner width 1.52
    c = cabin_numbers()
    cv.line(va.pt(0.0, c["ceiling"]), va.pt(0.30, c["ceiling"]), W_FINE, (3.0, 1.0), color=MUTED)
    for v in (vf, va):
        cv.line(v.pt(0.0, c["floor"]), v.pt(0.65, c["floor"]), W_FINE, (3.0, 1.0), color=MUTED)
        cv.line(v.pt(0.76, c["zmw"] - 0.12), v.pt(0.76, c["zmw"] + 0.12), W_FINE, (3.0, 1.0), color=MUTED)
        cv.line(v.pt(0.65, c["floor"] - 0.03), v.pt(0.65, c["floor"] + 0.03), W_FINE, color=MUTED)
    X, Y = va.pt(0.02, c["floor"])
    ds.text(X, Y - 1.2, f"FLOOR WL {c['floor'] * 1000:.0f} · 1300 WIDE", 2.0, "label", "start", fill=MUTED,
            tag="cab")
    X, Y = va.pt(0.02, c["ceiling"])
    ds.text(X, Y + 3.0, f"CEILING WL {c['ceiling'] * 1000:.0f} (1470)", 2.0, "label", "start", fill=MUTED,
            tag="cab")


def _runs(mask):
    """Index arrays of the consecutive True runs of a boolean mask."""
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    br = np.where(np.diff(idx) > 1)[0]
    return [r for r in np.split(idx, br + 1) if len(r) >= 2]


# ============================================================================================ tables
def knot_rows():
    T = F.CONTROL_LINES
    cols = ("crown", "keel", "half_breadth", "max_breadth_wl", "n_top", "m_top", "n_bot", "m_bot")
    from drawing.lines_fit import FIXED, TIES
    xs = sorted({round(x, 3) for k in cols for x, _ in T[k]})
    rows = []
    for x in xs:
        r = [f"{x * 1000:.0f}"]
        for k in cols:
            v = [val for xx, val in T[k] if abs(xx - x) < 1e-6]
            if not v:
                r.append("")
                continue
            s = f"{v[0] * 1000:.0f}" if k in ("crown", "keel", "half_breadth", "max_breadth_wl") else f"{v[0]:.2f}"
            if any(abs(x - f) < 1e-6 for f in FIXED.get(k, ())):
                s += "*"
            elif any(abs(x - t) < 1e-6 for t in TIES.get(k, ())):
                s += "="
            else:
                s += " "
            r.append(s)
        rows.append(tuple(r))
    return rows


def deviation_rows():
    """Rows: dataset, n, rms, max, rev-A rms, rev-A max, worst at, remark (mm).  Also returns the raw
    deviations of the current loft and of rev A."""
    from drawing import lines_fit as LF
    D = LF.deviations()
    D0 = LF.deviations(LF.rev_a_oml())
    rows = []
    rem = {
        "crown": "max at the cowl front: drawn nose 18 high (drawn prop axis WL 1673; WL 1655 kept)",
        "keel": "visible keel only (not behind wing fairing 5300-7470, strake 10720-11960); max as crown",
        "half_breadth": "plan view; strake tips STA 11650-11950 ignored",
        "fin_root": "dorsal-fin root line (side view) at the plan fillet half-breadth, STA 9250-12450",
    }
    names = {"crown": "PROFILE CROWN", "keel": "PROFILE KEEL", "half_breadth": "HALF-BREADTH",
             "fin_root": "FIN-ROOT LINE"}

    def f(v):
        return f"{v * 1000:.1f}"

    for key in ("crown", "keel", "half_breadth", "fin_root"):
        rms, mx, k = LF.stats(D[key]["dev"])
        r0, m0, _ = LF.stats(D0[key]["dev"])
        rows.append((names[key], str(len(D[key]["dev"])), f(rms), f(mx), f(r0), f(m0),
                     f"STA {D[key]['x'][k] * 1000:.0f}", rem[key]))
    ls, ls0 = D["lower_sil"], D0["lower_sil"]
    rows.append(("LOWER SILHOUETTE", str(len(ls["dev"])), "-", f(max(ls["dev"].max(), 0)), "-",
                 f(max(ls0["dev"].max(), 0)), "", "fuselage never below the strake / ventral-fairing silhouette "
                 "(STA 10700-13560); MAX = protrusion"))
    srem = {"EF1": "cowling ring only; the chin-inlet crescent is not OML (Stage 3 inlet)",
            "FR16-30": "constant cabin section, checked at 5 stations 4590-8230",
            "FR33": "keel knee region (flat bottom to tail-cone transition)",
            "FR36": "dorsal fin excluded", "FR38": "dorsal fin, ventral strakes excluded",
            "FR40": "dorsal fin, strakes, ventral fairing (BL 121, WL 1606) excluded"}
    s2 = []
    for name, S in D["sections"].items():
        rms, mx, k = LF.stats(S["dev"])
        r0, m0, _ = LF.stats(D0["sections"][name]["dev"])
        y, z = S["pts"][k]
        if S["sheet"] == 2:
            s2.append((name, rms, mx, y, z, len(S["dev"]), r0, m0))
            continue
        xs = S["xs"]
        lab = f"{name} {xs[0] * 1000:.0f}" + (f"-{xs[-1] * 1000:.0f}" if len(xs) > 1 else "")
        rows.append((lab, str(len(S["dev"])), f(rms), f(mx), f(r0), f(m0),
                     f"BL {abs(y) * 1000:.0f} WL {z * 1000:.0f}", srem.get(name, "")))
    rms = np.sqrt(np.mean([r[1] ** 2 for r in s2]))
    w = max(s2, key=lambda r: r[2])
    rows.append(("FR19-FR31 (SHEET 2)", str(sum(r[5] for r in s2)), f(rms), f(w[2]),
                 f(np.sqrt(np.mean([r[6] ** 2 for r in s2]))), f(max(r[7] for r in s2)),
                 f"{w[0]} BL {abs(w[3]) * 1000:.0f} WL {w[4] * 1000:.0f}",
                 "phantom cabin section, weight 0.25 (sheet 2: x +/-15, z +/-45); FR31 lies on the keel knee"))
    return rows, D


# ============================================================================================ sheet
def draw(ds):
    """Sheet entry point for drawing.master: the clean content, then the overlay-only layer."""
    draw_clean(ds)
    try:
        draw_overlay(ds)
    except Exception as e:                      # noqa: BLE001 -- the clean sheet must not depend on refs/cache
        ds.log.append(f"overlay skipped: {e}")


def draw_clean(ds):
    ds.frame_and_title(tb_width=250.0)
    xs = np.linspace(F.STA["cowl_front"], F.STA["tail_end"], 2600)
    frames = {n: F.FRAMES[n] for n in GRID_FRAMES}

    # ---------------- profile (1:20) and half-breadth plan (1:20), aligned in x
    vp = ds.add_view(side_view("profile", origin=(38.0, 186.0), scale=20, box=(0.30, 0.80, 13.80, 3.00)))
    vh = ds.add_view(plan_view("halfbreadth", origin=(38.0, 224.0), scale=20, box=(0.30, -0.02, 13.80, 0.95)))
    station_grid(ds, [vp, vh], frames, [(0.80, 3.00), (0.0, 0.95)], label_view=vp, label_at="hi")
    draw_key_stations(ds, vp, 0.80, 3.00)
    draw_profile(ds, vp, xs)
    draw_halfbreadth(ds, vh, xs)

    # ---------------- body plan (1:10)
    vf = ds.add_view(front_view("body_fwd", origin=(140.0, 559.0), scale=10, box=(0.0, 0.80, 0.95, 2.90)))
    va = ds.add_view(aft_view("body_aft", origin=(140.0, 559.0), scale=10, box=(0.0, 0.80, 0.95, 2.90)))
    draw_body_plan(ds, vf, va)

    # ---------------- view titles, scale bars
    view_title(ds, 783.0, 70.0, "PROFILE", "SEEN FROM PORT · SCALE 1:20")
    view_title(ds, 783.0, 196.0, "HALF-BREADTH PLAN", "SEEN FROM ABOVE · STARBOARD HALF · 1:20")
    view_title(ds, 140.0, 506.0, "BODY PLAN", "SCALE 1:10")
    ds.text(95.0, 515.5, "FORWARD SECTIONS SEEN FROM AHEAD", 2.4, "label", "middle", fill=MUTED, tag="title")
    ds.text(185.0, 515.5, "AFT SECTIONS SEEN FROM AFT", 2.4, "label", "middle", fill=MUTED, tag="title")
    scale_bar(ds, 745.0, 236.0, 20, length_m=1.5, step_m=0.25)
    scale_bar(ds, 60.0, 535.0, 10, length_m=1.0, step_m=0.1)
    legend(ds, 752.0, 84.0)

    # ---------------- change / deviation call-outs (our numbers)
    c = cabin_numbers()
    callout(ds, vp, (6.9, float(F.z_top(6.9))), f"CABIN CROWN WL {F.z_top(6.9) * 1000:.0f}",
            offset=(8.0, -6.5), lines=[f"REV A {REV_A['crown'] * 1000:.0f}: +{(F.z_top(6.9) - REV_A['crown']) * 1000:.0f}"])
    callout(ds, vp, (6.2, float(F.z_bot(6.2))), f"CABIN KEEL WL {F.z_bot(6.2) * 1000:.0f}",
            offset=(8.0, 9.0), lines=[f"REV A {REV_A['keel'] * 1000:.0f}: +{(F.z_bot(6.2) - REV_A['keel']) * 1000:.0f}"])
    callout(ds, vh, (11.0, float(F.half_w(11.0))), f"HALF-BREADTH STA 11000: {F.half_w(11.0) * 1000:.0f}",
            offset=(-2.0, -13.0), lines=[f"REV A {REV_A['hw11'] * 1000:.0f}: {(F.half_w(11.0) - REV_A['hw11']) * 1000:+.0f}"])

    # ---------------- tables
    krows = knot_rows()
    kcols = [("STA", 15.0, "r"), ("CROWN", 15.0, "r"), ("KEEL", 15.0, "r"), ("HALF-BR", 15.0, "r"),
             ("MAX-BR WL", 17.0, "r"), ("n TOP", 13.0, "r"), ("m TOP", 13.0, "r"), ("n BOT", 13.0, "r"),
             ("m BOT", 13.0, "r")]
    yk = table(ds, 262.0, 250.0, kcols, krows, title="CONTROL-LINE KNOTS (model/fuselage.py)", size=2.2,
               row_h=3.35, zebra=lambda i: i % 2 == 1)
    ds.text(262.0, yk + 3.6, "mm (exponents dimensionless) · * fixed · = tied (constant cabin section)",
            2.1, "label", "start", fill=MUTED, tag="tnote")
    ds.text(262.0, yk + 7.0, "pchip (monotone cubic) through the knots of each line", 2.1, "label", "start",
            fill=MUTED, tag="tnote")
    section_law_box(ds, 262.0, yk + 12.0, 262.0 + sum(c_[1] for c_ in kcols))

    try:
        drows, D = deviation_rows()
    except Exception as e:                      # noqa: BLE001 -- reference cache missing
        drows = [("(reference not available)", "", "", "-", "", "", "", str(e)[:80])]
        ds.log.append(f"deviation table: reference not available ({e})")
    dcols = [("DATASET", 41.0, "l"), ("N", 11.0, "r"), ("RMS", 12.0, "r"), ("MAX", 12.0, "r"),
             ("REV A RMS", 17.0, "r"), ("REV A MAX", 17.0, "r"), ("WORST AT", 40.0, "l"), ("REMARK", 263.0, "l")]
    yd = table(ds, 412.0, 250.0, dcols, drows,
               title="DEVIATIONS OF THE LOFT FROM THE PILATUS DRAWING (NORMAL DISTANCE, mm)", size=2.2,
               row_h=3.55, zebra=lambda i: i % 2 == 1, font="label")
    def _num(v):                                # table cells are strings; '' / '-' = not evaluated
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    maxes = [_num(r[3]) for r in drows]
    rmses = [_num(r[2]) for r in drows[:3]]
    evaluated = [v for v in maxes if v is not None] and [v for v in rmses if v is not None]
    if not evaluated:
        verdict, ok = "- targets not evaluated (reference not available).", True
    else:
        ok = all(v <= 20.0 for v in maxes if v is not None) and all(v <= 8.0 for v in rmses if v is not None)
        verdict = "- ALL MET." if ok else "- NOT MET (see remarks)."
    ds.text(412.0, yd + 3.8, "Targets: profile / half-breadth RMS <= 8, max <= 20; every frame section max <= 20 "
            + verdict + "  REV A = the model before this refit.",
            2.3, "label", "start", weight=600,
            fill=M.ACCENT if not ok else INK, tag="tnote")

    cabin_table(ds, 412.0, yd + 10.0, c)
    notes_block(ds, 580.0, yd + 8.0, 825.0, c)
    ds.log.append("deviations: " + "; ".join(f"{r[0]} {r[3]}" for r in drows))


def legend(ds, x0, y0):
    items = [("OML (crown, keel, max half-breadth, sections)", dict(w=W_OBJ)),
             ("buttock / water lines", dict(w=W_FINE, color=LINE_INK)),
             ("max-breadth WL", dict(w=W_FINE, dash=CHAIN, color=LINE_INK)),
             ("spinner / cabin (reference)", dict(w=W_FINE, dash=(2.0, 0.8), color=MUTED)),
             ("frame station grid", dict(w=W_GRID, color=GRID))]
    M.legend_rows(ds, x0, y0, items, dy=4.6, size=2.3)


def section_law_box(ds, x0, y0, x1):
    cv = ds.cv
    h = 36.0
    cv.rect(x0, y0, x1 - x0, h, lw=M.W_TABLE)
    ds.text(x0 + 2.0, y0 + 4.6, "SECTION LAW (each half)", 2.8, "label", "start", weight=600, tag="law")
    ds.text(x0 + 2.0, y0 + 11.0, "|y / hw|^n + |(z - zmw) / hz|^m = 1", 2.8, "mono", "start", tag="law")
    lines = ["hw = half-breadth, zmw = max-breadth WL,",
             "hz = crown - zmw (upper) or zmw - keel (lower);",
             "n: crown / keel flatness, m: side flatness;",
             "n = m = 2: ellipse. Section parameter t = polar",
             "angle about (0, zmw) in normalised coordinates."]
    for i, s in enumerate(lines):
        ds.text(x0 + 2.0, y0 + 17.0 + 3.6 * i, s, 2.3, "label", "start", tag="law")


def cabin_table(ds, x0, y0, c):
    rows = [("crown / keel WL (STA 4600-8200)", f"{c['crown'] * 1000:.0f} / {c['keel'] * 1000:.0f}"),
            ("OML depth / max breadth", f"{c['depth'] * 1000:.0f} / {c['max_breadth'] * 1000:.0f}"),
            ("max-breadth WL", f"{c['zmw'] * 1000:.0f}"),
            (f"ceiling WL (crown - {CROWN_ALLOW * 1000:.0f})", f"{c['ceiling'] * 1000:.0f}"),
            ("floor WL (ceiling - 1470)", f"{c['floor'] * 1000:.0f}"),
            ("floor WL change vs rev A (1120)", f"{(c['floor'] - 1.12) * 1000:+.0f}"),
            ("OML width at the floor", f"{c['oml_width_at_floor'] * 1000:.0f}"),
            (f"floor width avail. (- 2 x {SIDE_ALLOW * 1000:.0f})", f"{c['floor_width_avail'] * 1000:.0f} >= 1300"),
            (f"max inner width (- 2 x {SIDE_ALLOW * 1000:.0f})", f"{c['inner_max_width'] * 1000:.0f} ~ 1520")]
    return table(ds, x0, y0, [("CABIN (STAGE 3)", 110.0, "l"), ("mm", 44.0, "r")], rows,
                 title="CABIN SECTION NUMBERS", size=2.2, row_h=3.5, font="label")


def notes_block(ds, x0, y0, x1, c):
    items = [
        "Drawn from the loft parameters of model/fuselage.py (knot tables + section law), not from the mesh. "
        "Stations = STA mm aft of the datum (3000 ahead of the firewall); WL above the static ground line; "
        "BL from the centre line, + starboard.",
        "Knot values fitted by least squares (drawing/lines_fit.py) to the registered Pilatus NGX model drawing "
        "190.10.40.432: side crown / visible keel, plan half-breadth, frame sections EF1-FR40 (sheet 1) and the "
        "sheet-2 phantom cabin section, with smoothness regularisation. Deviation = normal distance, + = ours outside.",
        "Fixed: spinner tip STA 390, prop axis WL 1655 at the disc (prop clearance 320 kept, the drawing shows 336); "
        "thrust line 2 deg nose-down / 2 deg right (drawn), so the spinner tip is at WL 1636 and the spinner base "
        "centre 4 mm above the cowl-front ring (R 250 at STA 1044; Stage 3); firewall STA 3000, tail-cone closure "
        "STA 13570 at the lower end of the rudder trailing edge; 14,400 overall length is set by the tail bullet.",
        "Not part of this OML (Stage 3 parts): chin-inlet crescent, dorsal fin, ventral strakes, ventral fairing "
        "under the tail cone (FR40, lower silhouette aft of STA 11900), wing-root fairing. Aft of the rudder "
        "leading edge (STA 12650 at the keel) the tail cone lies inside the rudder / fin and is trimmed there.",
        f"Changes vs rev A: cabin crown {REV_A['crown'] * 1000:.0f} -> {c['crown'] * 1000:.0f}, keel "
        f"{REV_A['keel'] * 1000:.0f} -> {c['keel'] * 1000:.0f} (flat from STA 2850), aft body slimmer "
        f"(half-breadth STA 11000 {REV_A['hw11'] * 1000:.0f} -> {F.half_w(11.0) * 1000:.0f}), tail end "
        f"{REV_A['tail_end'] * 1000:.0f} -> {F.STA['tail_end'] * 1000:.0f}, spinner R 290 -> 250, cowl front "
        f"950 -> 1044.",
    ]
    return notes(ds, x0, y0, x1, items, size=2.3, line_h=3.3)


# ============================================================================================ overlay
def draw_overlay(ds):
    """Pilatus drawing in red on the overlay variant."""
    vp, vh, vf, va = (ds.views[k] for k in ("profile", "halfbreadth", "body_fwd", "body_aft"))
    n = ds.ov_mbp(vp, "side")
    n += ds.ov_mbp(vh, "plan")
    d = M.mbp_data()
    for name in ("EF1", "EF2", "FR10", "FR12", "FR14", "FR16-30"):
        for ln in d["sections"][name]["lines"]:
            if ln["kind"] in ("outline", "hidden") and len(ln["pts"]) >= 5:
                ds.ov_polylines(vf, [ln["pts"]], dash=(1.6, 0.9) if ln["kind"] == "hidden" else None,
                                clip=(-0.005, 0.80, 0.95, 2.90))
    for name in ("FR16-30", "FR33", "FR36", "FR38", "FR40"):
        for ln in d["sections"][name]["lines"]:
            if ln["kind"] in ("outline", "hidden") and len(ln["pts"]) >= 5:
                ds.ov_polylines(va, [ln["pts"]], dash=(1.6, 0.9) if ln["kind"] == "hidden" else None,
                                clip=(-0.005, 0.80, 0.95, 2.90))
    # sheet-2 phantom cabin section (identical on FR19..FR31): one copy, dashed
    for ln in d["sections"]["FR19"]["lines"]:
        if ln.get("tag") == "phantom":
            ds.ov_polylines(va, [ln["pts"]], dash=(0.8, 0.8), clip=(-0.005, 0.80, 0.95, 2.90))
    ds.ov_text(752.0, 116.0, "RED: PILATUS 190.10.40.432 (REGISTERED, SHEET 1;", 2.4)
    ds.ov_text(752.0, 119.6, "SHEET-2 PHANTOM CABIN SECTION DOTTED)", 2.4)
    ds.log.append(f"overlay: {n} Pilatus side/plan polylines + sections")


if __name__ == "__main__":
    M.main(["L1"] + sys.argv[1:])
