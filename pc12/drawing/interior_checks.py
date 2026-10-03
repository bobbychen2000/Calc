"""
Sheet L6B -- INTERIOR ARRANGEMENT, sheet 2 of 2: the checks behind sheet L6, computed from the parameter tables of
model/interior.py (crew_checks / cabin_checks): the crew station per occupant (95th / 50th / 5th male, 5th female)
and in general, full rudder, reach (grasp / touch), the knee / yoke sensitivity to the estimated inputs, the cabin and
the club table, deviations and decisions, key parameters with their source notes, other POH layouts, the POH-arm CG
cross-check, the sheet notes, the open points for the owner and the revisions.  Table text 3.4 mm (the sensitivity
table and revisions 3.0; review r2: L6 kept its drawings, the long text moved here); long cells wrap.

    python3 -m drawing.master L6 L6B
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing import sheet as S  # noqa: E402
from drawing.master import INK, PAPER, MUTED, W_TABLE, W_TABLE_IN  # noqa: E402
from model import interior as I  # noqa: E402
from model import cockpit_glazing as CG  # noqa: E402
from drawing.interior_sheet import context, mm, revisions_block  # noqa: E402

TXT = 3.4                              # table text on this sheet (mm)
HEAD = 3.0                             # table header text
TITLE = 3.8                            # table title bar text

SHEET = dict(id="L6B", title="INTERIOR ARRANGEMENT - CHECKS", subtitle="INTERIOR ARRANGEMENT - CHECKS & PARAMETERS",
             size="A1", scale="-", rev="F", order=61, sheet_no="2 OF 2", dwg="PC12-L6", date="2026-10-03")

COLS = ((28.0, 286.0), (296.0, 556.0), (566.0, 826.0))
Y_TOP = 16.0
Y_MAX = 578.0                          # frame bottom; column 3 stops above the title block (Y_TB)
Y_TB = 500.0
LH = 4.5                               # wrapped line pitch at TXT
ROW_PAD = 1.3


def wtable(ds, x0, y0, cols, rows, title=None, size=TXT, font="label", zebra=True):
    """Ruled table whose cells wrap to the column width.  cols: [(header, width_mm, align)]; returns the bottom y."""
    cv = ds.cv
    xs = [x0]
    for c in cols:
        xs.append(xs[-1] + c[1])
    x1 = xs[-1]
    y = y0
    if title:
        cv.rect(x0, y, x1 - x0, 7.0, lw=W_TABLE, fill=INK)
        ds.text(x0 + 2.0, y + 3.5, title, TITLE, "label", "start", weight=600, fill=PAPER, vcenter=True, spacing=0.2,
                tag="table")
        y += 7.0
    hl = [S.wrap(h, c[1] - 1.6, HEAD, "label") for h, c in zip([c[0] for c in cols], cols)]
    hh = max(len(h) for h in hl) * (HEAD + 1.0) + 2.0
    for i, lines in enumerate(hl):
        for k, t in enumerate(lines):
            ds.text(0.5 * (xs[i] + xs[i + 1]), y + 1.0 + 0.5 * (HEAD + 1.0) + (HEAD + 1.0) * k, t, HEAD, "label",
                    "middle", weight=600, vcenter=True, tag="table")
    cv.line((x0, y + hh), (x1, y + hh), W_TABLE)
    y += hh
    top = y
    for r_i, r in enumerate(rows):
        cells = [S.wrap(str(s), c[1] - 2.4, size, font if c[2] == "l" else "mono") for s, c in zip(r, cols)]
        n = max(len(cl) for cl in cells)
        h = n * LH + ROW_PAD
        if zebra and r_i % 2 == 1:
            cv.rect(x0, y, x1 - x0, h, lw=0, fill="#EEF1F2", stroke=False)
        for i, cl in enumerate(cells):
            al = cols[i][2]
            for k, t in enumerate(cl):
                ty = y + 0.5 * ROW_PAD + LH * (k + 0.5)
                if al == "r":
                    ds.text(xs[i + 1] - 1.2, ty, t, size, "mono", "end", vcenter=True, tag="table")
                elif al == "c":
                    ds.text(0.5 * (xs[i] + xs[i + 1]), ty, t, size, "mono", "middle", vcenter=True, tag="table")
                else:
                    ds.text(xs[i] + 1.2, ty, t, size, font if al != "m" else "mono", "start", vcenter=True,
                            tag="table")
        y += h
    for xx in xs[1:-1]:
        cv.line((xx, top - hh), (xx, y), W_TABLE_IN)
    cv.rect(x0, y0, x1 - x0, y - y0, lw=W_TABLE)
    return y


def sgn(v):
    r = int(round(float(v) * 1000))
    return f"{r:+d}" if r else "0"


def text_block(ds, x0, y0, x1, lines, size=TXT, color=MUTED):
    """Wrapped plain paragraph; returns the bottom y."""
    y = y0
    for t in S.wrap(" ".join(lines), x1 - x0, size):
        ds.text(x0, y + 0.7 * size, t, size, "label", "start", fill=color, tag="tnote")
        y += LH
    return y


# ---------------------------------------------------------------------------------------------------- blocks
def crew_occupants(ds, x0, y0, x1, ctx):
    kc = ctx["crew"]
    c = I.CREW_SEAT
    occ = kc["occ"]
    keys = ("p95m", "p50m", "p5m", "p5f")

    def row(label, fn, note=""):
        return (label,) + tuple(fn(occ[k]) for k in keys) + (note,)
    kr = I.CRITERIA["knee_clear"]
    R = I.YOKE["roll"]
    T = I.PEDALS["travel"]
    rows = [
        row("scale of the 95th-pct links", lambda o: f"{o['scale']:.2f}", "uniform scaling [E]"),
        row("seat notch / pedal crank", lambda o: f"{sgn(o['dx'])} / {sgn(o['crank'])}",
            f"each picks the knee angle ~{I.CRITERIA['knee_angle']:.0f}°; crank - = fwd"),
        row("seat height (vertical travel)", lambda o: sgn(o["dz"]), f"toward the design eye, ±{mm(c['travel_z'])}"),
        row("eye vs design eye, fwd / up", lambda o: f"{sgn(-o['eye_dx'])} / {sgn(o['eye_dz'])}", "0 up = on it"),
        row("over the nose (deg)", lambda o: f"{o['over_nose']:.1f}", "to the windshield lower edge"),
        row("knee angle (deg)", lambda o: f"{o['knee_angle']:.0f}", "neutral pedals"),
        row("knee top WL", lambda o: mm(o["knee_top"]), f"lower panel edge {mm(I.PANEL['mfd_z'] + I.PANEL['lower_dz'])}; "
            f"grip bottoms {mm(I.PANEL['mfd_z'] + I.YOKE['hub_dz'] + I.YOKE['grip_dz'])}"),
        row("knee to the lower panel", lambda o: mm(o["clear_panel"]), "side view"),
        row(f"legs to the yoke, pitch ±{mm(I.YOKE['travel'][1])}, wings level", lambda o: sgn(o["yoke_pitch"]),
            f"criterion >= {mm(kr)}; 3-D, knees on the hip-to-pedal line (pedals ±{mm(I.PEDALS['dy'])} [M]), 95th "
            f"±{mm(occ['p95m']['pose']['leg_y'][1])}"),
        row(f"... with roll ±{R:.0f}° [E]", lambda o: sgn(o["yoke_sweep"]), "pitch x roll sweep; - = contact"),
        row(f"roll keeping {mm(kr)} / to contact (deg)",
            lambda o: f"{max(o['roll_clear'], 0):.0f} / {max(o['roll_contact'], 0):.0f}",
            "full pitch travel; 90 = no contact"),
        row(f"FULL RUDDER ±{mm(T)}: up-knee top WL", lambda o: mm(o["rud_knee_top"]),
            "the pedal that comes aft lifts that knee [E travel]"),
        row("... legs to the yoke, wings level", lambda o: sgn(o["rud_pitch"]),
            "up-knee on the worse leg, other leg extended; full pitch sweep"),
        row(f"... with roll ±{R:.0f}°", lambda o: sgn(o["rud_sweep"]), "crosswind flare: full aft, roll, opposite rudder"),
        row("... roll to contact (deg)", lambda o: f"{max(o['rud_roll_contact'], 0):.0f}", "0 = already wings level"),
        row("extended knee, pedal full fwd (deg)",
            lambda o: f"{o['ext_knee']:.0f}{'' if o['ext_ok'] else ' !'}",
            f"reach limit <= {I.CRITERIA['knee_ext']:.0f}° [E]; ! = beyond it"),
        row("H-point to the pedal ball", lambda o: mm(o["hip_to_ball"]), "neutral pedals"),
        row("headroom (head top to lining)", lambda o: mm(o["headroom"]), "at the seat BL"),
        row("shoulder room", lambda o: mm(o["shoulder_room"]), "deltoid to the sidewall lining"),
        row("headrest lock (along the back)", lambda o: mm(o["head_c"]),
            f"six positions {mm(c['head_lock'][0])}-{mm(c['head_lock'][1])}"),
        row("headrest rear to the divider", lambda o: mm(o["head_div"]), "at the occupant's notch"),
    ]
    w = x1 - x0
    return wtable(ds, x0, y0, [("LEFT SEAT", 64.0, "l"), ("95TH M", 25.0, "r"), ("50TH M", 25.0, "r"),
                               ("5TH M", 25.0, "r"), ("5TH F", 25.0, "r"), ("NOTE", w - 164.0, "l")], rows,
                  title="CREW STATION - OCCUPANTS AT THEIR SETTINGS (mm)")


def crew_general(ds, x0, y0, x1, ctx):
    kc = ctx["crew"]
    c = I.CREW_SEAT
    occ = kc["occ"]
    e, f_u = kc["eye"], kc["eye_off"]
    v = kc["vision"]
    da, rc, ig = kc["div_aft"], kc["recline"], kc["ingress"]
    lo, hi = c["head_lock"]
    tx = c["travel_x"]
    rows = [
        ("design eye STA / BL / WL", f"{mm(e[0])} / {mm(abs(e[1]))} / {mm(e[2])}",
         f"the 50th-pct eye on the neutral seat: SRP + {mm(f_u[0])} fwd / {mm(f_u[1])} up; L2 used "
         f"{mm(CG.EYE[0])}/{mm(abs(CG.EYE[1]))}/{mm(CG.EYE[2])}"),
        ("neutral SRP STA / WL", f"{mm(kc['srp'][0])} / {mm(kc['srp'][2])}",
         f"{mm(c['srp_h'])} above the floor; travel ±{mm(tx)} / ±{mm(c['travel_z'])}"),
        ("occupants at the design eye", "5TH M - 95TH M",
         f"5th female {sgn(occ['p5f']['eye_dz'])} below it at full up (over-nose {occ['p5f']['over_nose']:.1f}°): "
         "cushion"),
        ("eye to own PFD / to MFD", f"{mm(kc['eye_to_pfd'])} / {mm(kc['eye_to_mfd'])}",
         f"PFD centre {kc['pfd_down_deg']:.0f}° below horizontal"),
        ("over the nose / abeam down / up", f"{v['over_nose_down']:.1f}° / {v['abeam_down_over_sill']:.0f}° / "
         f"{v['abeam_up_to_top']:.0f}°", f"glareshield lip {kc['lip_down_deg']:.0f}° down: clear of the view"),
        ("aft notch: headrest to divider", f"{sgn(da[lo])} / {sgn(da[c['head_c']])} / {sgn(da[hi])}",
         f"lowest / 50th / top lock; divider fwd face {mm(I.DIVIDER['x_aft'] - I.DIVIDER['t'])}"),
        ("recline room to the divider", f"{rc[-tx]:.1f}° / {rc[0.0]:.1f}° / {rc[tx]:.1f}°",
         "fwd / centre / aft notch, 50th headrest ('reclining' [S])"),
        ("seat vs the tunnel plinth", f"{mm(kc['plinth_lat'])}",
         f"trimmed inboard cushion (symmetric: {sgn(kc['plinth_lat_sym'])}; its top only "
         f"{mm(kc['plinth_cushion_top'])} above the plinth at the lowest fwd seat); plates {mm(kc['plate_lat'])}"),
        ("armrests vs the pedestal", f"{mm(kc['arm_pedestal'])}",
         f"inboard arm face to the PCL grip over the seat travel (lowest seat), >= "
         f"{mm(I.CRITERIA['arm_pedestal'])} [E]; the arm's bottom clears the quadrant top"),
        ("ingress: headrests / backs / cushions", f"{mm(ig['head_gap'])} / {mm(ig['back_gap'])} / "
         f"{mm(ig['cushion_gap'])}",
         f"95th hip {mm(ig['hip'])}: hips pass between the headrests, legs between the backs, then over the inboard "
         f"cushion with the armrest up (stowed along the back, top {mm(ig['arm_up_top'])} above the floor); divider "
         f"opening {mm(ig['opening'])}"),
        ("room behind the seat back", f"{mm(ig['behind_neutral'])} / {mm(ig['behind_fwd'])}", "neutral / fwd notch"),
        ("curtain to seat / track; extinguisher", f"{sgn(kc['curtain_clear'])} / {sgn(kc['curtain_track'])} / "
         f"{sgn(kc['ext_clear'])}",
         f"aft notch: the stowed curtain ({'LH' if I.DIVIDER['curtain'][0] < 0 else 'RH'}, "
         f"{mm(I.DIVIDER['curtain'][2])} deep [E]) to the seat back below its flare top and to the crew track's aft "
         "end; the bottle to the co-pilot seat's back / plate"),
    ]
    return wtable(ds, x0, y0, [("CREW STATION", 52.0, "l"), ("VALUE", 46.0, "r"), ("NOTE", x1 - x0 - 98.0, "l")],
                  rows, title="CREW STATION - GENERAL (mm)")


def reach_block(ds, x0, y0, x1, ctx):
    kc = ctx["crew"]
    s5 = kc["occ"]["p5f"]["scale"]
    rows = []
    for lab, kind, d in kc["reach"]:
        rows.append((lab, kind.upper(), f"{mm(d['p5f'][0])} {d['p5f'][1]}", f"{mm(d['p95m'][0])} {d['p95m'][1]}"))
    y = wtable(ds, x0, y0, [("TARGET", 72.0, "l"), ("KIND", 24.0, "c"), ("5TH F: DIST / CLASS", 60.0, "r"),
                            ("95TH M: DIST / CLASS", x1 - x0 - 156.0, "r")], rows,
               title="REACH FROM THE NEARER SHOULDER JOINT (mm)")
    rs, ft = I.MANIKIN["reach_sh"], I.MANIKIN["fingertip"]
    return text_block(ds, x0, y + 1.5, x1, [
        f"GRASP (levers, CCD palm grip): straight arm, shoulder joint to thumbtip {mm(rs)} (95th; 5th F "
        f"{mm(s5 * rs)}), from the thumbtip reach {mm(I.MANIKIN['reach'])} less the back-wall offset. TOUCH (touch "
        f"screens, push-buttons, switches, breakers): + {mm(ft)} to the index fingertip [E] ({mm(rs + ft)} / "
        f"{mm(s5 * (rs + ft))}). LOCKED: within it, harness locked; LEAN: within +{mm(I.MANIKIN['lean'])} with the "
        "inertia reel unlocked (normal in flight); NO: beyond."])


def _deg(a):
    return "none" if a >= 89.9 else f"{max(a, 0):.0f}°"


def sensitivity_block(ds, x0, y0, x1, ctx):
    """Open point 1: the knee / yoke result against each estimated input (interior.crew_sensitivity)."""
    lim = I.CRITERIA["knee_ext"]

    def ext(a):
        return f"{a:.0f}°{'!' if a > lim else ''}"
    rows = []
    for lab, d in ctx["sens"]:
        a, b, f = d["p95m"], d["p50m"], d["p5f"]
        rows.append((lab, f"{sgn(a['dx'])} / {sgn(a['crank'])}", _deg(a["contact"]),
                     f"{sgn(a['rud'])} / {_deg(a['rud_contact'])}", f"{sgn(b['dx'])} / {sgn(b['crank'])}",
                     _deg(b["contact"]), f"{sgn(b['rud'])} / {_deg(b['rud_contact'])}",
                     f"{ext(a['ext'])} / {ext(b['ext'])} / {ext(f['ext'])}", sgn(d["div"])))
    w = x1 - x0
    y = wtable(ds, x0, y0, [("INPUT (vs as set)", 46.0, "l"), ("95TH NOTCH / CRANK", 25.0, "r"),
                            ("95 CONTACT", 18.0, "r"), ("95 RUDDER mm / CONTACT", 27.0, "r"),
                            ("50TH NOTCH / CRANK", 25.0, "r"), ("50 CONTACT", 18.0, "r"),
                            ("50 RUDDER mm / CONTACT", 27.0, "r"), ("EXT. KNEE 95 / 50 / 5F", w - 208.0, "r"),
                            ("HEAD TO DIVIDER", 22.0, "r")], rows,
               title="KNEE vs YOKE - SENSITIVITY TO THE ESTIMATED INPUTS (OPEN POINT 1)", size=3.0)
    return text_block(ds, x0, y + 1.5, x1, [
        "Left seat. Each row changes one input from the as-set state; every occupant then re-picks notch and crank "
        f"(knee ~{I.CRITERIA['knee_angle']:.0f}° rule, least travel). CONTACT: yoke roll (full pitch travel) at which a "
        "knee first touches a grip, neutral pedals. RUDDER: the up-knee on the pedal that came aft, other leg extended: "
        f"wings-level clearance / roll to contact; none = no contact to 90°. EXT. KNEE: at full forward rudder, ! = "
        f"beyond {lim:.0f}° [E]. HEAD TO DIVIDER: aft notch, top headrest lock."])


def cg_block(ds, x0, y0, x1, ctx):
    """POH occupant arms vs the 50th's CG on the drawn poses (interior.cg_crosscheck)."""
    rows = [(lab, mm(poh), mm(srp), mm(cg), sgn(d)) for lab, poh, srp, cg, d in ctx["cg"]]
    w = x1 - x0
    y = wtable(ds, x0, y0, [("SEAT (50TH-PCT MALE)", w - 116.0, "l"), ("POH ARM", 29.0, "r"), ("SRP STA", 29.0, "r"),
                            ("CG STA", 29.0, "r"), ("CG - POH", 29.0, "r")], rows,
               title="POH OCCUPANT ARMS vs THE OCCUPANT CG (mm)")
    cg = {r[0]: r[4] for r in ctx["cg"]}
    fwd = [r[4] for r in ctx["cg"] if "fwd-facing" in r[0]]
    return text_block(ds, x0, y + 1.5, x1, [
        "Method: Dempster (1955) segment-mass fractions and segment CG locations (Winter's table) on the sheet's "
        "50th-pct poses, both limbs alike. Forward-facing cabin seats "
        f"{sgn(min(fwd))}..{sgn(max(fwd))}: the method agrees with the POH to ~2 cm. Pilot: "
        f"{sgn(cg['PILOT, centre notch'])} at the centre notch but {sgn(cg['PILOT, full aft'])} with the seat full aft, "
        "so the POH crew arm reads as a full-aft value (conservative for the aft CG); the SRP stays at "
        f"{mm(I.CREW_SEAT['srp_x'])} (the divider bounds it: open point 9). Aft-facing PAX 1/2: the plan-render "
        "footprint (open point 4)."])


def cabin_block(ds, x0, y0, x1, ctx):
    k = ctx["cabin"]
    rec = k["recline"]
    hr = k["head_rest"]
    tb = k["table"]
    tt = I.TABLES["club_p"]
    po50, po95 = tb["p50m"]["posture"], tb["p95m"]["posture"]
    rows = [
        ("cabin length (divider -> aft wall)", mm(k["length"]), f"{mm(I.CABIN['length'])} published"),
        ("cabin width (lining, max breadth)", mm(k["width"]), f"{mm(I.CABIN['width'])} published"),
        ("cabin height (floor -> headliner, CL)", mm(k["height"]), f"{mm(I.CABIN['height'])} published (POH 1450)"),
        ("floor width (carpet) / between linings", f"{mm(k['floor_width'])} / {mm(k['floor_width_avail'])}",
         f"{mm(I.CABIN['floor_width'])} published"),
        ("floor length (divider -> FR34)", mm(k["floor_length"]), f"{mm(I.CABIN['floor_length'])} POH"),
        ("aisle between armrests / cushions", f"{mm(k['aisle_arm'])} / {mm(k['aisle_cushion'])}",
         f"seats fully outboard (TTL); one arm per seat, inboard; cushion to the ledge {mm(k['cushion_to_ledge'])}"),
        ("club: cushion fronts / 95th knees", f"{mm(k['club_gap'])} / {mm(k['club_knee_gap'])}",
         f"PAX 1 -> PAX 3; POH-mirror PAX 1: {mm(k['club_gap_mirror'])}"),
        ("club: 95th toes pass each other", mm(k["club_toes_pass"]),
         f"feet interleave: PAX 3 at CL ±{mm(k['club_feet_y'][0])}, PAX 1 ±{mm(k['club_feet_y'][1])}; outer foot "
         f"{sgn(k['club_feet_kick'])} to the kick panel"),
        ("pitch PAX 3 -> 5, stagger 5 -> 6", f"{mm(k['pitch_fwd'])} / {mm(k['stagger'])}", "POH"),
        ("headroom 95th: outboard / inboard", f"{mm(k['headroom'])} / {mm(k['headroom_in'])}",
         f"seat slid inboard {mm(I.EXEC_SEAT['travel'][2])} [S]"),
        ("shoulder room 95th: out / in", f"{sgn(k['shoulder_room'])} / {sgn(k['shoulder_room_in'])}",
         "deltoid to the sidewall lining"),
        ("headrest (raised) top over head centre", f"{sgn(hr['p95m'][0])} / {sgn(hr['p50m'][0])}",
         "95th / 50th: the 95th's head centre is above the headrest; it supports the 50th"),
        ("seated eye WL 95th / 50th", f"{mm(k['eye_wl'])} / {mm(k['eye_wl_p50'])}",
         f"window {mm(k['win'][0])}-{mm(k['win'][1])}: eyes above the window top (no seated photo to test)"),
        ("club table underside vs the legs, 95 / 50 / 5M / 5F",
         " / ".join(sgn(tb[q]["full"][0]) for q in ("p95m", "p50m", "p5m", "p5f")),
         f"top {mm(tt['top_h'])} ({mm(k['table_ledge'])} under the ledge cap [M]), feet under the knees: the legs "
         f"(CL ±{mm(I.MANIKIN['knee_y'])}) are under the top; outboard leaf alone: "
         + " / ".join(sgn(tb[q]["leaf"][0]) for q in ("p95m", "p50m", "p5m", "p5f"))),
        ("table: shank angle for 25 / toes to the facing base",
         f"{po50['shank']:.0f}° / {sgn(po50['toe_gap'])}",
         f"50th with the feet forward: fits; 95th needs {po95['shank']:.0f}° and his feet {mm(-po95['toe_gap'])} under "
         "the facing seat's base: does not fit (decision + open point)"
         if po95["shank"] is not None else "95th: no posture fits"),
        ("recline reached PAX 1 / 2 / 3 / 4 / 5 / 6",
         " / ".join(f"{rec[f'PAX {i}'][0]:.0f}" for i in range(1, 7)),
         f"deg from vertical, of {I.EXEC_SEAT['recline_deg']:.0f} [E]; limits: " +
         ", ".join(f"{i}: {rec[f'PAX {i}'][1].replace(' occupant', '')}" for i in range(1, 7) if rec[f"PAX {i}"][1])),
        ("PAX 6 back to FR34 / PAX 1 to cabinet", f"{mm(k['back_to_partition'])} / {mm(k['pax1_back_to_cabinet'])}",
         "upright, at the floor"),
        ("exit hatch clear of the PAX 2 cushion", mm(k["exit_clear"]),
         f"of {mm(k['exit_x'][1] - k['exit_x'][0])}; sill {mm(k['exit_sill_h'])} above the floor"),
        ("lavatory: 95th knees past the door line", mm(k["lav_knee_past_door"]),
         f"facing inboard on the toilet (back at the lid hinge); lav {mm(k['lav_len'])} x {mm(k['lav_depth'])}: "
         "doors cannot close"),
        ("lav: floor in front of the cabinet", mm(k["lav_floor"]),
         f"cabinet {mm(I.LAVATORY['cabinet'][2])} deep [E] to the bi-fold line (P1046411 shows carpet there)"),
        ("lav bi-folds to the entry zone", mm(k["lav_swing_clear"]),
         f"fold out <= {mm(I.LAVATORY['leaf'])}; entry zone |BL| > {mm(I.CLEAR_ZONES['entry_bl'])}"),
    ]
    return wtable(ds, x0, y0, [("CABIN (EX-6S-2)", 64.0, "l"), ("VALUE", 54.0, "r"), ("NOTE", x1 - x0 - 118.0, "l")],
                  rows, title="CABIN CHECKS (mm), 95TH-PCT MALE UNLESS NOTED")


def deviations_block(ds, x0, y0, x1, ctx):
    kc, cc = ctx["crew"], ctx["cabin"]
    c = I.CREW_SEAT
    e = kc["eye"]
    v = kc["vision"]
    o95 = kc["occ"]["p95m"]
    tb = cc["table"]
    y = I.YOKE
    dev = [
        ("yoke grips (r2)", f"built from the measured span {mm(y['span'])}: grips {mm(y['grip'][0])} long from "
                            f"{sgn(y['grip_dz'])} below the hub centre, tops {y['grip'][2]:.0f}° inboard (JTF key, "
                            "P1046408); rev B: 15° outboard from the hub centre, span unused"),
        ("DECISION: yoke vs knees", f"keep the measured hub, grips and pedals: the 95th's knee meets a grip from "
                                    f"{max(o95['roll_contact'], 0):.0f}° roll (neutral pedals). The outcome depends on "
                                    "the estimated inputs more than on the measured ones (sensitivity table): the "
                                    "owner is asked which input to fix, open point 1"),
        ("pedals (r3)", f"±{mm(I.PEDALS['dy'])} centres, {mm(I.PEDALS['pad_wh'][0])} pads, measured face-on "
                        "(P1046408, MFD bezel scale + depth correction); rev B ±90 / 80 [E]. The crew knees sit on the "
                        f"hip-to-pedal line + {mm(I.MANIKIN['knee_splay'])} splay: 95th "
                        f"±{mm(o95['pose']['leg_y'][1])} (rev B ±{mm(I.MANIKIN['knee_y'])})"),
        ("crew SRP vs POH arm (r3)", f"SRP kept at {mm(c['srp_x'])}: the POH arm 4071 is the 50th's CG with the seat "
                                     "full aft (CG table); 60-85 further aft would put the aft-notch headrest as far "
                                     "into the divider and off the render's cushion front 3720 [M]"),
        ("seat tracks (r3)", f"surface-mounted {mm(I.SEAT_TRACKS['h'])} [E] over the whole cabin floor (crew "
                             f"{mm(I.SEAT_TRACKS['crew_h'])}): over the carry-through the floor is <= "
                             f"{mm(I.FLOOR['t_wing'])} [H], too thin for a flush 20-25 track; local channels in the "
                             "spar cap would need the structure (not modelled). The cabin seat heights [M] are read from "
                             "the carpet and include the track; the seat bases stand on the tracks (B-B)"),
        ("lavatory (r3)", f"cabinet {mm(I.LAVATORY['cabinet'][3])} tall [M] (0.33 ring as scale; r2 450 [E]), niche "
                          f"{mm(I.LAVATORY['niche'][0])}-{mm(I.LAVATORY['niche'][1])} [M]; the lower seat puts the "
                          f"95th's knees {mm(cc['lav_knee_past_door'])} past the door line"),
        ("divider (r3)", "curtain drawn: track at the headliner, bundle stowed "
                         f"{'LH' if I.DIVIDER['curtain'][0] < 0 else 'RH'} (PRO 3001, orange; NGX 2281 stows a grey "
                         "one RH); fire extinguisher on the RH divider's fwd face (plan); autoland cup (A-A)"),
        ("SDUs (r2)", f"top {sgn(I.PANEL['sdu_top_dz'])} vs the MFD centre (10-20 under the MFD bezel), reclined "
                      f"{I.PANEL['sdu_recline']:.0f}° (JTF, camera-matched P1046406, P1046408); drawn "
                      f"{mm(I.sdu_height())} tall in view D; rev B -170 / 20°"),
        ("cabin seat arms (r2)", "one armrest, inboard: a deep side panel (base top to 435) with the seat control on "
                                 "its forward end; the 610 ledge is the outboard armrest; rev B drew two arms"),
        ("lavatory (r2)", f"cabinet wall to wall {mm(I.LAVATORY['cabinet'][0])}-{mm(I.LAVATORY['cabinet'][1])}, "
                          f"bowl at the POH arm {mm(I.LAVATORY['bowl_x'])}, shelf + drawer aft of "
                          f"{mm(I.LAVATORY['shelf_x'])}, lit niche, TP holder (P1046411); depth "
                          f"{mm(I.LAVATORY['cabinet'][2])} [E]; rev B 400 x 450 box"),
        ("DECISION: club table", f"keep the measured table (top {mm(I.TABLES['club_p']['top_h'])}, outboard leaf + "
                                 f"unfolding inboard leaf); up to the 50th fits (feet fwd "
                                 f"{tb['p50m']['posture']['shank']:.0f}°); the 95th does not "
                                 f"({sgn(tb['p95m']['full'][0])}): open point 3"),
        ("full rudder (r2)", f"pedal travel ±{mm(I.PEDALS['travel'])} [E] and the toe brake added; the knee checks "
                             "pose the up-knee on the aft pedal and the extended leg on the forward one"),
        ("reach (r2)", f"grasp vs touch: touch targets get the {mm(I.MANIKIN['fingertip'])} fingertip; the 95th "
                       "reaches the PDUs and SDUs harness locked"),
        ("crew armrest hinge (r2)", "in the back's thickness, stowed along the back side; rev B hinged it 125 ahead "
                                    "of the back"),
        ("PAX 1/2 aft-facing club", "render footprint used: 108 aft of the POH-occupant mirror"),
        ("PAX 5 (LH aft)", "POH 8180 used; the marketing plan render shows it 180 fwd"),
        ("LH cabinet", "moved +56 aft of the render (5244) to clear the airstair opening"),
        ("design eye", f"{mm(e[0])}/{mm(abs(e[1]))}/{mm(e[2])} = the 50th eye on the neutral seat; replaces 3980 "
                       f"(info) and {mm(CG.EYE[0])}/{mm(abs(CG.EYE[1]))}/{mm(CG.EYE[2])} (L2); over-nose "
                       f"{v['over_nose_down']:.1f}° vs {CG.vision(CG.EYE)['over_nose_down']:.1f}°"),
        ("vs rev A (legacy 3-D)", f"crew seat BL {mm(c['bl'])} (335; yoke key 372), SRP {mm(c['srp_h'])} above the "
                                  f"floor (300), vertical ±{mm(c['travel_z'])} (±40), back {c['back_deg']:.0f}° (11°), "
                                  f"inboard cushion {mm(c['cushion_in'])} (tunnel plinth); flight-deck floor flush "
                                  f"{mm(I.FLOOR['wl'])} (1240 + 19 step); MFD WL {mm(I.PANEL['mfd_z'])} (1960; notes "
                                  "1830; cabin-photo check 2010 ±50); hood closed onto the WS frame (plate 80-150 "
                                  "below); CB panels on the sidewall above the consoles (below them); FR34 veneer "
                                  f"header + curtain (net); aft wall {mm(I.BAGGAGE['aft_x'])} = divider + "
                                  f"{mm(I.CABIN['length'])} (FR36 9750, render 9744)"),
    ]
    return wtable(ds, x0, y0, [("ITEM", 50.0, "l"), ("DEVIATION / DECISION (vs the references and rev B)",
                                                     x1 - x0 - 50.0, "l")], dev, title="DEVIATIONS & DECISIONS")


KEY_PARAMS = [("CREW_SEAT", "srp_x", "crew SRP STA (centre notch)"), ("CREW_SEAT", "bl", "crew seat BL"),
              ("CREW_SEAT", "srp_h", "crew SRP above the floor"), ("CREW_SEAT", "travel_x", "crew seat travel +/-"),
              ("CREW_SEAT", "travel_z", "crew seat vertical +/-"), ("CREW_SEAT", "back_deg", "crew back angle"),
              ("CREW_SEAT", "cushion_in", "crew cushion inboard"), ("CREW_SEAT", "arm_pivot", "crew armrest hinge"),
              ("PANEL", "glass_x", "PDU glass STA"), ("PANEL", "mfd_z", "MFD centre WL"),
              ("PANEL", "sdu_top_dz", "SDU top vs MFD centre"), ("PANEL", "sdu_recline", "SDU recline"),
              ("YOKE", "hub_dz", "yoke hub vs MFD centre"), ("YOKE", "span", "yoke grips overall"),
              ("YOKE", "grip", "grip length / r / cant"), ("YOKE", "grip_dz", "grip bottoms vs hub"),
              ("YOKE", "roll", "yoke roll +/-"), ("PEDALS", "heel_x", "pedal heel point STA"),
              ("PEDALS", "travel", "rudder pedal travel +/-"), ("PEDESTAL", "top_h", "pedestal top above floor"),
              ("DIVIDER", "x_aft", "divider aft face"), ("EXEC_SEAT", "bl", "cabin seat BL"),
              ("EXEC_SEAT", "length", "cabin seat length"), ("EXEC_SEAT", "arm_w", "cabin seat arm"),
              ("EXEC_SEAT", "srp_h", "cabin SRP above floor"), ("LEDGES", "top_h", "ledge top above the floor"),
              ("TABLES.club_p", "top_h", "club table top"), ("TABLES.club_p", "leaf", "club table outboard leaf"),
              ("LAVATORY", "cabinet", "lav cabinet x0 x1 d h"), ("BAGGAGE", "partition_x", "FR34 partition"),
              ("LINING", "side", "sidewall lining"), ("MANIKIN", "fingertip", "touch reach allowance"),
              ("CRITERIA", "knee_ext", "extended-knee limit"), ("PEDALS", "dy", "pedal centres +/-"),
              ("SEAT_TRACKS", "h", "cabin seat track height")]


def _param(tab, key):
    """interior.<TAB>[key], TAB may be dotted into a dict ('TABLES.club_p')."""
    d = I
    for part in tab.split("."):
        d = d[part] if isinstance(d, dict) else getattr(d, part)
    return d[key]


def _fmt(v, key=""):
    if isinstance(v, tuple):
        return " / ".join(f"{float(q):.0f}°" if abs(float(q)) >= 8 else f"{float(q) * 1000:.0f}" for q in v)
    if key.endswith("_deg") or key in ("roll", "sdu_recline", "knee_ext"):
        return f"{float(v):.0f}°"
    return f"{float(v) * 1000:.0f}"


def params_block(ds, x0, y0, x1, ctx):
    rows = []
    for tab, key, lab in KEY_PARAMS:
        val = _param(tab, key)
        rows.append((lab, _fmt(val, key), I.src(val)))
    return wtable(ds, x0, y0, [("PARAMETER", 46.0, "l"), ("VALUE", 44.0, "r"),
                               ("SOURCE NOTE (model/interior.py)", x1 - x0 - 90.0, "l")], rows,
                  title="KEY PARAMETERS ([S] SOURCED [M] MEASURED [E] ESTIMATED [H] HARD)")


def layouts_block(ds, x0, y0, x1, ctx):
    lay = []
    for k_ in ("EX-8S", "STD-9S"):
        L = I.SEAT_LAYOUTS[k_]
        lay.append((k_, "LH", " ".join(mm(s["occ"]) for s in L["seats"] if s["side"] < 0)))
        lay.append(("", "RH", " ".join(mm(s["occ"]) for s in L["seats"] if s["side"] > 0)))
    return wtable(ds, x0, y0, [("LAYOUT", 28.0, "l"), ("SIDE", 16.0, "c"),
                               ("OCCUPANT ARMS (POH), FWD -> AFT", x1 - x0 - 44.0, "m")], lay,
                  title="OTHER POH LAYOUTS (DATA ONLY)")


def notes_items(ctx):
    cc = ctx["crew"]
    f_, u_ = cc["eye_off"]
    return [
        "Sheet L6 is drawn from the parameter tables of model/interior.py and the fuselage, openings and glazing "
        "parameters (L1-L3), never from the mesh. Each value carries a source tag: [S] sourced, [M] measured from "
        "photos / renders, [E] estimated, [H] hard constraint.",
        "Seat stations: POH NGX Report 02406 weight-and-balance occupant arms (POH datum = model datum). EX-6S-2 is "
        "the PRO standard 6-seat layout: aft-facing club pair, forward-facing club pair, staggered aft pair, forward "
        "RH lavatory.",
        f"Crew seat: IPECO 3A318-type, travel ±{mm(I.CREW_SEAT['travel_x'])} in 9 holes (POH), vertical "
        f"±{mm(I.CREW_SEAT['travel_z'])} (est.). Design eye = the 50th-pct eye on the neutral seat = SRP + "
        f"{mm(f_)} fwd / {mm(u_)} up; the 95th (seat down) and 5th male (seat up) reach it. Accommodated range at the "
        f"design eye as drawn: 5th male - 95th male; the 5th female sits {mm(-cc['occ']['p5f']['eye_dz'])} below it "
        "(open point 2).",
        f"Manikins: {I.MANIKIN['name']} (stature {mm(I.MANIKIN['stature'])}, sitting height {mm(I.MANIKIN['sit_h'])}, "
        f"eye {mm(I.MANIKIN['eye_sit'])}), scaled uniformly for the 50th / 5th male and 5th female. Crew: each sets "
        f"seat height, notch and pedal crank (knee angle ~{I.CRITERIA['knee_angle']:.0f}°); feet on the pedals, hands "
        f"on the grips, knees on the hip-to-pedal line (pedals ±{mm(I.PEDALS['dy'])} [M]); full rudder moves one "
        f"pedal {mm(I.PEDALS['travel'])} forward and the other as far aft. Cabin: upright, outboard (TTL), feet flat "
        "under the knees unless noted. Sections A-A / B-B draw what lies forward of the cut (legs, hands) in phantom.",
        f"Seat tracks: surface-mounted, {mm(I.SEAT_TRACKS['h'])} cabin / {mm(I.SEAT_TRACKS['crew_h'])} crew [E], over "
        "the carry-through too; the seat heights include them.",
        f"Lining: headliner {mm(I.LINING['crown'])} below the OML at the crown, sidewall {mm(I.LINING['side'])}, "
        f"giving the published {I.CABIN['width']:.2f} x {I.CABIN['height']:.2f} cabin; floor WL {mm(I.FLOOR['wl'])} "
        "flush from the pedals to the baggage wall. The pedestal stands on a carpeted plinth over the nose-wheel "
        "tunnel (gear, hard).",
        "Stage 2 only: the 3-D interior is still rev A and is rebuilt from these tables after the owner's review.",
    ]


def open_points_items(ctx):
    cc, kc = ctx["cabin"], ctx["crew"]
    c = I.CREW_SEAT
    o = kc["occ"]
    o95, o50, o5f = o["p95m"], o["p50m"], o["p5f"]
    tb = cc["table"]
    po50, po95 = tb["p50m"]["posture"], tb["p95m"]["posture"]
    p52 = I.crew_setting(1.575 / I.MANIKIN["stature"])
    r52 = I.rudder_checks(p52)
    sens = dict(ctx["sens"])

    def row(k):
        return sens[k]
    s0, sw, sk, sh = (row(k) for k in ("as set", "knees 30 wider (splay +30)", "knee target 130 deg (120)",
                                       "yoke hub 50 higher"))
    lim = I.CRITERIA["knee_ext"]
    e5 = o5f["pose"]["eye"]
    v200 = CG.vision(np.array([e5[0], -0.200, e5[1]]))["over_nose_down"]
    return [
        f"KNEES vs YOKE: WHICH INPUT TO FIX? With the measured hub, grips and pedals (grip bottoms WL "
        f"{mm(I.PANEL['mfd_z'] + I.YOKE['hub_dz'] + I.YOKE['grip_dz'])}, pedals ±{mm(I.PEDALS['dy'])}), the 95th's "
        f"knee meets a grip from {max(o95['roll_contact'], 0):.0f}° roll with neutral pedals (50th "
        f"{max(o50['roll_contact'], 0):.0f}°); with full rudder the 95th touches it wings level "
        f"({sgn(o95['rud_pitch'])}) and the 50th from {max(o50['rud_roll_contact'], 0):.0f}°. The estimated inputs move "
        f"this more than the measured ones (sensitivity table): knees 30 wider -> 95th neutral contact "
        f"{_deg(sw['p95m']['contact'])}; a 130° knee target (seat further aft) -> {_deg(sk['p95m']['contact'])}, full "
        f"rudder {sgn(sk['p95m']['rud'])}, but the 50th's forward rudder needs {sk['p50m']['ext']:.0f}° "
        f"(> {lim:.0f}°); the hub 50 higher -> {_deg(sh['p95m']['contact'])}, full-rudder contact from "
        f"{_deg(sh['p95m']['rud_contact'])}. Please choose what to pin down: the seat-setting rule (knee target), the "
        "knee spacing, the rudder travel, the hub height, or the roll travel / a roll limit. Wanted: the control-wheel "
        "roll and rudder travel (AMM / POH) and a side-on photo of a seated pilot at the yoke.",
        f"5TH-FEMALE ACCOMMODATION. At the forward notch, pedals cranked fully aft and the seat full up "
        f"(+{mm(I.CREW_SEAT['travel_z'])}, the travel limit [E]), her eye is {mm(-o5f['eye_dz'])} below the design eye: "
        f"over the nose {o5f['over_nose']:.1f}° along her BL (design eye {kc['vision']['over_nose_down']:.1f}°), "
        f"{v200:.1f}° along BL 200; full forward rudder straightens her knee to {o5f['ext_knee']:.0f}° (limit "
        f"{lim:.0f}° [E]; a 5 ft 2 in pilot, scale {1.575 / I.MANIKIN['stature']:.2f}: {r52['ext_knee']:.0f}°). As drawn "
        "the station accommodates 5th male - 95th male. Options: a booster cushion, more vertical travel (the IPECO "
        "3A318 figure is wanted; ±51 is [E]), or state the range as 5M-95M.",
        f"CLUB TABLE. Deployed (top {mm(I.TABLES['club_p']['top_h'])}, under the ledge cap), the 95th's knees are "
        f"{mm(-tb['p95m']['full'][0])} into it and the 50th's {mm(-tb['p50m']['full'][0])} with the feet under the "
        f"knees (the outboard leaf alone: the same, the outboard leg is under it). The 50th fits with the feet "
        f"{po50['shank']:.0f}° forward (toes {mm(po50['toe_gap'])} short of the facing seat's base); the 95th would "
        f"need {po95['shank']:.0f}° and put his feet {mm(-po95['toe_gap'])} under it. Kept: the table serves up to "
        "about the 50th. Confirm, or re-measure the table / ledge height.",
        f"Aft-facing club PAX 1/2: plan render (used) or POH-occupant mirror? The render leaves "
        f"{mm(cc['exit_clear'])} of the {mm(cc['exit_x'][1] - cc['exit_x'][0])} exit hatch clear of the PAX 2 cushion; "
        f"the mirror gives a {mm(cc['club_gap_mirror'])} club gap (render {mm(cc['club_gap'])}, 95th toes pass "
        f"{mm(cc['club_toes_pass'])}).",
        f"Design eye {mm(kc['eye'][0])} / {mm(abs(kc['eye'][1]))} / {mm(kc['eye'][2])} (over-nose "
        f"{kc['vision']['over_nose_down']:.1f}°) to replace cockpit_glazing.EYE (L2) and the viewer camera.",
        f"Tunnel plinth (gear, {mm(I.pedestal_plinth()[2] * 2)} wide, {mm(I.pedestal_plinth()[3] - I.FLOOR['fd_wl'])} "
        f"tall to STA {mm(I.pedestal_plinth()[1])}): the crew cushions are trimmed to {mm(c['cushion_in'])} inboard "
        "to clear it; the photos show symmetric cushions and no step at the pedestal foot. Can the tunnel end or drop?",
        f"Lavatory: cabinet wall to wall, {mm(I.LAVATORY['cabinet'][2])} deep [E], leaves "
        f"{mm(cc['lav_floor'])} of floor to the bi-fold line (BL {mm(I.LAVATORY['inboard_bl'])}); a seated 95th's "
        f"knees still reach {mm(cc['lav_knee_past_door'])} past it. Door line / cabinet depth to confirm.",
        f"Cabin seated eye above the window top (95th {mm(cc['eye_wl'])}, 50th {mm(cc['eye_wl_p50'])} vs "
        f"{mm(cc['win'][1])}): a seated-passenger photo would test the cushion {mm(I.EXEC_SEAT['cushion_top'])} / SRP "
        f"{mm(I.EXEC_SEAT['srp_h'])} (the windows are fixed by L3).",
        f"Crew SRP {mm(c['srp_x'])} vs the POH pilot arm 4071: the 50th's CG is {sgn(ctx['cg'][0][4])} from it at the "
        f"centre notch and {sgn(ctx['cg'][1][4])} with the seat full aft, so the POH arm is read as a full-aft value "
        "and the SRP is kept (the aft-notch headrest is already at the divider). Confirm the POH arm convention; "
        f"crew seat vertical travel (±{mm(c['travel_z'])} est.), back / headrest heights (side-on photo), MFD WL; "
        "interior scheme and cabin height 1.47 vs 1.45.",
    ]


def notes_block(ds, x0, y0, x1, ctx):
    return M.notes(ds, x0, y0, x1, notes_items(ctx), title="NOTES (SHEET L6)", size=TXT, line_h=LH)


def open_block(ds, x0, y0, x1, ctx):
    return M.notes(ds, x0, y0, x1, open_points_items(ctx), title="OPEN POINTS FOR THE OWNER", size=TXT, line_h=LH)


def _height(fn, width, ctx):
    """Height (mm) a block takes at this width: drawn once on a scratch sheet."""
    tmp = M.DrawingSheet("tmp", "tmp")
    return fn(tmp, 0.0, 0.0, width, ctx)


REV_SHORT = (("A", "-", "first issue (legacy 3-D interior)"),
             ("B", "2026-09-24", "Stage-2 parameter tables, checks; review r1"),
             ("C", "2026-09-26", "review r2 + r3 (list on sheet 1): sensitivity, CG cross-check, 5th-female point"),
             ("D", "2026-09-26", "Stage-3 review r2: sheepskin in the crew outline, yoke grips, curtain / track"),
             ("E", "2026-09-27", "Stage-3 review r3: exec legrest, PC-24 yoke face, PCL grip, armrest / pedestal row"),
             ("F", "2026-10-03", "Stage-4 final judge r1: yoke shield a full U, grips 160, heads r 18 [M]"))


def revisions(ds, x0, y0, x1, ctx):
    return revisions_block(ds, x0, y0, x1, size=3.0, title_size=TITLE, rows=REV_SHORT)


def draw(ds):
    ds.frame_and_title(fields=dict(date=SHEET["date"]))
    ctx = context()
    ctx["sens"] = I.crew_sensitivity()
    ctx["cg"] = I.cg_crosscheck()
    gap = 5.0
    # column 1: crew; column 2: cabin, deviations; column 3: parameters, layouts; the sensitivity, CG cross-check, open
    # points, notes and revisions go where they fit (column 3 stops above the title block)
    plan = [(0, crew_occupants), (0, crew_general), (0, reach_block), (0, sensitivity_block), (0, notes_block),
            (1, cabin_block), (1, deviations_block), (1, open_block), (1, revisions),
            (2, params_block), (2, layouts_block), (2, cg_block)]
    ys = [Y_TOP, Y_TOP, Y_TOP]
    for ci, fn in plan:
        x0, x1 = COLS[ci]
        ys[ci] = fn(ds, x0, ys[ci], x1, ctx) + gap
    for ci, y in enumerate(ys):
        lim = Y_TB if ci == 2 else Y_MAX
        if y - gap > lim:
            ds.log.append(f"L6B column {ci + 1} runs to y {y - gap:.0f} (> {lim:.0f})")


if __name__ == "__main__":
    M.main(["L6B"] + sys.argv[1:])
