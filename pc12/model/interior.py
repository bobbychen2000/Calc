"""
Interior (for the cutaway view) and primary structure (for the X-ray view).

Flight deck: PC-12 PRO style Garmin G3000 PRIME -- three 14-in touchscreen
displays and two touchscreen secondary displays on the pedestal, dual yokes.
Cabin: 6-seat executive layout (4-seat club + 2 forward-facing), flat floor at
fuselage.CABIN_FLOOR_WL (5.16 m x 1.52 m x 1.47 m cabin, floor at least 1.30 m wide),
the entry aisle clear of the airstair door (door panel STA 4.65-5.29), baggage area
behind a net at the cargo door.
Structure: fuselage frames at the Pilatus frame stations (fuselage.FRAMES, numbered
frames interpolated between them) interrupted at the openings, stringers, wing spars
and ribs (representative, not the certified structural drawing).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import (Mesh, superellipsoid, box, cylinder, sweep_tube, rotation_matrix, grid_surface,
                      planar_cap, revolve, trim)
from model.parts import Part
from model import fuselage as F
from model import wing as W

FLOOR_Z = F.CABIN_FLOOR_WL        # 1.259: crown 2.769 - lining 0.040 - cabin height 1.470 (decision D1)
LINING = 0.085


def rbox(center, size, e=0.28, R=None, n=14):
    return superellipsoid(center, np.asarray(size) / 2, (e, e), nu=n, nv=n + 6, R=R)


def roty(a):
    return rotation_matrix((0, 1, 0), np.radians(a))


def seat(x, y, facing=+1, floor=FLOOR_Z, width=0.52, crew=False, back_h=0.74, head_w=0.55):
    """facing=+1 forward-facing (back toward +x), -1 aft-facing."""
    f = facing
    parts_leather, parts_frame = [], []
    cz = floor + 0.40
    parts_leather.append(rbox((x, y, cz), (0.50, width, 0.14), e=0.35))
    back_c = np.array([x + f * 0.24, y, floor + 0.41 + back_h / 2])
    parts_leather.append(rbox(back_c, (0.14, width, back_h), e=0.35, R=roty(-f * 12)))
    parts_leather.append(rbox(back_c + [f * 0.07, 0, back_h / 2 + 0.07], (0.12, width * head_w, 0.15), e=0.45,
                              R=roty(-f * 12)))
    for s in (-1, 1):
        parts_leather.append(rbox((x + f * 0.02, y + s * (width / 2 + 0.03), floor + 0.58), (0.42, 0.07, 0.07), e=0.5))
    parts_frame.append(box((x, y, floor + 0.17), (0.34, width * 0.7, 0.30)))
    if crew:
        # 5-point harness shoulder straps
        for sg in (-1, 1):
            parts_frame.append(box(back_c + [-f * 0.08, sg * 0.10, 0.06], (0.01, 0.045, back_h * 0.7)))
    return Mesh.merge(parts_leather), Mesh.merge(parts_frame)


FD_FLOOR_Z = 1.24
EYE_Y = 0.335


def section_limit(x, z, inset):
    """Half-width available inside the lining at station x, water line z."""
    return max(0.0, float(F.side_y(x, z)) - inset)


def fitted_plate(x0, x1, z, inset=0.06, n=16, thick=0.03, y_min=0.0):
    """Horizontal plate following the fuselage section (floors); y_min > 0 leaves a centre slot |y| < y_min."""
    xs = np.linspace(x0, x1, n)
    hw = np.array([min(section_limit(x, z, inset), section_limit(x, z - thick, inset)) for x in xs])
    if y_min <= 0:
        tops = [np.vstack([np.stack([xs, hw, np.full(n, z)], 1), np.stack([xs[::-1], -hw[::-1], np.full(n, z)], 1)])]
    else:
        tops = [np.vstack([np.stack([xs, s * hw, np.full(n, z)], 1), np.stack([xs[::-1], np.full(n, s * y_min), np.full(n, z)], 1)])
                for s in (1, -1)]
    out = []
    for top in tops:
        out += [planar_cap(top, (0, 0, 1)), planar_cap(top - [0, 0, thick], (0, 0, -1))]
    return Mesh.merge(out)


def build_flightdeck(parts):
    m_leather, m_frame, m_panel, m_metal = [], [], [], []
    screens = {}
    # flight-deck floor (raised over the nose-wheel well), fitted to the section, with the nose-wheel tunnel hump
    # under the centre pedestal (gear.NOSE_TUNNEL: the retracted nose wheel stows there)
    from model.gear import NOSE_TUNNEL as TU
    m_frame.append(fitted_plate(3.26, TU["x0"], FD_FLOOR_Z, inset=0.07, n=4))
    m_frame.append(fitted_plate(TU["x0"], TU["x1"], FD_FLOOR_Z, inset=0.07, n=16, y_min=TU["hy"] + 0.012))
    m_frame.append(fitted_plate(TU["x1"], 4.34, FD_FLOOR_Z, inset=0.07, n=6))
    m_panel.append(rbox((0.5 * (TU["x0"] + TU["x1"]), 0.0, 0.5 * (FD_FLOOR_Z - 0.03 + TU["z_top"] + 0.025)),
                        (TU["x1"] - TU["x0"] + 0.02, 2 * TU["hy"] + 0.04, TU["z_top"] + 0.025 - FD_FLOOR_Z + 0.03),
                        e=0.18))
    # instrument panel: a tilted plate whose outline follows the fuselage section
    tilt = np.radians(12)
    Rp = roty(-12)
    pc = np.array([3.47, 0, 1.84])
    n_p = Rp @ np.array([1.0, 0, 0])
    up_p = Rp @ np.array([0, 0, 1.0])
    rows = []
    for v in np.linspace(-0.22, 0.20, 9):
        p = pc + v * up_p
        rows.append((v, section_limit(p[0], p[2], 0.085)))
    outline = [pc + v * up_p + w * np.array([0, 1.0, 0]) for v, w in rows] + \
              [pc + v * up_p - w * np.array([0, 1.0, 0]) for v, w in rows[::-1]]
    outline = np.array(outline)
    front = planar_cap(outline + n_p * 0.02, n_p)
    back = planar_cap(outline - n_p * 0.03, -n_p)
    k = len(outline)
    Vs = np.vstack([outline + n_p * 0.02, outline - n_p * 0.03])
    ii = np.arange(k)
    Fs = np.vstack([np.stack([ii, (ii + 1) % k, (ii + 1) % k + k], 1), np.stack([ii, (ii + 1) % k + k, ii + k], 1)])
    m_panel += [front, back, Mesh(Vs, Fs)]
    # glareshield: shelf under the windshield base, fitted to the section
    gz = 2.075
    m_panel.append(fitted_plate(3.40, 3.63, gz, inset=0.10, n=10, thick=0.035))
    # three 14-in touchscreen PDUs (G3000 PRIME)
    for key, y in (("screen_pfd", -0.368), ("screen_mfd", 0.0), ("screen_pfd", 0.368)):
        c = pc + n_p * 0.028 + np.array([0, y, -0.01])
        bezel = box(c, (0.012, 0.35, 0.225), R=Rp)
        glass = box(c + n_p * 0.007, (0.004, 0.312, 0.192), R=Rp)
        m_metal.append(bezel)
        screens.setdefault(key, []).append(glass)
    # centre pedestal with two 7-in touchscreen SDUs + power lever + cursor control
    ped_c = np.array([3.80, 0, FD_FLOOR_Z + 0.27])
    m_panel.append(rbox(ped_c, (0.62, 0.22, 0.52), e=0.2))
    Rt = roty(-35)
    for kk, x in enumerate((3.60, 3.84)):
        c = np.array([x, 0, FD_FLOOR_Z + 0.55 - 0.08 * kk])
        m_metal.append(box(c, (0.19, 0.17, 0.03), R=Rt))
        screens.setdefault("screen_sdu", []).append(box(c + Rt @ np.array([0, 0, 0.017]), (0.145, 0.125, 0.004), R=Rt))
    m_metal.append(cylinder((4.00, 0.0, FD_FLOOR_Z + 0.54), (3.96, 0.0, FD_FLOOR_Z + 0.68), 0.012, n=8))
    m_panel.append(rbox((3.96, 0.0, FD_FLOOR_Z + 0.70), (0.05, 0.09, 0.05), e=0.5))
    m_panel.append(rbox((4.02, 0.07, FD_FLOOR_Z + 0.53), (0.07, 0.05, 0.03), e=0.5))     # cursor control device
    # PC-24-style yokes
    for y in (-EYE_Y, EYE_Y):
        m_metal.append(cylinder((3.47, y, 1.66), (3.66, y, 1.70), 0.022, n=12))
        m_panel.append(rbox((3.68, y, 1.73), (0.05, 0.10, 0.11), e=0.4))
        for sg in (-1, 1):
            m_panel.append(cylinder((3.69, y, 1.72), (3.70, y + sg * 0.13, 1.78), 0.018, n=10))
            m_panel.append(cylinder((3.70, y + sg * 0.13, 1.78), (3.68, y + sg * 0.14, 1.86), 0.02, n=10))
        for sg in (-1, 1):   # rudder pedals
            m_frame.append(box((3.38, y + sg * 0.085, FD_FLOOR_Z + 0.10), (0.03, 0.075, 0.17), R=roty(-25)))
    # crew seats: eye point ~ WL 2.36, headrest clear of the roof curvature
    for y in (-EYE_Y, EYE_Y):
        a, b = seat(4.02, y, +1, floor=FD_FLOOR_Z, width=0.44, crew=True, back_h=0.64, head_w=0.50)
        m_leather.append(a)
        m_frame.append(b)
    p = Part("flight_deck", "Flight deck: Garmin G3000 PRIME, PC-24-style yokes, crew seats", "interior",
             explode=(0, 0, 0.0), group="Interior",
             material_note="3 x 14-in touchscreen PDUs, 2 x 7-in touchscreen SDUs",
             info={"avionics": "Garmin G3000 PRIME (PC-12 PRO)", "displays": "3 x 14 in + 2 x 7 in",
                   "design eye": "STA 3,980 / BL +/-335 / WL 2,360 (est.)"})
    p.add(Mesh.merge(m_leather), "leather_dark").add(Mesh.merge(m_frame), "metal_dark")
    p.add(Mesh.merge(m_panel), "panel_black").add(Mesh.merge(m_metal), "metal_dark")
    for key, lst in screens.items():
        for g in lst:
            p.add(g, key)
    parts[p.id] = p


CABIN_X = (4.40, 9.52)                 # cabin floor (cockpit divider -> aft baggage bay)
SEAT_ROWS = ((5.72, -1), (6.98, +1), (7.98, +1))   # (seat centre STA, facing): club pair, club pair, aft pair
SEAT_Y = 0.40
TABLE_X = 6.35
BAGGAGE_NET_X = 8.60


def ledge_spans():
    """Side-ledge x-spans per side, clear of the door panels (and 0.10 m of margin)."""
    from model.fuselage_parts import openings_table
    out = {}
    for side in (-1, 1):
        spans = [(5.10, 8.25)]
        for r in openings_table():
            if r["side"] != side or r["kind"] not in ("door",) or r.get("panel") is None:
                continue
            a, b = r["panel"]["x0"] - 0.10, r["panel"]["x1"] + 0.10
            new = []
            for x0, x1 in spans:
                if b <= x0 or a >= x1:
                    new.append((x0, x1))
                    continue
                if a > x0:
                    new.append((x0, a))
                if b < x1:
                    new.append((b, x1))
            spans = [sp for sp in new if sp[1] - sp[0] > 0.3]
        out[side] = spans
    return out


def build_cabin(parts):
    leather, frame, carpet, wood, lin = [], [], [], [], []
    # floor panels (flat floor at CABIN_FLOOR_WL)
    carpet.append(fitted_plate(*CABIN_X, FLOOR_Z, inset=0.055, n=28))
    # side ledges / cabinets with wood caps, interrupted at the doors
    for s_, spans in ledge_spans().items():
        for x0, x1 in spans:
            xm, L = 0.5 * (x0 + x1), x1 - x0
            lin.append(rbox((xm, s_ * 0.615, FLOOR_Z + 0.21), (L, 0.08, 0.42), e=0.3))
            wood.append(box((xm, s_ * 0.60, FLOOR_Z + 0.425), (L, 0.12, 0.02)))
    # executive seating: 4-seat club (the forward pair faces aft) + 2 forward-facing
    for x, f in SEAT_ROWS:
        for y in (-SEAT_Y, SEAT_Y):
            a, b = seat(x, y, f)
            leather.append(a)
            frame.append(b)
    # club tables
    for y in (-SEAT_Y, SEAT_Y):
        wood.append(rbox((TABLE_X, y * 1.2, FLOOR_Z + 0.68), (0.46, 0.34, 0.03), e=0.4))
    # aft baggage net frame
    for sg in (-1, 1):
        frame.append(cylinder((BAGGAGE_NET_X, sg * 0.55, FLOOR_Z), (BAGGAGE_NET_X, sg * 0.55, FLOOR_Z + 1.15),
                              0.012, n=8))
    frame.append(cylinder((BAGGAGE_NET_X, -0.55, FLOOR_Z + 1.15), (BAGGAGE_NET_X, 0.55, FLOOR_Z + 1.15), 0.012, n=8))
    p = Part("cabin_interior", "Cabin: executive 6-seat interior", "interior", group="Interior",
             material_note="Leather seats, wood veneer ledges",
             info={"cabin": "5.16 x 1.52 x 1.47 m", "floor": f"WL {FLOOR_Z * 1000:.0f}, "
                   f"{F.cabin_floor_width(6.0):.2f} m wide inside the lining", "seats": "6 executive (up to 9)"})
    p.add(Mesh.merge(leather), "leather").add(Mesh.merge(frame), "metal_dark")
    p.add(Mesh.merge(carpet), "carpet").add(Mesh.merge(wood), "wood").add(Mesh.merge(lin), "lining")
    parts[p.id] = p


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def frame_ring(x, depth=0.055, n=144):
    t = np.linspace(0, 1, n, endpoint=False)
    outer = F.section(np.full(n, x), t)
    c = np.array([x, 0, float(F.z_mw(x))])
    d = outer - c
    dn = d / np.linalg.norm(d, axis=1, keepdims=True)
    o = outer - dn * 0.004
    i = outer - dn * (0.004 + depth)
    V = np.vstack([o, i])
    k = np.arange(n)
    Fc = np.vstack([np.stack([k, (k + 1) % n, (k + 1) % n + n], 1), np.stack([k, (k + 1) % n + n, k + n], 1)])
    UV = np.vstack([np.stack([np.full(n, x), t], 1)] * 2)
    return Mesh(V, Fc, UV=UV)


def cut_openings(m, margin=0.03):
    """Interrupt structure at door / window / windshield cut-outs."""
    from model.fuselage_parts import openings_field
    from cad.mesh import trim
    f = openings_field(m) - margin
    return trim(m, f, "positive") if (f < 0).any() else m


def frame_stations():
    """Numbered fuselage frames: the labelled Pilatus frames (fuselage.FRAMES FR10 ... FR40) with the frames between
    them interpolated at equal pitch, plus FR41 ... ahead of the tail-cone closure.  Returns [(name, STA)]."""
    import re
    lab = sorted((int(re.sub(r"\D", "", k)), v) for k, v in F.FRAMES.items() if k.startswith("FR"))
    out = []
    for (n0, x0), (n1, x1) in zip(lab[:-1], lab[1:]):
        for k in range(n0, n1):
            out.append((f"FR{k}", x0 + (x1 - x0) * (k - n0) / (n1 - n0)))
    n, x = lab[-1]
    pitch = (lab[-1][1] - lab[-2][1]) / (lab[-1][0] - lab[-2][0])
    from model import empennage as E
    while x < float(E.tail_cut_x(F.z_bot(min(x, F.STA["tail_end"])))) - 0.05:
        out.append((f"FR{n}", x))
        n, x = n + 1, x + pitch
    return out


def build_structure(parts):
    from model import empennage as E
    from model.fuselage_parts import bulkhead, nose_trunnion_notch
    rings = []
    frames = frame_stations()
    for name, x in frames:
        r = frame_ring(x, depth=0.065 if x < 10 else 0.045)
        r = cut_openings(r)
        if (E.tail_cut_field(r.V[:, 0], r.V[:, 2]) > 0).any():
            r = trim(r, E.tail_cut_field(r.V[:, 0], r.V[:, 2]), "negative")
        rings.append(r)
    # stringers: kept above and below the window belt (belt WL 1.995-2.380 -> gap 1.95-2.43), to the tail closure
    strs = []
    x_end = float(E.tail_cut_x(2.2)) - 0.02
    for t in np.linspace(0, 1, 28, endpoint=False):
        z6 = float(F.section(np.array(6.0), np.array(t))[2])
        if 1.95 < z6 < 2.43:
            continue
        xs = np.linspace(3.05, x_end, 110)
        P = F.section(xs, np.full_like(xs, t))
        c = np.stack([xs, np.zeros_like(xs), F.z_mw(xs)], 1)
        d = P - c
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        tube = sweep_tube(P - d * 0.015, 0.008, n=6, cap=False)
        tube.UV = np.stack([tube.V[:, 0], np.full(len(tube.V), t)], 1)
        tube = trim(tube, E.tail_cut_field(tube.V[:, 0], tube.V[:, 2]) + 0.02, "negative")
        strs.append(cut_openings(tube, margin=0.02))
    # pressure bulkheads (forward one notched round the nose-gear trunnion, like the firewall)
    bh = [bulkhead(F.STA["firewall"] + 0.01, 0.97, notch=nose_trunnion_notch, normal=(1, 0, 0)),
          bulkhead(F.STA["aft_pressure_bulkhead"] + 0.01, 0.97, normal=(1, 0, 0))]
    # wing spars (front ~15 %, rear ~66 %) and ribs; the carry-through flattened under the cabin floor (wing.py)
    sp = []
    for frac in (0.15, 0.66):
        rows = []
        ys = np.linspace(-W.SEMI + 0.05, W.SEMI - 0.05, 60)
        for y in ys:
            s = W.section_at(abs(y))
            lo = s.lower(np.array(frac)) * [1, np.sign(y) if y != 0 else 1, 1]
            up = s.upper(np.array(frac)) * [1, np.sign(y) if y != 0 else 1, 1]
            lo = np.array([lo[0], y, lo[2] + 0.004])
            up = np.array([up[0], y, up[2] - 0.004])
            rows.append(np.linspace(lo, up, 4))
        m = grid_surface(np.array(rows))
        m.V = W.centre_section_clamp(m.V, margin=0.004)
        sp.append(m)
    ribs = []
    for y in list(np.arange(0.9, W.SEMI - 0.2, 0.55)):
        s = W.section_at(y)
        xx = np.linspace(0.02, 0.97, 30)
        loop = np.vstack([s.lower(xx[::-1]) + [0, 0, 0.004], s.upper(xx[1:]) - [0, 0, 0.004]])
        for sg in (1, -1):
            r = planar_cap(loop * [1, sg, 1], (0, sg, 0))
            ribs.append(r)
    p = Part("structure", "Primary structure: frames, stringers, spars, ribs", "structure", group="Structure",
             material_note="2024-T3 / 7075-T6, zinc-chromate primed",
             info={"frames": f"{len(frames)}: {frames[0][0]} (STA {frames[0][1] * 1000:.0f}) - {frames[-1][0]} "
                             f"(STA {frames[-1][1] * 1000:.0f}), labelled frames per the Pilatus drawing",
                   "wing": "2-spar box, ribs @ 550 mm"})
    p.add(Mesh.merge(rings + bh), "zinc_chromate").add(Mesh.merge(strs), "zinc_chromate")
    p.add(Mesh.merge(sp + ribs), "interior_green")
    parts[p.id] = p


def build(parts):
    build_flightdeck(parts)
    build_cabin(parts)
    build_structure(parts)
    return parts
