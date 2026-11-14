"""
SF50 wing: tapered low wing, NACA 23015 -> 23012, single-slotted flaps, ailerons with the left trim tab and the right
servo tab, de-ice boots, wing-tip fairings with nav / strobe / landing lights, main-gear wells, pitot probes, root
vortex generators, aileron fences, static wicks.
"""
from __future__ import annotations
import numpy as np

from sf50_kernel import (Mesh, trim, band, planar_cap, cap_ring, grid_surface, superellipsoid, box, cylinder,
                         sweep_tube, Section, skin, strip, curve_patch, closed_body, bezier, cos_pts, naca230xx,
                         Part, rotation_about, rotation_matrix, boundary_loops)
import sf50_geom as G

ROOT_AF, TIP_AF = naca230xx(0.15), naca230xx(0.12)
GAP = 0.010


def airfoil_at(y):
    w = np.clip((abs(y) - 0.85) / (G.Y_TIPCAP - 0.85), 0, 1)
    return ROOT_AF.blend(TIP_AF, w)


def section_at(y):
    """Right-wing section at butt line y >= 0."""
    c = float(G.wing_chord(y) + G.te_fillet(y))
    tw = G.INC_ROOT + (G.INC_TIP - G.INC_ROOT) * np.clip(y, 0, G.Y_TIPCAP) / G.Y_TIPCAP
    return Section(le=np.array([float(G.wing_x_le(y)), y, float(G.wing_z_le(y))]), chord=c,
                   e_c=np.array([1.0, 0, 0]), e_t=np.array([0, 0, 1.0]), twist=float(tw), airfoil=airfoil_at(y),
                   pivot_frac=0.0)


def span_stations(a, b, step=0.2):
    n = max(2, int(np.ceil((b - a) / step)) + 1)
    return np.linspace(a, b, n)


# ------------------------------------------------------------------------------------------------ control-surface sections
def flap_cove(sec, n=14):
    af = sec.airfoil
    xlo, xlip = G.FLAP_X_LO, G.FLAP_X_LIP
    lo = np.array([xlo, float(af.lower(xlo))])
    zu = float(af.upper(xlip))
    lip_b = np.array([xlip, zu - 0.0050])
    c = bezier(lo, lo + [-0.040, 0.006], [xlip - 0.10, zu - 0.026], lip_b, n=n)
    return np.vstack([c, [[xlip, zu]]])


def flap_loop(sec, n=18):
    af = sec.airfoil
    xlo, xlip = G.FLAP_X_LO, G.FLAP_X_LIP
    x0u = xlip - 0.010
    xu = cos_pts(n, 0.0, 1.0) * (1 - x0u) + x0u
    zu = af.upper(xu) - 0.0065 * np.clip((x0u + 0.022 - xu) / 0.022, 0, 1)
    x0l = xlo + 0.012
    xl = (cos_pts(n, 0.0, 1.0) * (1 - x0l) + x0l)[::-1]
    zl = af.lower(xl)
    nose_top = np.array([xu[0], zu[0]])
    nose_bot = np.array([x0l, float(af.lower(x0l))])
    nose = bezier(nose_bot, nose_bot + [-0.032, 0.008], [x0u - 0.075, nose_top[1] - 0.026], nose_top, n=12)
    upper = np.stack([xu, zu], 1)
    lower = np.stack([xl, zl], 1)
    return np.vstack([upper[:-1], [[1.0, float(af.upper(1.0))]], lower[1:-1], nose[:-1]])


def hinge_arc_ends(af, xh, R):
    zh = float(af.camber(xh))

    def f(th, surf):
        return zh + R * np.sin(th) - float(surf(xh + R * np.cos(th)))
    a, b = np.pi / 2, np.pi
    for _ in range(50):
        m = 0.5 * (a + b)
        a, b = (m, b) if f(m, af.upper) > 0 else (a, m)
    tu = 0.5 * (a + b)
    a, b = np.pi, 1.5 * np.pi
    for _ in range(50):
        m = 0.5 * (a + b)
        a, b = (a, m) if f(m, af.lower) < 0 else (m, b)
    return zh, tu, 0.5 * (a + b)


def plain_cove(sec, xh, gap=0.010, n=16):
    af = sec.airfoil
    R = 0.5 * float(af.upper(xh) - af.lower(xh)) + gap
    zh, tu, tl = hinge_arc_ends(af, xh, R)
    th = np.linspace(tu, tl, n)
    return np.stack([xh + R * np.cos(th), zh + R * np.sin(th)], 1), (tu, tl, R)


def plain_surface_loop(sec, xh, n=16, x_end=1.0):
    af = sec.airfoil
    r = 0.5 * float(af.upper(xh) - af.lower(xh))
    zh = float(af.camber(xh))
    xu = cos_pts(n, 0, 1) * (x_end - xh) + xh
    upper = np.stack([xu, af.upper(xu)], 1)
    lower = np.stack([xu, af.lower(xu)], 1)[::-1]
    th = np.linspace(1.5 * np.pi, 0.5 * np.pi, 13)[1:-1]
    nose = np.stack([xh + r * np.cos(th), zh + r * np.sin(th)], 1)
    return np.vstack([upper, lower, nose])


def tab_loop(sec, x0, n=10):
    af = sec.airfoil
    r = 0.5 * float(af.upper(x0) - af.lower(x0))
    zh = float(af.camber(x0))
    xu = cos_pts(n, 0, 1) * (1 - x0 - r) + x0 + r
    upper = np.stack([xu, af.upper(xu)], 1)
    lower = np.stack([xu[::-1], af.lower(xu[::-1])], 1)
    th = np.linspace(1.5 * np.pi, 0.5 * np.pi, 9)[1:-1]
    nose = np.stack([x0 + r + r * np.cos(th), zh + r * np.sin(th)], 1)
    return np.vstack([upper, lower, nose])


def x_end_of_plain(sec, xh, gap=0.010):
    _, (tu, tl, R) = plain_cove(sec, xh, gap)
    return xh + R * np.cos(tu), xh + R * np.cos(tl)


def cut_rib(sec, cove2d, x_lo, x_up):
    af = sec.airfoil
    xs_u = cos_pts(14, 0, 1) * (1 - x_up) + x_up
    xs_l = (cos_pts(14, 0, 1) * (1 - x_lo) + x_lo)[::-1]
    poly = np.vstack([cove2d[:-1] if len(cove2d) > 2 else cove2d, np.stack([xs_u, af.upper(xs_u)], 1),
                      np.stack([xs_l, af.lower(xs_l)], 1)[:-1]])
    return sec.point(poly[:, 0], poly[:, 1])


def segmented_surface(section_fn, s0, s1, xh, tab, step=0.15, gap=0.008):
    t0, t1, xt = tab
    bodies = []
    if t0 - s0 > 0.02:
        bodies.append(closed_body(section_fn, span_stations(s0, t0, step), lambda s: plain_surface_loop(s, xh)))
    bodies.append(closed_body(section_fn, span_stations(t0, t1, step), lambda s: plain_surface_loop(s, xh, x_end=xt)))
    if s1 - t1 > 0.02:
        bodies.append(closed_body(section_fn, span_stations(t1, s1, step), lambda s: plain_surface_loop(s, xh)))
    tb = closed_body(section_fn, span_stations(t0 + gap, t1 - gap, step), lambda s: tab_loop(s, xt + 0.004))
    a, b = section_fn(t0), section_fn(t1)
    ha = a.point(np.array(xt + 0.004), np.array(float(a.airfoil.camber(xt))))
    hb = b.point(np.array(xt + 0.004), np.array(float(b.airfoil.camber(xt))))
    return Mesh.merge(bodies), tb, (ha, hb)


# ------------------------------------------------------------------------------------------------ wells / fields
MAIN_T = None   # set in sf50_gear (trunnion); wells defined here from the retracted geometry
# retracted tyre centre in plan (x, y) [inf: retraction about the trunnion, sf50_gear]; the trunnion rose with the wing in
# fix round 2 (G.WING_DZ), so the longer leg stows the tyre that much further inboard
WELL_C = (G.X_MAIN_AXLE, 1.096 - G.WING_DZ)
WELL_R = 0.250
SLOT = dict(x0=4.900, x1=5.335, y0=1.215 - G.WING_DZ, y1=1.690)


def main_opening_sdf(x, y):
    d1 = np.hypot(x - WELL_C[0], np.abs(y) - WELL_C[1]) - WELL_R
    cx, cy = 0.5 * (SLOT["x0"] + SLOT["x1"]), 0.5 * (SLOT["y0"] + SLOT["y1"])
    hx, hy = 0.5 * (SLOT["x1"] - SLOT["x0"]), 0.5 * (SLOT["y1"] - SLOT["y0"])
    qx, qy = np.abs(x - cx) - hx, np.abs(np.abs(y) - cy) - hy
    d2 = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)
    return np.minimum(d1, d2)


# ------------------------------------------------------------------------------------------------ wing tip
# Upswept, aft-raked tip (fix round 1 of Phase 3a; before: a flat rounded cap with three box lamps on it). Evidence:
# AFM P/N 31452-001 Fig 1-1 plan view (rounded leading-edge corner sweeping aft, the outermost point near the trailing
# edge) and front view (the tip turned up at its outer end), Fig 8-1 isometric (upturned tips), Cirrus product-page photos
# (an upturned, aft-raked tip fin above the trailing part of the tip, the lamps in a clear lens at the tip leading edge).
# Shape, height and angles below are read off those views by eye [inf]; the outermost point stays at the 38.7 ft span.
# Fix round 2: the fin height is fitted to the AFM Fig 1-1 FRONT view (orthographic; the reading is local reference data,
# refs/cache/local/models/afm_sf50_meas.json) - the fix-round-1 fin (a broad plate with a square top) was about twice as
# high. The Cirrus photos show a slender spike raked aft; perspective photos give no height, so the drawing sets the height
# and the photos the plan shape: the fin narrows to a point (le_top > 1: its leading edge rakes aft past the rib trailing
# edge) [inf: photos]. Conflict recorded in SF50_FACTS.md (S5 / S11).
TIP = dict(
    reach=0.30,        # horizontal (dihedral-plane) run of the tip body before the upturn, m [inf] (solved: see _tip_solve)
    bend=0.060,        # radius of the upturn, m [inf]
    cant=np.radians(70.0),   # fin angle from the wing plane (20 deg outward of vertical) [inf: photos]
    rise=0.130,        # fin top above the tip chord plane, m: the top lands 0.058 m above the extrapolated upper-surface
                       # line [inf: fitted to the AFM Fig 1-1 front view; tools/models/test_models.mjs checks it when the
                       # local reference file is present]
    le_body=0.42,      # leading edge raked aft by this share of the rib chord over the body (rounded corner) [inf: AFM plan]
    le_top=1.10,       # ... and by this share at the fin top: past the rib trailing edge, so the fin ends in a point [inf: photos]
    te_top=0.16,       # trailing edge of the fin top behind the rib trailing edge, m (aft rake) [inf: photos]
    t_body=0.085,      # absolute thickness at the end of the body, m [inf]
    t_root=0.045, t_top=0.008,   # fin thickness at its root / top, m [inf]
)


def _tip_path(reach, n_body=14, n_bend=10, n_fin=12):
    """Arc-length stations along the tip span path (dihedral-plane frame): [(a, theta, part)]."""
    T = TIP
    a_bend = T["bend"] * T["cant"]
    fin_len = max((T["rise"] - T["bend"] * (1 - np.cos(T["cant"]))) / np.sin(T["cant"]), 0.02)
    out = []
    for a in np.sin(np.linspace(0, np.pi / 2, n_body)) * reach:
        out.append((a, 0.0, "body"))
    for k in range(1, n_bend + 1):
        th = T["cant"] * k / n_bend
        out.append((reach + T["bend"] * th, th, "bend"))
    for k in range(1, n_fin + 1):
        out.append((reach + a_bend + fin_len * k / n_fin, T["cant"], "fin"))
    return out, reach + a_bend + fin_len


def _tip_sections(reach):
    """Sections of the tip (Section objects in the right-wing frame) and their arc-length parameter."""
    T = TIP
    s0 = section_at(G.Y_TIPCAP)
    c0, tw = s0.chord, s0.twist
    path, a_end = _tip_path(reach)
    # path integration in the (y, z) plane, starting at the rib LE, continuing the dihedral line, then turning up
    y, z = s0.le[1], s0.le[2]
    pts = []
    prev_a, prev_th = 0.0, 0.0
    for a, th, part in path:
        da = a - prev_a
        phi = G.DIHEDRAL + 0.5 * (th + prev_th)
        y += da * np.cos(phi)
        z += da * np.sin(phi)
        pts.append((a, th, part, y, z))
        prev_a, prev_th = a, th
    a_fin0 = reach + T["bend"] * T["cant"] * 0.5
    secs = []
    for a, th, part, y, z in pts:
        if a <= reach:   # body: the leading edge rounds aft (elliptic quadrant), thickness thins toward the upturn
            u = a / reach if reach > 0 else 0.0
            k_le = T["le_body"] * (1 - np.sqrt(max(1 - u * u, 0.0)))
            d_te = 0.0
            thick = 0.12 * c0 + (T["t_body"] - 0.12 * c0) * u ** 1.6
        else:            # bend + fin: leading edge keeps raking aft (concave), trailing edge runs aft to the pointed top
            v = np.clip((a - reach) / (a_end - reach), 0, 1)
            k_le = T["le_body"] + (T["le_top"] - T["le_body"]) * (1 - (1 - v) ** 1.5)
            d_te = T["te_top"] * v ** 1.3
            vb = np.clip((a - reach) / max(a_fin0 - reach, 1e-6), 0, 1)
            t_fin = T["t_root"] + (T["t_top"] - T["t_root"]) * np.clip((a - a_fin0) / max(a_end - a_fin0, 1e-6), 0, 1)
            thick = T["t_body"] + (t_fin - T["t_body"]) * vb if a < a_fin0 else t_fin
        x_le = s0.le[0] + k_le * c0
        chord = c0 * (1 - k_le) + d_te
        e_c = np.array([1.0, 0, 0])
        e_t = np.array([0.0, -np.sin(th), np.cos(th)])
        # keep the leading edge on the (twisted) chord line of the rib so the tip does not kink at the joint
        R = rotation_matrix(np.cross(e_c, e_t), -tw)
        le = np.array([s0.le[0], y, z]) + (k_le * c0) * (R @ e_c)
        t_rel = float(np.clip(thick / max(chord, 1e-3), 0.03, 0.20))
        af = TIP_AF if a == 0 else naca230xx(t_rel)
        secs.append((a, part, Section(le=le, chord=float(chord), e_c=e_c, e_t=e_t, twist=float(tw), airfoil=af, pivot_frac=0.0)))
    return secs


def _tip_rows(secs, n):
    xl = cos_pts(n, 0, 1)[::-1]
    xu = cos_pts(n, 0, 1)[1:]
    rows, uv = [], []
    for a, part, sec in secs:
        rows.append(np.vstack([sec.lower(xl), sec.upper(xu)]))
        uv.append(np.stack([np.full(len(xl) + len(xu), a), np.concatenate([-xl, xu])], 1))
    return np.array(rows), np.array(uv)


def _tip_solve(n=72):
    """Body reach so that the outermost point of the tip is at SPAN/2 (38.7 ft overall) [obs: span]."""
    lo, hi = 0.05, 0.45
    target = G.SPAN / 2 - 0.0015
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        P, _ = _tip_rows(_tip_sections(mid), 24)
        if P[..., 1].max() > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# lens (clear, flush) at the tip leading edge: chord share on each surface and the body stations it spans [inf]
LENS_A = (0.035, 0.80)    # share of the body reach
LENS_XC = 0.075           # chord share from the leading edge, both surfaces
STROBE = dict(xc=(0.62, 0.86), a=(0.02, 0.85))   # aft-facing white strobe lens on the outboard face of the upturn [inf]


def tip_extension(n=72):
    """-> dict(skin, cap, lens, lamp_white, lamp_nav, strobe_glass, strobe_lamp, rims, anchors{nav, land, strobe}, reach)."""
    reach = _tip_solve(n)
    secs = _tip_sections(reach)
    P, UV = _tip_rows(secs, n)
    m = grid_surface(P, UV=UV)
    # outward normals: away from each row's centroid
    cen = P.mean(1)
    rad = (P - cen[:, None, :]).reshape(-1, 3)
    if np.mean(np.sum(rad * m.N[:len(rad)], 1)) < 0:
        m = m.flipped()
    a_end = secs[-1][0]
    # lens region: body stations LENS_A x reach, |signed chord| < LENS_XC (UV = (a, signed chord))
    a0, a1 = LENS_A[0] * reach, LENS_A[1] * reach

    def lens_field(mm):
        a, xc = mm.UV[:, 0], mm.UV[:, 1]
        return np.maximum(np.maximum(a0 - a, a - a1), np.abs(xc) - LENS_XC) * 1.0

    # strobe region: on the fin's outboard face (the LOWER surface of the banked sections) in the bend
    i_b0 = [i for i, (a, part, s) in enumerate(secs) if part == "bend"]
    ab0, ab1 = secs[i_b0[0]][0], secs[min(i_b0[-1] + 3, len(secs) - 1)][0]

    def strobe_field(mm):
        a, xc = mm.UV[:, 0], mm.UV[:, 1]
        fa = np.maximum(ab0 + STROBE["a"][0] * (ab1 - ab0) - a, a - (ab0 + STROBE["a"][1] * (ab1 - ab0)))
        fx = np.maximum(-xc - STROBE["xc"][1], STROBE["xc"][0] + xc)   # lower surface: xc negative
        return np.maximum(fa, fx)

    skin_m = trim(m, lens_field(m), "positive")
    skin_m = trim(skin_m, strobe_field(skin_m), "positive")
    lens = trim(m, lens_field(m), "negative")
    strobe = trim(m, strobe_field(m), "negative")
    rims = []
    for loop in boundary_loops(skin_m):
        if len(loop) < 8:
            continue
        V = skin_m.V[loop]
        # only the loops of the two openings (not the outer boundary of the skin at the rib / the fin top)
        a_l, x_l = skin_m.UV[loop, 0], skin_m.UV[loop, 1]
        if a_l.min() < 1e-6 or a_l.max() > a_end - 1e-6 or np.abs(x_l).max() > 0.95:
            continue
        N = skin_m.N[loop]
        b = np.roll(V, -1, 0)
        d = 0.014
        VV = np.vstack([V, b, b - d * np.roll(N, -1, 0), V - d * N])
        k = len(V)
        i = np.arange(k)
        rims.append(Mesh(VV, np.vstack([np.stack([i, i + k, i + 2 * k], 1), np.stack([i, i + 2 * k, i + 3 * k], 1)])))
    # lamps behind the lens (reflector + LED clusters) 14 mm inside the skin: inboard 60 % landing lights (white),
    # outboard 40 % the position light (red / green by side) [inf: layout]
    back = lens.offset(-0.014)
    split_a = a0 + 0.60 * (a1 - a0)
    lamp_white = trim(back, split_a - back.UV[:, 0], "positive")
    lamp_nav = trim(back, back.UV[:, 0] - split_a, "positive")
    strobe_lamp = strobe.offset(-0.010)
    # top cap of the fin
    cap = cap_ring(P[-1], secs[-1][2].e_c * 0 + np.cross(secs[-1][2].e_c, secs[-1][2].e_t) * -1)

    def centre(mm, outward=0.0):
        c = mm.V.mean(0)
        nrm = mm.N.mean(0)
        nrm = nrm / max(np.linalg.norm(nrm), 1e-9)
        return c + outward * nrm

    anchors = dict(nav=centre(lamp_nav, 0.016), land=centre(lamp_white, 0.016), strobe=centre(strobe_lamp, 0.012))
    return dict(skin=skin_m, cap=cap, lens=lens.offset(0.0004), lamp_white=lamp_white, lamp_nav=lamp_nav,
                strobe_glass=strobe.offset(0.0004), strobe_lamp=strobe_lamp, rims=Mesh.merge(rims), anchors=anchors,
                reach=reach, rows=P)


def lens_bump(c, n_dir, r, h, e=(0.35, 0.35)):
    """Small lens / lamp body: a flattened superellipsoid along n_dir."""
    n_dir = np.asarray(n_dir, float) / np.linalg.norm(n_dir)
    a = np.cross(n_dir, [0, 0, 1.0]) if abs(n_dir[2]) < 0.9 else np.cross(n_dir, [1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(n_dir, a)
    R = np.stack([n_dir, a, b], 1)
    return superellipsoid(c, (h, r, r), e=e, nu=12, nv=20, R=R)


# ------------------------------------------------------------------------------------------------ build
def build_right(n=72):
    out = {"skin": [], "boot": [], "ribs": [], "well": []}

    def add_skin(m):
        uvx = m.UV[:, 1]
        y = m.UV[:, 0]
        f_boot = np.maximum(np.maximum(np.where(uvx >= 0, uvx - 0.085, -uvx - 0.05), G.BOOT_Y[0] - y), y - G.BOOT_Y[1])
        boot = trim(m, f_boot, "negative")
        rest = trim(m, f_boot, "positive")
        fw = np.where(rest.UV[:, 1] < 0, main_opening_sdf(rest.V[:, 0], rest.V[:, 1]), 1.0)
        if (fw < 0).any():
            rest = trim(rest, fw, "positive")
        out["skin"].append(rest)
        if boot.nf:
            out["boot"].append(boot.offset(0.0012))

    ys = np.r_[np.linspace(0.0, 0.70, 5), span_stations(0.75, G.Y_FLAP[0], 0.04)]
    add_skin(skin(section_at, ys, n=n))
    ys = span_stations(G.Y_FLAP[0], G.Y_FLAP[1], 0.12)
    add_skin(skin(section_at, ys, x_lo_end=G.FLAP_X_LO, x_up_end=G.FLAP_X_LIP, n=n))
    out["skin"].append(curve_patch(section_at, ys, flap_cove, outward_hint=lambda s: s.e_c))
    ys = span_stations(G.Y_FLAP[1], G.Y_AIL[0], 0.04)
    add_skin(skin(section_at, ys, n=n))
    ys = span_stations(G.Y_AIL[0], G.Y_AIL[1], 0.12)
    xl_end, xu_end = x_end_of_plain(section_at(0.5 * sum(G.Y_AIL)), G.AIL_XH)
    add_skin(skin(section_at, ys, x_lo_end=xl_end, x_up_end=xu_end, n=n))
    out["skin"].append(curve_patch(section_at, ys, lambda s: plain_cove(s, G.AIL_XH)[0], outward_hint=lambda s: s.e_c))
    ys = span_stations(G.Y_AIL[1], G.Y_TIPCAP, 0.05)
    add_skin(skin(section_at, ys, n=n))
    for y, sgn in ((G.Y_FLAP[0], +1), (G.Y_FLAP[1], -1)):
        sec = section_at(y)
        out["ribs"].append(planar_cap(cut_rib(sec, flap_cove(sec), G.FLAP_X_LO, G.FLAP_X_LIP), (0, sgn, 0)))
    for y, sgn in ((G.Y_AIL[0], +1), (G.Y_AIL[1], -1)):
        sec = section_at(y)
        cove, _ = plain_cove(sec, G.AIL_XH)
        xl_e, xu_e = x_end_of_plain(sec, G.AIL_XH)
        out["ribs"].append(planar_cap(cut_rib(sec, cove[::-1], xl_e, xu_e), (0, sgn, 0)))
    ys = span_stations(G.Y_FLAP[0] + GAP, G.Y_FLAP[1] - GAP, 0.12)
    out["flap"] = closed_body(section_at, ys, flap_loop)
    return out


def wing_surface_z(x, y, upper=False):
    """Approximate wing surface height at plan point (x, |y|) (no twist correction beyond the section)."""
    sec = section_at(abs(y))
    u = np.clip((x - sec.le[0]) / sec.chord, 0, 1)
    p = sec.upper(np.array(u)) if upper else sec.lower(np.array(u))
    return float(p[2])


def build(parts):
    import sf50_fuselage as FU
    R = build_right()
    ribs = Mesh.merge(R["ribs"])
    TX = tip_extension()
    # main-gear well liner: a shallow dish above the lower-skin opening (right side)
    well = []
    xs = np.linspace(SLOT["x0"] - 0.02, WELL_C[0] + WELL_R + 0.02, 24)
    ysl = np.linspace(WELL_C[1] - WELL_R - 0.02, SLOT["y1"] + 0.02, 24)
    X, Y = np.meshgrid(xs, ysl, indexing="ij")
    Z = np.zeros_like(X)
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            zl = wing_surface_z(X[i, j], Y[i, j])
            zu = wing_surface_z(X[i, j], Y[i, j], upper=True)
            Z[i, j] = zl + 0.80 * (zu - zl)
    dish = grid_surface(np.stack([X, Y, Z], -1))
    dish = trim(dish, main_opening_sdf(dish.V[:, 0], dish.V[:, 1]) - 0.02, "negative")
    well.append(dish)

    for side, sgn in (("R", 1), ("L", -1)):
        mir = (lambda m: m) if sgn > 0 else (lambda m: m.mirrored_y())
        wing_skin = Mesh.merge(R["skin"] + [ribs])
        # remove what is inside the fuselage
        f = lambda m: G.inside_fuselage(m.V)
        wing_skin = trim(wing_skin, f(wing_skin), "positive")
        boot = Mesh.merge(R["boot"])
        boot = trim(boot, f(boot), "positive")
        p = Part(f"wing_{side}", f"{'Right' if sgn > 0 else 'Left'} wing", "wing", group="Wing",
                 material_note="Carbon spar, carbon sandwich skins, integral fuel tank (296 US gal usable total, TCDS)",
                 info={"airfoil": "NACA 23015 root -> NACA 23012 tip [inf: SF50 section unpublished]",
                       "root chord (BL 0)": f"{G.C0:.3f} m", "tip chord (span/2)": f"{G.wing_chord(G.WING_SEMI_REF):.3f} m",
                       "LE sweep": f"{np.degrees(G.LE_SWEEP):.2f} deg [inf]", "dihedral": f"{np.degrees(G.DIHEDRAL):.1f} deg [inf]",
                       "area": f"{G.WING_AREA} m2 (TCDS)"})
        p.add(mir(wing_skin), "paint_white").add(mir(boot), "deice_boot").add(mir(Mesh.merge(well)), "gear_bay")
        p.add(mir(Mesh.merge([TX["skin"], TX["cap"]])), "paint_white").add(mir(TX["rims"]), "seal")
        p.info["tip"] = ("upswept, aft-raked tip: body reach %.3f m, upturn %.0f deg from the wing plane, top %.2f m above the "
                         "tip chord plane, top trailing edge %.2f m aft [inf: AFM Fig 1-1 plan / front, Fig 8-1, Cirrus photos]; "
                         "outermost point at the 38.7 ft span [obs]" % (TX["reach"], np.degrees(TIP["cant"]), TIP["rise"], TIP["te_top"]))
        parts[p.id] = p
        build_controls(parts, R, side, sgn, mir)
        build_tip_lights(parts, p, TX, side, sgn, mir)
        build_wing_details(parts, p, side, sgn, mir)


def hinge_line(y0, y1, xc, zc_fn=None):
    a, b = section_at(y0), section_at(y1)
    ha = a.point(np.array(xc), np.array(float(a.airfoil.camber(xc)) if zc_fn is None else zc_fn(a)))
    hb = b.point(np.array(xc), np.array(float(b.airfoil.camber(xc)) if zc_fn is None else zc_fn(b)))
    return ha, hb


def build_controls(parts, R, side, sgn, mir):
    m = lambda v: np.asarray(v) * [1, sgn, 1]
    # single-slotted flap on a drop hinge below the lower surface [inf: hinge position]; TCDS: 15 deg (50 %), 39 deg (100 %)
    ha, hb = hinge_line(G.Y_FLAP[0], G.Y_FLAP[1], 0.80, lambda s: float(s.airfoil.lower(0.80)) - 0.065)
    ha, hb = m(ha), m(hb)
    axis = (hb - ha) / np.linalg.norm(hb - ha) * sgn
    f = Part(f"flap_{side}", f"{'Right' if sgn > 0 else 'Left'} flap (single-slotted)", "controls_wing",
             pivot=dict(origin=ha.tolist(), axis=axis.tolist(), kind="flap", travel=[0.0, 0.0, 0.0], max=39.0,
                        settings=[0, 15, 39]),
             group="Flight controls", material_note="Aluminium (Wikipedia: 'primary flight control surfaces and wing flaps are aluminum')",
             info={"deflection": "UP 0, 50 % 15.0 deg, 100 % 39.0 deg (FAA TCDS A00018CH)", "span": f"BL {G.Y_FLAP[0]}-{G.Y_FLAP[1]} [inf]"})
    f.add(mir(R["flap"]), "paint_white")
    # flap hinge fairings (two) under the wing [inf]
    fair = []
    for yy in (G.Y_FLAP[0] + 0.35, G.Y_FLAP[1] - 0.25):
        sec = section_at(yy)
        p0 = sec.point(np.array(0.62), np.array(float(sec.airfoil.lower(0.62))))
        p1 = sec.point(np.array(0.92), np.array(float(sec.airfoil.lower(0.92))))
        fair.append(superellipsoid(0.5 * (p0 + p1) + [0, 0, -0.045], (0.5 * np.linalg.norm(p1 - p0), 0.035, 0.05),
                                   e=(0.6, 0.6), nu=12, nv=16))
    fx = Part(f"flap_fairings_{side}", f"{'Right' if sgn > 0 else 'Left'} flap hinge fairings", "controls_wing",
              group="Wing", material_note="[inf]")
    fx.add(mir(Mesh.merge(fair)), "paint_white")
    parts[fx.id] = fx
    parts[f.id] = f
    # aileron + tab: left = roll trim tab (TCDS 'LH Aileron Trim' +-10 deg, AFM 'LH Aileron, Roll Trim Tab'),
    # right = roll servo tab (AFM 'RH Aileron, Roll Servo Tab')
    sec_fn = section_at
    body, tabm, (ta, tb) = segmented_surface(sec_fn, G.Y_AIL[0] + GAP, G.Y_AIL[1] - GAP, G.AIL_XH,
                                             (G.Y_AIL[0] + 0.10, G.Y_AIL[0] + 0.62, 0.90), step=0.12)
    ha, hb = hinge_line(G.Y_AIL[0], G.Y_AIL[1], G.AIL_XH)
    ha, hb = m(ha), m(hb)
    axis = (hb - ha) / np.linalg.norm(hb - ha) * sgn
    ai = Part(f"aileron_{side}", f"{'Right' if sgn > 0 else 'Left'} aileron", "controls_wing",
              pivot=dict(origin=ha.tolist(), axis=axis.tolist(), kind="aileron", range=[-15.0, 11.5], sign=sgn),
              group="Flight controls", material_note="Aluminium, sealed gap",
              info={"deflection": "UP 15.0, DOWN 11.5 deg (FAA TCDS A00018CH)", "span": f"BL {G.Y_AIL[0]}-{G.Y_AIL[1]} [inf]"})
    ai.add(mir(body), "paint_white")
    parts[ai.id] = ai
    ta, tb = m(ta), m(tb)
    tax = (tb - ta) / np.linalg.norm(tb - ta) * sgn
    if sgn < 0:
        tp = Part(f"ail_tab_{side}", "Left aileron roll trim tab", "controls_wing", parent=ai.id,
                  pivot=dict(origin=ta.tolist(), axis=tax.tolist(), kind="tab", gearing=0.0, range=[-10.0, 10.0]),
                  group="Flight controls", material_note="Electric roll trim, +-10 deg (TCDS)")
    else:
        tp = Part(f"ail_tab_{side}", "Right aileron roll servo tab", "controls_wing", parent=ai.id,
                  pivot=dict(origin=ta.tolist(), axis=tax.tolist(), kind="tab", gearing=-0.5, range=[-12.0, 12.0]),
                  group="Flight controls", material_note="Servo tab (AFM walk-around) [inf: gearing]")
    tp.add(mir(tabm), "paint_white")
    parts[tp.id] = tp
    # static wicks on the aileron trailing edge (AFM 'Static Wicks')
    wicks = []
    for yy in (G.Y_AIL[0] + 0.85, G.Y_AIL[1] - 0.15):
        sec = section_at(yy)
        te = sec.point(np.array(0.995), np.array(float(sec.airfoil.camber(0.995))))
        wicks.append(cylinder(te, te + [0.11, 0, -0.004], 0.0035, n=6))
    ai.add(mir(Mesh.merge(wicks)), "black")


def build_tip_lights(parts, wing_part, TX, side, sgn, mir):
    """Flush lenses in the tip (fix round 1: they were three box lamps standing on the cap): a clear lens over the tip
    leading edge with the landing lights (inboard, white) and the position light (outboard, red / green) behind it, and a
    clear strobe lens on the outboard face of the upturn. Anchors -> wing part info 'light_anchors' and light:<kind> nodes."""
    m = lambda v: np.asarray(v, float) * [1, sgn, 1]
    col = "light_red" if sgn < 0 else "light_green"
    wing_part.add(mir(TX["lens"]), "lens").add(mir(TX["strobe_glass"]), "lens")
    wing_part.add(mir(TX["lamp_white"]), "light_white").add(mir(TX["lamp_nav"]), col).add(mir(TX["strobe_lamp"]), "light_white")
    A = TX["anchors"]
    tag = "L" if sgn < 0 else "R"
    wing_part.info["light_anchors"] = {
        f"nav{tag}": {"p": m(A["nav"]).tolist(), "colour": "red" if sgn < 0 else "green",
                      "src": "AFM walk-around 'Wing Tip, Strobe/Nav Lights'; lens at the tip leading edge (Cirrus photos) [inf: position]"},
        f"strobe{tag}": {"p": m(A["strobe"]).tolist(), "colour": "white",
                         "src": "AFM Kinds of Operation: anti-collision lights 3 installed [inf: position on the tip]"},
        f"land{tag}": {"p": m(A["land"]).tolist(), "colour": "white",
                       "src": "AFM Kinds of Operation 'Landing Lights 4/0 ... at least one wingtip landing light is operative' "
                              "(wing-tip landing lights exist) [obs]; their number per tip and position [inf]"},
    }


def build_wing_details(parts, wing_part, side, sgn, mir):
    m = lambda v: np.asarray(v, float) * [1, sgn, 1]
    det = []
    # pitot probe under the wing near the tip (AFM walk-around 'Wing Tip ... Pitot Probe') [inf: position]
    yy = G.Y_TIPCAP - 0.45
    sec = section_at(yy)
    base = sec.point(np.array(0.22), np.array(float(sec.airfoil.lower(0.22))))
    p1 = base + [0, 0, -0.10]
    p2 = p1 + [-0.26, 0, 0]
    det.append(cylinder(base + [0, 0, 0.01], p1, 0.010, n=10))
    det.append(cylinder(p1 + [0.01, 0, 0], p2, 0.008, n=10))
    det.append(sweep_tube(np.array([p2, p2 + [-0.03, 0, 0]]), 0.006, n=10))
    # wing-root vortex generators (AFM 'Wing Root Vortex Generator') [inf: three small vanes on the upper surface]
    vg = []
    for k, yy in enumerate((1.00, 1.08, 1.16)):
        sec = section_at(yy)
        p = sec.point(np.array(0.10), np.array(float(sec.airfoil.upper(0.10))))
        vg.append(box(p + [0, 0, 0.012], (0.05, 0.003, 0.024), R=__import__("sf50_kernel").rotation_matrix((0, 0, 1), np.radians(15 * (-1) ** k))))
    # aileron fence at the aileron inboard end (AFM 'Aileron Fence (if installed)') [inf: shape]
    sec = section_at(G.Y_AIL[0] - 0.02)
    xs = np.linspace(0.55, 0.98, 10)
    up = sec.upper(xs)
    fence = []
    for a, b in zip(up[:-1], up[1:]):
        c = 0.5 * (a + b)
        L = np.linalg.norm(b - a)
        fence.append(box(c + [0, 0, 0.022], (L, 0.004, 0.045)))
    wp = Part(f"wing_details_{side}", f"{'Right' if sgn > 0 else 'Left'} wing details (pitot, VGs, fence)", "details",
              group="Systems", material_note="[inf: positions]")
    wp.add(mir(Mesh.merge(det)), "metal").add(mir(Mesh.merge(vg + fence)), "paint_white")
    parts[wp.id] = wp
