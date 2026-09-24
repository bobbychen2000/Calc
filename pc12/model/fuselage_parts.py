"""
Fuselage components: skin panels (cowling, forward, centre, aft), glazing,
doors, seals and seams -- all cut from the one lofted outer mould line so every
panel, door and window lies exactly on the same surface.
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, grid_surface, grid_normals, trim, band, boundary_loops, solidify, cap_ring
from cad import sdf2d
from model import fuselage as F
from model.parts import Part
from model import cockpit_glazing as CG

BIG = 10.0
SPLIT_FWD = 4.36          # forward / centre fuselage joint (frame)
SPLIT_AFT = 9.85          # aft pressure bulkhead
N_AROUND = 144

# ---------------------------------------------------------------------------
# opening definitions (side projection x/z, rounded rectangles)
# ---------------------------------------------------------------------------
WIN_HX, WIN_HZ, WIN_R, WIN_CZ = 0.155, 0.215, 0.060, 2.010   # 'rectangular' PC-24-style (Pilatus)
FIXED_WINDOWS = {  # side -> stations
    -1: [5.52, 6.32, 7.12, 7.92],
    +1: [4.72, 6.32, 7.12, 7.92, 8.72],
}
AIRSTAIR = dict(side=-1, cx=4.715, cz=1.775, hx=0.305, hz=0.675, r=0.09)   # 0.61 x 1.35 m
CARGO = dict(side=-1, cx=8.925, cz=1.780, hx=0.675, hz=0.660, r=0.10)      # 1.35 x 1.32 m
EXIT = dict(side=+1, cx=5.520, cz=1.905, hx=0.255, hz=0.455, r=0.08)       # Type III 0.51 x 0.91 m
DOOR_WINDOWS = {"door_airstair": 4.715, "door_cargo": 8.72, "exit_hatch": 5.52}

# windshield panes (x, s) where s = signed arc length from crown (+ starboard)
WS_CORE = [(3.345, 0.034), (3.470, 0.470), (3.880, 0.455), (3.905, 0.034)]
WS_R = 0.03
# cockpit side window (x, z) core polygon
SW_CORE = [(3.700, 1.985), (4.255, 1.985), (4.255, 2.385), (3.980, 2.430)]
SW_R = 0.045


def rr(p, o):
    return sdf2d.rrect(p[0], p[1], o["cx"], o["cz"], o["hx"], o["hz"], o["r"])


def window_sdf(x, z, cx):
    return sdf2d.rrect(x, z, cx, WIN_CZ, WIN_HX, WIN_HZ, WIN_R)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_perim_x = np.linspace(0.9, 14.4, 200)
_perim_v = np.array([F.perimeter(x) for x in _perim_x])


def perim(x):
    return np.interp(x, _perim_x, _perim_v)


def signed_s(x, t):
    tt = np.where(t > 0.5, t - 1.0, t)
    return tt * perim(x)


def skin_grid(xs, ts):
    X, T = np.meshgrid(xs, ts, indexing="ij")
    P = F.section(X, T)
    UV = np.stack([X, T], -1)
    return P, UV


def skin_patch(x0, x1, t0, t1, d=0.010):
    xs = np.linspace(x0, x1, max(4, int(np.ceil((x1 - x0) / d)) + 1))
    pm = perim(0.5 * (x0 + x1))
    ts = np.linspace(t0, t1, max(4, int(np.ceil(abs(t1 - t0) * pm / d)) + 1))
    P, UV = skin_grid(xs, ts)
    return grid_surface(P, UV=UV)


def side_patch(o, side, pad=0.03, d=0.010):
    """Dense skin patch covering a side-projected rounded rect."""
    x0, x1 = o["cx"] - o["hx"] - pad, o["cx"] + o["hx"] + pad
    z0, z1 = o["cz"] - o["hz"] - pad, o["cz"] + o["hz"] + pad
    xm = 0.5 * (x0 + x1)
    ta = F.t_of(xm, z0, side)
    tb = F.t_of(xm, z1, side)
    ta, tb = min(ta, tb) - 0.004, max(ta, tb) + 0.004
    return skin_patch(x0, x1, ta, tb, d)


def xz_of(m):
    return m.V[:, 0], m.V[:, 2]


def side_mask(m, side):
    return (m.V[:, 1] * side) > 0.2


def rim(loop_V, loop_N, depth):
    """Inward extrusion of a boundary loop (door jamb / window reveal)."""
    a = loop_V
    b = np.roll(loop_V, -1, 0)
    ai = a - depth * loop_N
    bi = b - depth * np.roll(loop_N, -1, 0)
    n = len(a)
    V = np.vstack([a, b, bi, ai])
    i = np.arange(n)
    Fc = np.vstack([np.stack([i, i + n, i + 2 * n], 1), np.stack([i, i + 2 * n, i + 3 * n], 1)])
    m = Mesh(V, Fc)
    return m


# ---------------------------------------------------------------------------
# SDF fields over the main skin
# ---------------------------------------------------------------------------

def openings_field(m: Mesh):
    """Union of every opening cut into the fuselage skin (negative = hole)."""
    x, z = xz_of(m)
    y = m.V[:, 1]
    d = np.full(len(x), BIG)
    for side, stations in FIXED_WINDOWS.items():
        on = (y * side) > 0.2
        for cx in stations:
            d = np.where(on, np.minimum(d, window_sdf(x, z, cx)), d)
    for o in (AIRSTAIR, CARGO, EXIT):
        on = (y * o["side"]) > 0.2
        d = np.where(on, np.minimum(d, rr((x, z), o)), d)
    # cockpit side windows + two-piece windshield (constraint-defined, see cockpit_glazing)
    d = np.minimum(d, CG.sidewindow_sdf(x, y, z))
    s = signed_s(x, m.UV[:, 1])
    d = np.minimum(d, CG.windshield_sdf(x, s, z, y))
    # nose-gear bay in the belly
    from model.bays import nose_bay_sdf
    d = np.minimum(d, np.where(z < 1.1, nose_bay_sdf(x, y), BIG))
    return d


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------

def build_skin():
    xs = F.station_grid(0.030, 0.05, extra=[SPLIT_FWD, 3.215, 3.832, 4.268, 4.41, 5.02, 8.25, 9.6])
    ts = np.linspace(0, 1, N_AROUND, endpoint=False)
    P, UV = skin_grid(xs, ts)
    N = grid_normals(P, close_u=False, close_v=True)

    def sub(x0, x1):
        i0 = int(np.searchsorted(xs, x0 - 1e-9))
        i1 = int(np.searchsorted(xs, x1 + 1e-9))
        return grid_surface(P[i0:i1], close_v=True, N=N[i0:i1], UV=UV[i0:i1])

    return xs, sub


def build(parts_out: dict):
    xs, sub = build_skin()

    # ---- cowling (upper / lower halves split on the prop axis water line) ----
    cowl = sub(0.95, 3.00)
    split = cowl.V[:, 2] - (F.PROP_AXIS_Z + 0.02)
    up = trim(cowl, split, "positive")
    lo = trim(cowl, split, "negative")
    parts_out["cowl_upper"] = Part("cowl_upper", "Upper engine cowling", "cowling",
                                   explode=(0, 0, 0.9), group="Powerplant installation",
                                   material_note="Carbon/Nomex honeycomb, Cu mesh")
    parts_out["cowl_upper"].add(up, "paint_white")
    parts_out["cowl_lower"] = Part("cowl_lower", "Lower engine cowling", "cowling",
                                   explode=(0, 0, -0.8), group="Powerplant installation",
                                   material_note="Carbon/Nomex honeycomb")
    parts_out["cowl_lower"].add(lo, "paint_white")

    # ---- forward fuselage (cockpit) ----
    fwd = sub(3.00, SPLIT_FWD)
    fwd = trim(fwd, openings_field(fwd), "positive")
    parts_out["fus_fwd"] = Part("fus_fwd", "Forward fuselage & flight deck shell", "fuselage_fwd",
                                explode=(-0.9, 0, 0.25), group="Fuselage",
                                material_note="2024-T3 skins, frames 10-14")
    parts_out["fus_fwd"].add(fwd, "paint_white")

    # ---- centre fuselage (pressure cabin) ----
    cen = sub(SPLIT_FWD, SPLIT_AFT)
    cen = trim(cen, openings_field(cen), "positive")
    parts_out["fus_center"] = Part("fus_center", "Centre fuselage (pressure cabin)", "fuselage_center",
                                   explode=(0, 0, 0.35), group="Fuselage",
                                   material_note="2024-T3 skin, 5.8 psi max differential")
    parts_out["fus_center"].add(cen, "paint_white")

    # ---- aft fuselage / tail cone ----
    aft = sub(SPLIT_AFT, 14.36)
    end = F.section(np.full(N_AROUND, 14.36), np.linspace(0, 1, N_AROUND, endpoint=False))
    tip = cap_ring(end, (1, 0, 0))
    parts_out["fus_aft"] = Part("fus_aft", "Aft fuselage & tail cone", "fuselage_aft",
                                explode=(1.1, 0, 0.3), group="Fuselage",
                                material_note="Semi-monocoque, frames 29-38")
    parts_out["fus_aft"].add(aft, "paint_white").add(tip, "paint_white")

    build_glazing(parts_out)
    build_doors(parts_out)
    return parts_out


def build_glazing(parts_out):
    glass_parts = []
    seals = []
    # cabin windows (fixed)
    for side, stations in FIXED_WINDOWS.items():
        for cx in stations:
            o = dict(cx=cx, cz=WIN_CZ, hx=WIN_HX, hz=WIN_HZ, r=WIN_R)
            p = side_patch(o, side, pad=0.03, d=0.013)
            fn = lambda m, cx=cx: window_sdf(m.V[:, 0], m.V[:, 2], cx)
            glass_parts.append(trim(p, fn(p) - 0.010, "negative").offset(-0.006))
            seals.append(band(p, fn, -0.006, 0.010).offset(0.0015))
    # cockpit side windows
    sw_glass, sw_seal = [], []
    for side in (-1, 1):
        o = dict(cx=3.78, cz=2.235, hx=0.52, hz=0.28, r=0.0)
        p = side_patch(o, side, pad=0.02, d=0.014)
        fn = lambda m: CG.sidewindow_sdf(m.V[:, 0], m.V[:, 1], m.V[:, 2])
        sw_glass.append(trim(p, fn(p) - 0.010, "negative").offset(-0.005))
        sw_seal.append(band(p, fn, -0.006, 0.012).offset(0.0015))
    # windshield (two panes either side of the centre post)
    p = skin_patch(3.17, 3.90, -0.22, 0.22, d=0.012)
    fn = lambda m: CG.windshield_sdf(m.V[:, 0], signed_s(m.V[:, 0], m.UV[:, 1]), m.V[:, 2], m.V[:, 1])
    ws_glass = trim(p, fn(p) - 0.012, "negative").offset(-0.004)
    ws_seal = band(p, fn, -0.006, 0.014).offset(0.0015)

    g = Part("glazing_cabin", "Cabin windows (9 fixed, stretched acrylic)", "glazing",
             explode=(0, 0, 0), group="Glazing", qty=9,
             material_note="Two-ply laminated stretched acrylic")
    g.add(Mesh.merge(glass_parts), "glass").add(Mesh.merge(seals), "seal")
    parts_out[g.id] = g
    w = Part("glazing_flightdeck", "Windshield (2 heated panes) & side windows (no DV window, PRO)", "glazing",
             explode=(-0.3, 0, 0.35), group="Glazing", qty=4,
             material_note="Heated laminated glass windshield, acrylic side windows")
    w.add(ws_glass, "glass_windshield").add(Mesh.merge(sw_glass), "glass").add(
        Mesh.merge([ws_seal] + sw_seal), "seal")
    parts_out[w.id] = w


def build_door(o, pid, name, window_cx=None, hinge="bottom", open_angle=132.0, explode=(0, 0, 0),
               note=""):
    side = o["side"]
    p = side_patch(o, side, pad=0.03, d=0.022)
    x, z = xz_of(p)
    dd = rr((x, z), o)
    skin = trim(p, dd + 0.004, "negative")
    if window_cx is not None:
        wd = window_sdf(skin.V[:, 0], skin.V[:, 2], window_cx)
        skin = trim(skin, wd, "positive")
    slab_out, slab_in = solidify(skin, 0.045, separate=True)
    # hinge line along bottom (airstair) or top (cargo) edge, on the skin
    zh = o["cz"] - o["hz"] + 0.01 if hinge == "bottom" else o["cz"] + o["hz"] - 0.01
    yh = side * float(F.side_y(o["cx"], zh))
    origin = (o["cx"], yh, zh)
    ang = np.radians(open_angle) * (1 if hinge == "bottom" else -1) * (-side)
    part = Part(pid, name, "doors", pivot=dict(origin=origin, axis=(1, 0, 0), kind="door",
                                               open=float(ang)),
                explode=explode, group="Doors", material_note=note)
    part.add(slab_out, "paint_white").add(slab_in, "lining")
    extra = []
    if window_cx is not None:
        wo = dict(cx=window_cx, cz=WIN_CZ, hx=WIN_HX, hz=WIN_HZ, r=WIN_R)
        wp = side_patch(wo, side, pad=0.03, d=0.013)
        fn = lambda m: window_sdf(m.V[:, 0], m.V[:, 2], window_cx)
        part.add(trim(wp, fn(wp) - 0.010, "negative").offset(-0.006), "glass")
        part.add(band(wp, fn, -0.006, 0.010).offset(0.0015), "seal")
    return part


def build_doors(parts_out):
    d1 = build_door(AIRSTAIR, "door_airstair", "Airstair passenger door (0.61 x 1.35 m)",
                    window_cx=DOOR_WINDOWS["door_airstair"], hinge="bottom", open_angle=128,
                    explode=(0, -0.9, 0), note="Downward-opening, integral steps")
    d2 = build_door(CARGO, "door_cargo", "Cargo door (1.35 x 1.32 m)",
                    window_cx=DOOR_WINDOWS["door_cargo"], hinge="top", open_angle=100,
                    explode=(0, -1.0, 0.2), note="Upward-opening, gas-strut assisted")
    d3 = build_door(EXIT, "exit_hatch", "Type III overwing emergency exit",
                    window_cx=DOOR_WINDOWS["exit_hatch"], hinge="bottom", open_angle=0,
                    explode=(0, 0.8, 0.1), note="Plug-type, removable inward")
    d3.pivot = None
    for d in (d1, d2, d3):
        parts_out[d.id] = d
    # seams + jambs (fixed to the fuselage)
    seams, jambs = [], []
    for o in (AIRSTAIR, CARGO, EXIT):
        p = side_patch(o, o["side"], pad=0.03, d=0.012)
        fn = lambda m, o=o: rr((m.V[:, 0], m.V[:, 2]), o)
        seams.append(band(p, fn, 0.0, 0.007).offset(0.0008))
        ring = band(p, fn, 0.0, 0.03)
        loops = boundary_loops(ring)
        # pick the loop whose points lie closest to the opening outline
        best = None
        for loop in loops:
            lv = ring.V[loop]
            sd = np.abs(rr((lv[:, 0], lv[:, 2]), o)).mean()
            if best is None or sd < best[0]:
                best = (sd, loop)
        if best is not None:
            loop = best[1]
            jm = rim(ring.V[loop], ring.N[loop], 0.055)
            jambs.append(jm)
    s = Part("door_frames", "Door surrounds, seals & jambs", "doors", group="Doors",
             material_note="Machined door frames")
    s.add(Mesh.merge(seams), "seam").add(Mesh.merge(jambs), "jamb")
    parts_out[s.id] = s
