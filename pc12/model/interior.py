"""
Interior (for the cutaway view) and primary structure (for the X-ray view).

Flight deck: PC-12 PRO style Garmin G3000 PRIME -- three 14-in touchscreen
displays and two touchscreen secondary displays on the pedestal, dual yokes.
Cabin: 6-seat executive layout (4-seat club + 2 forward-facing), flat floor
(5.16 m x 1.52 m x 1.47 m cabin, 1.30 m floor width), aft baggage area behind
the cargo door.
Structure: fuselage frames and stringers, wing spars and ribs (representative
pitch, not the certified structural drawing).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import (Mesh, superellipsoid, box, cylinder, sweep_tube, rotation_matrix, grid_surface,
                      planar_cap, revolve)
from model.parts import Part
from model import fuselage as F
from model import wing as W

FLOOR_Z = 1.12
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


def fitted_plate(x0, x1, z, inset=0.06, n=16, thick=0.03):
    """Horizontal plate following the fuselage section (flight-deck floor)."""
    xs = np.linspace(x0, x1, n)
    hw = np.array([section_limit(x, z, inset) for x in xs])
    top = np.vstack([np.stack([xs, hw, np.full(n, z)], 1), np.stack([xs[::-1], -hw[::-1], np.full(n, z)], 1)])
    cap = planar_cap(top, (0, 0, 1))
    bot = planar_cap(top - [0, 0, thick], (0, 0, -1))
    return Mesh.merge([cap, bot])


def build_flightdeck(parts):
    m_leather, m_frame, m_panel, m_metal = [], [], [], []
    screens = {}
    # flight-deck floor (raised over the nose-wheel well), fitted to the section
    m_frame.append(fitted_plate(3.26, 4.34, FD_FLOOR_Z, inset=0.07))
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


def build_cabin(parts):
    leather, frame, carpet, wood, lin = [], [], [], [], []
    # floor panels (flat floor 1.30 m wide)
    carpet.append(fitted_plate(4.46, 9.52, FLOOR_Z, inset=0.055, n=24))
    # side ledges / cabinets with wood caps
    for s in (-1, 1):
        lin.append(rbox((6.45, s * 0.615, FLOOR_Z + 0.21), (3.2, 0.08, 0.42), e=0.3))
        wood.append(box((6.45, s * 0.60, FLOOR_Z + 0.425), (3.2, 0.12, 0.02)))
    # executive seating: 4-seat club + 2 forward-facing
    layout = [(5.25, -1), (6.55, +1), (7.65, +1)]
    for x, f in layout:
        for y in (-0.40, 0.40):
            a, b = seat(x, y, f)
            leather.append(a)
            frame.append(b)
    # club tables
    for y in (-0.40, 0.40):
        wood.append(rbox((5.90, y * 1.2, FLOOR_Z + 0.68), (0.46, 0.34, 0.03), e=0.4))
    # aft baggage net frame + divider
    for sg in (-1, 1):
        frame.append(cylinder((8.32, sg * 0.55, FLOOR_Z), (8.32, sg * 0.55, FLOOR_Z + 1.18), 0.012, n=8))
    frame.append(cylinder((8.32, -0.55, FLOOR_Z + 1.18), (8.32, 0.55, FLOOR_Z + 1.18), 0.012, n=8))
    p = Part("cabin_interior", "Cabin: executive 6-seat interior", "interior", group="Interior",
             material_note="Leather seats, wood veneer ledges",
             info={"cabin": "5.16 x 1.52 x 1.47 m", "floor width": "1.30 m", "seats": "6 executive (up to 9)"})
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


def build_structure(parts):
    from model.fuselage_parts import FIXED_WINDOWS
    rings = []
    wins = sorted(set(FIXED_WINDOWS[1] + FIXED_WINDOWS[-1]))
    cabin = [w + 0.40 for w in wins] + [wins[0] - 0.40]
    stations = [3.30, 3.62, 3.95] + sorted(cabin) + [9.85] + list(np.arange(10.35, 14.0, 0.50))
    for x in stations:
        rings.append(cut_openings(frame_ring(x, depth=0.065 if x < 10 else 0.045)))
    # stringers: kept above and below the window belt (as on the real airframe)
    strs = []
    for t in np.linspace(0, 1, 28, endpoint=False):
        z6 = float(F.section(np.array(6.0), np.array(t))[2])
        if 1.70 < z6 < 2.32:
            continue
        xs = np.linspace(3.05, 13.6, 90)
        P = F.section(xs, np.full_like(xs, t))
        c = np.stack([xs, np.zeros_like(xs), F.z_mw(xs)], 1)
        d = P - c
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        tube = sweep_tube(P - d * 0.015, 0.008, n=6, cap=False)
        tube.UV = np.stack([tube.V[:, 0], np.full(len(tube.V), t)], 1)
        strs.append(cut_openings(tube, margin=0.02))
    # pressure bulkheads
    bh = []
    for x in (3.00, 9.85):
        t = np.linspace(0, 1, 72, endpoint=False)
        sec = F.section(np.full_like(t, x + 0.01), t)
        ctr = np.array([x, 0, float(F.z_mw(x))])
        bh.append(planar_cap(ctr + (sec - ctr) * 0.97, (1, 0, 0)))
    # wing spars (front ~15 %, rear ~66 %) and ribs
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
        sp.append(grid_surface(np.array(rows)))
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
             info={"frames": f"{len(stations)} (representative)", "wing": "2-spar box, ribs @ 550 mm"})
    p.add(Mesh.merge(rings + bh), "zinc_chromate").add(Mesh.merge(strs), "zinc_chromate")
    p.add(Mesh.merge(sp + ribs), "interior_green")
    parts[p.id] = p


def build(parts):
    build_flightdeck(parts)
    build_cabin(parts)
    build_structure(parts)
    return parts
