"""
PC-12 wing: tapered, unswept quarter-chord, LS(1)-0417MOD root -> LS(1)-0313 tip,
single-piece Fowler flap (67 % of trailing edge), short-span mass-balanced
aileron, blended winglet, pneumatic de-ice boots, flap-track fairings.

Planform (reference trapezoid to the winglet root, both halves):
    area 25.81 m^2, winglet-tip span 16.28 m, root chord 2.151 m, tip chord 1.075 m
    -> MAC 1.673 m at y = 3.556 m, LEMAC = STA 5.337 m (from the POH aft CG limit
       6.107 m = 46 % MAC), quarter chord STA 5.755 m.
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, trim, planar_cap, grid_surface, cap_ring, superellipsoid, rotation_matrix, band
from model.airfoil import ls0417mod, ls0313, naca00
from model.lifting import Section, skin, strip, curve_patch, closed_body, bezier, cos_pts
from model.parts import Part

# ---- design constraints (official data) ---------------------------------
SPAN_TOTAL = 16.28          # m, over the winglets
AREA_REF = 25.81            # m^2, reference trapezoid
TAPER = 0.50                # tip / root chord (estimated from planform)
AFT_CG = 6.107              # m aft of datum at MTOW = 46 % MAC (POH / Jane's)
AFT_CG_MAC = 0.46

# ---- winglet shape ("PC-21 style", Series 10A onward; POPA variant guide) ------
# Pilatus publishes no winglet geometry.  Values below are estimates cross-checked
# against an independent open-source PC-12 model: small fin blended into the aft
# half of the tip, ~30 deg cant, ~32 deg LE sweep, ~0.27 m above the upper skin.
WL_BEND_R = 0.14
WL_CANT = np.radians(30.0)       # from vertical, outward
WL_HEIGHT = 0.30                 # straight part above the bend
WL_MID_CHORD = 0.45              # chord at the end of the blend
WL_TIP_CHORD = 0.32
WL_TE_SWEEP = 0.06               # trailing edge moves aft by this much tip-to-top (m)
WL_LE_SWEEP = np.radians(32.0)   # nominal, for reporting
_a_end = np.pi / 2 - WL_CANT
WL_LATERAL = WL_BEND_R * np.sin(_a_end) + WL_HEIGHT * np.cos(_a_end)

# ---- derived planform -------------------------------------------------------
WL_SKIN = 0.0118                                   # winglet outer skin beyond its chord path at the tip
SEMI = SPAN_TOTAL / 2 - WL_LATERAL - WL_SKIN        # winglet-root butt line
C_ROOT = AREA_REF / SEMI / (1 + TAPER)
C_TIP = TAPER * C_ROOT
MAC = 2 / 3 * C_ROOT * (1 + TAPER + TAPER ** 2) / (1 + TAPER)
LEMAC = AFT_CG - AFT_CG_MAC * MAC
X_QC = LEMAC + 0.25 * MAC                           # unswept quarter-chord line
DIHEDRAL = np.radians(4.5)
Z_QC0 = 0.905
INC_ROOT, INC_TIP = np.radians(2.0), np.radians(-1.0)

Y_FLAP = (0.80, 5.90)
Y_AIL = (5.96, 7.62)
FLAP_X_LO, FLAP_X_LIP = 0.695, 0.745
AIL_XH = 0.765
BOOT_Y = (0.95, 7.55)
GAP = 0.012   # spanwise gap between control surface and wing (m)

ROOT_AF, TIP_AF = ls0417mod(), ls0313()


def chord(y):
    return C_ROOT + (C_TIP - C_ROOT) * np.clip(y, 0, SEMI) / SEMI


def airfoil_at(y):
    w = np.clip((y - 0.6) / (SEMI - 0.6), 0, 1)
    return ROOT_AF.blend(TIP_AF, w)


def section_at(y):
    """Right-wing section at butt line y (>= 0)."""
    c = chord(y)
    x_le = X_QC - 0.25 * c
    z_ref = Z_QC0 + y * np.tan(DIHEDRAL)
    tw = INC_ROOT + (INC_TIP - INC_ROOT) * np.clip(y, 0, SEMI) / SEMI
    return Section(le=np.array([x_le, y, z_ref]), chord=c, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 0, 1.0]), twist=tw, airfoil=airfoil_at(y))


def mac():
    lam = C_TIP / C_ROOT
    m = 2 / 3 * C_ROOT * (1 + lam + lam ** 2) / (1 + lam)
    ym = SEMI / 3 * (1 + 2 * lam) / (1 + lam)
    return m, ym, X_QC - 0.25 * m


# ---------------------------------------------------------------------------
# control-surface section geometry (chord units)
# ---------------------------------------------------------------------------

def flap_cove(sec, n=14):
    af = sec.airfoil
    lo = np.array([FLAP_X_LO, float(af.lower(FLAP_X_LO))])
    zu_lip = float(af.upper(FLAP_X_LIP))
    lip_b = np.array([FLAP_X_LIP, zu_lip - 0.0055])
    c = bezier(lo, lo + [-0.045, 0.004], [0.650, zu_lip - 0.028], lip_b, n=n)
    return np.vstack([c, [[FLAP_X_LIP, zu_lip]]])


def flap_loop(sec, n=18):
    af = sec.airfoil
    xu = cos_pts(n, 0.0, 1.0) * (1 - 0.736) + 0.736
    zu = af.upper(xu)
    blend = np.clip((0.758 - xu) / 0.022, 0, 1)
    zu = zu - 0.0075 * blend
    xl = (cos_pts(n, 0.0, 1.0) * (1 - 0.708) + 0.708)[::-1]
    zl = af.lower(xl)
    nose_top = np.array([xu[0], zu[0]])
    nose_bot = np.array([0.708, float(af.lower(0.708))])
    nose = bezier(nose_bot, nose_bot + [-0.034, 0.006], [0.668, nose_top[1] - 0.030], nose_top, n=12)
    upper = np.stack([xu, zu], 1)
    lower = np.stack([xl, zl], 1)
    loop = np.vstack([upper[:-1], [[1.0, float(af.upper(1.0))]], [[1.0, float(af.lower(1.0))]], lower[1:-1], nose[:-1]])
    return loop


def hinge_arc_ends(af, xh, R):
    """Angles where a circle (centre on camber at xh, radius R) meets the upper/lower surface."""
    zh = float(af.camber(xh))

    def f(th, surf):
        x = xh + R * np.cos(th)
        z = zh + R * np.sin(th)
        return z - float(surf(x))
    # upper: search theta in (pi/2, pi)
    a, b = np.pi / 2, np.pi
    for _ in range(50):
        m = 0.5 * (a + b)
        if f(m, af.upper) > 0:
            a = m
        else:
            b = m
    tu = 0.5 * (a + b)
    a, b = np.pi, 1.5 * np.pi
    for _ in range(50):
        m = 0.5 * (a + b)
        if f(m, af.lower) < 0:
            b = m
        else:
            a = m
    tl = 0.5 * (a + b)
    return zh, tu, tl


def plain_cove(sec, xh, gap=0.010, n=16):
    af = sec.airfoil
    r = 0.5 * float(af.upper(xh) - af.lower(xh))
    R = r + gap
    zh, tu, tl = hinge_arc_ends(af, xh, R)
    th = np.linspace(tu, tl, n)
    return np.stack([xh + R * np.cos(th), zh + R * np.sin(th)], 1), (tu, tl, R)


def plain_surface_loop(sec, xh, n=16, x_end=1.0):
    """Control-surface section: round nose about the hinge, airfoil surfaces aft.
    x_end < 1 truncates it with a flat face (the cut-out for a tab)."""
    af = sec.airfoil
    r = 0.5 * float(af.upper(xh) - af.lower(xh))
    zh = float(af.camber(xh))
    xu = cos_pts(n, 0, 1) * (x_end - xh) + xh
    upper = np.stack([xu, af.upper(xu)], 1)
    lower = upper.copy()
    lower[:, 1] = af.lower(xu)
    lower = lower[::-1]
    th = np.linspace(1.5 * np.pi, 0.5 * np.pi, 13)[1:-1]
    nose = np.stack([xh + r * np.cos(th), zh + r * np.sin(th)], 1)  # from bottom, around the front, to top
    # upper (LE->TE), TE, lower (TE->LE), nose (bottom->top)
    loop = np.vstack([upper, lower, nose])
    return loop


def tab_loop(sec, x0, n=10):
    """Trim/balance tab section from x0 to the trailing edge, blunt round nose."""
    af = sec.airfoil
    r = 0.5 * float(af.upper(x0) - af.lower(x0))
    zh = float(af.camber(x0))
    xu = cos_pts(n, 0, 1) * (1 - x0 - r) + x0 + r
    upper = np.stack([xu, af.upper(xu)], 1)
    lower = np.stack([xu[::-1], af.lower(xu[::-1])], 1)
    th = np.linspace(1.5 * np.pi, 0.5 * np.pi, 9)[1:-1]
    nose = np.stack([x0 + r + r * np.cos(th), zh + r * np.sin(th)], 1)
    return np.vstack([upper, lower, nose])


def segmented_surface(section_fn, s0, s1, xh, tab, step=0.15, gap=0.008):
    """Control surface split around a tab cut-out.  Returns (body, tab_body, tab_hinge_pts)."""
    t0, t1, xt = tab
    bodies = [closed_body(section_fn, span_stations(s0, t0, step), lambda s: plain_surface_loop(s, xh)),
              closed_body(section_fn, span_stations(t0, t1, step), lambda s: plain_surface_loop(s, xh, x_end=xt)),
              closed_body(section_fn, span_stations(t1, s1, step), lambda s: plain_surface_loop(s, xh))]
    tb = closed_body(section_fn, span_stations(t0 + gap, t1 - gap, step), lambda s: tab_loop(s, xt + 0.004))
    a, b = section_fn(t0), section_fn(t1)
    ha = a.point(np.array(xt + 0.004), np.array(float(a.airfoil.camber(xt))))
    hb = b.point(np.array(xt + 0.004), np.array(float(b.airfoil.camber(xt))))
    return Mesh.merge(bodies), tb, (ha, hb)


def x_end_of_plain(sec, xh, gap=0.010):
    _, (tu, tl, R) = plain_cove(sec, xh, gap)
    zh = float(sec.airfoil.camber(xh))
    return xh + R * np.cos(tu), xh + R * np.cos(tl)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def span_stations(a, b, step=0.25):
    n = max(2, int(np.ceil((b - a) / step)) + 1)
    return np.linspace(a, b, n)


def cut_rib(sec, cove2d, x_lo, x_up):
    """Flat rib closing the section aft of a cove (chord units polygon)."""
    af = sec.airfoil
    xs_u = cos_pts(14, 0, 1) * (1 - x_up) + x_up
    xs_l = (cos_pts(14, 0, 1) * (1 - x_lo) + x_lo)[::-1]
    poly = np.vstack([cove2d[:-1] if len(cove2d) > 2 else cove2d,
                      np.stack([xs_u, af.upper(xs_u)], 1),
                      np.stack([xs_l, af.lower(xs_l)], 1)[:-1]])
    pts = sec.point(poly[:, 0], poly[:, 1])
    return pts


def build_right(n=60):
    """Return dict of meshes for the right wing (y >= 0)."""
    out = {"skin": [], "boot": [], "flap": None, "aileron": None, "ribs": [], "winglet": None}

    def add_skin(m):
        # split off the leading-edge de-ice boot band
        uvx = m.UV[:, 1]
        y = m.UV[:, 0]
        f_boot = np.maximum(np.maximum(np.where(uvx >= 0, uvx - 0.10, -uvx - 0.065), BOOT_Y[0] - y), y - BOOT_Y[1])
        boot = trim(m, f_boot, "negative")
        rest = trim(m, f_boot, "positive")
        # main-gear wheel well + leg slot in the lower skin
        from model.bays import main_opening_sdf
        fw = np.where(rest.UV[:, 1] < 0, main_opening_sdf(rest.V[:, 0], rest.V[:, 1]), 1.0)
        if (fw < 0).any():
            rest = trim(rest, fw, "positive")
        out["skin"].append(rest)
        if boot.nf:
            out["boot"].append(boot.offset(0.0015))

    # panel A: root -> flap start (full section)
    ys = span_stations(0.0, Y_FLAP[0], 0.2)
    add_skin(skin(section_at, ys, n=n))
    out["skin"].append(strip(section_at, ys, 1.0, 1.0))

    # panel B: flap bay
    ys = span_stations(Y_FLAP[0], Y_FLAP[1], 0.25)
    add_skin(skin(section_at, ys, x_lo_end=FLAP_X_LO, x_up_end=FLAP_X_LIP, n=n))
    out["skin"].append(curve_patch(section_at, ys, flap_cove,
                                   outward_hint=lambda s: s.e_c))

    # panel C: between flap and aileron
    ys = span_stations(Y_FLAP[1], Y_AIL[0], 0.1)
    add_skin(skin(section_at, ys, n=n))
    out["skin"].append(strip(section_at, ys, 1.0, 1.0))

    # panel D: aileron bay
    ys = span_stations(Y_AIL[0], Y_AIL[1], 0.2)
    xl_end, xu_end = x_end_of_plain(section_at(0.5 * sum(Y_AIL)), AIL_XH)
    add_skin(skin(section_at, ys, x_lo_end=xl_end, x_up_end=xu_end, n=n))
    out["skin"].append(curve_patch(section_at, ys, lambda s: plain_cove(s, AIL_XH)[0],
                                   outward_hint=lambda s: s.e_c))

    # panel E: aileron end -> tip
    ys = span_stations(Y_AIL[1], SEMI, 0.1)
    add_skin(skin(section_at, ys, n=n))
    out["skin"].append(strip(section_at, ys, 1.0, 1.0))

    # cut ribs at the ends of the flap and aileron bays
    for y, sgn in ((Y_FLAP[0], +1), (Y_FLAP[1], -1)):
        sec = section_at(y)
        pts = cut_rib(sec, flap_cove(sec), FLAP_X_LO, FLAP_X_LIP)
        out["ribs"].append(planar_cap(pts, (0, sgn, 0)))
    for y, sgn in ((Y_AIL[0], +1), (Y_AIL[1], -1)):
        sec = section_at(y)
        cove, _ = plain_cove(sec, AIL_XH)
        xl_e, xu_e = x_end_of_plain(sec, AIL_XH)
        pts = cut_rib(sec, cove[::-1], xl_e, xu_e)
        out["ribs"].append(planar_cap(pts, (0, sgn, 0)))

    # flap body
    ys = span_stations(Y_FLAP[0] + GAP, Y_FLAP[1] - GAP, 0.25)
    out["flap"] = closed_body(section_at, ys, flap_loop)
    # aileron body with the Flettner geared balance tab cut-out (inboard 40 %)
    body, tabm, hinge = segmented_surface(section_at, Y_AIL[0] + GAP, Y_AIL[1] - GAP, AIL_XH,
                                          (Y_AIL[0] + 0.06, Y_AIL[0] + 0.72, 0.945), step=0.2)
    out["aileron"] = body
    out["ail_tab"] = (tabm, hinge)

    out["winglet"] = build_winglet()
    return out


# ---------------------------------------------------------------------------
# winglet
# ---------------------------------------------------------------------------
def winglet_path(n_bend=14, n_straight=8):
    sec0 = section_at(SEMI)
    y0, z0 = SEMI, sec0.le[2]
    # bend: circle centre above the tip
    a_end = np.pi / 2 - WL_CANT                    # final path angle from horizontal
    th = np.linspace(0, a_end, n_bend)
    cy, cz = y0, z0 + WL_BEND_R
    pts = [(cy + WL_BEND_R * np.sin(t), cz - WL_BEND_R * np.cos(t), t) for t in th]
    yb, zb, _ = pts[-1]
    for k in range(1, n_straight + 1):
        d = WL_HEIGHT * k / n_straight
        pts.append((yb + d * np.cos(a_end), zb + d * np.sin(a_end), a_end))
    arr = np.array(pts)
    # arc length
    seg = np.r_[0, np.cumsum(np.hypot(np.diff(arr[:, 0]), np.diff(arr[:, 1])))]
    return arr, seg


def build_winglet():
    arr, seg = winglet_path()
    L = seg[-1]
    s1 = WL_BEND_R * (np.pi / 2 - WL_CANT)          # arc length of the blend
    sec0 = section_at(SEMI)
    te0 = sec0.le[0] + sec0.chord
    tipaf = naca00(0.09)
    rows = []
    for (y, z, a), s in zip(arr, seg):
        u = min(s / s1, 1.0)
        blend = u * u * (3 - 2 * u)                  # smoothstep through the bend
        if s <= s1:
            c = C_TIP + (WL_MID_CHORD - C_TIP) * blend
        else:
            c = WL_MID_CHORD + (WL_TIP_CHORD - WL_MID_CHORD) * (s - s1) / (L - s1)
        te = te0 + WL_TE_SWEEP * s / L
        x_le = te - c
        e_t = np.array([0.0, -np.sin(a), np.cos(a)])
        af = sec0.airfoil.blend(tipaf, min(1.0, s / s1))
        tw = INC_TIP * (1 - blend)
        sec = Section(le=np.array([x_le, y, z]), chord=c, e_c=np.array([1.0, 0, 0]), e_t=e_t,
                      twist=tw, airfoil=af)
        n = 60
        xl = cos_pts(n)[::-1]
        xu = cos_pts(n)[1:]
        rows.append(np.vstack([sec.lower(xl), sec.upper(xu)]))
    P = np.array(rows)
    m = grid_surface(P)
    i = P.shape[1] // 2 + 20
    if np.dot(m.N[i], np.array([0, 0, 1.0])) < 0:
        m = m.flipped()
    te = grid_surface(np.stack([P[:, 0], P[:, -1]], 1))
    if np.dot(te.N.mean(0), [1, 0, 0]) < 0:
        te = te.flipped()
    cap = cap_ring(P[-1], P[-1].mean(0) - P[-2].mean(0))
    return Mesh.merge([m, te, cap]), P


# ---------------------------------------------------------------------------
def build(parts: dict):
    R = build_right()
    meshes_R = R
    wing_ribs = Mesh.merge(R["ribs"])
    for side, sgn in (("R", 1), ("L", -1)):
        def mir(m):
            return m if sgn > 0 else m.mirrored_y()
        skin_m = mir(Mesh.merge(R["skin"] + [wing_ribs]))
        boot_m = mir(Mesh.merge(R["boot"]))
        wl, _ = R["winglet"]
        wl = mir(wl)
        p = Part(f"wing_{side}", f"{'Right' if sgn > 0 else 'Left'} wing (integral fuel tank)", "wing",
                 explode=(0, sgn * 1.4, -0.15), group="Wing",
                 material_note="2024/7075 two-spar box, integral tank ribs 3-16",
                 info={"root chord": f"{C_ROOT*1000:,.0f} mm, LS(1)-0417MOD",
                       "tip chord": f"{C_TIP*1000:,.0f} mm, LS(1)-0313",
                       "MAC": f"{MAC*1000:,.0f} mm, LEMAC STA {LEMAC*1000:,.0f}",
                       "dihedral": "4.5 deg (est.)", "incidence": "+2.0 root / -1.0 tip (est.)"})
        p.add(skin_m, "paint_white").add(boot_m, "deice_boot")
        parts[p.id] = p
        w = Part(f"winglet_{side}", f"{'Right' if sgn > 0 else 'Left'} winglet", "winglets",
                 explode=(0, sgn * 0.8, 0.5), group="Wing", material_note="Carbon fibre / honeycomb, Cu foil")
        w.add(wl, "paint_white")
        parts[w.id] = w

        # flap: hinge/track motion (Fowler) around a line near the flap nose
        a = section_at(Y_FLAP[0])
        b = section_at(Y_FLAP[1])
        ha = a.point(np.array(0.73), np.array(float(a.airfoil.camber(0.73))))
        hb = b.point(np.array(0.73), np.array(float(b.airfoil.camber(0.73))))
        if sgn < 0:
            ha, hb = ha * [1, -1, 1], hb * [1, -1, 1]
        axis = (hb - ha) / np.linalg.norm(hb - ha)
        cm = 0.5 * (a.chord + b.chord)
        f = Part(f"flap_{side}", f"{'Right' if sgn > 0 else 'Left'} Fowler flap", "controls_wing",
                 pivot=dict(origin=ha.tolist(), axis=(axis * sgn).tolist(), kind="flap",
                            travel=[0.20 * cm, 0.0, -0.035 * cm], max=40.0, settings=[0, 15, 30, 40]),
                 explode=(0.9, 0, -0.3), group="Flight controls",
                 material_note="Single-piece Fowler flap, 3 support arms")
        f.add(mir(R["flap"]), "paint_white")
        parts[f.id] = f
        a = section_at(Y_AIL[0])
        b = section_at(Y_AIL[1])
        ha = a.point(np.array(AIL_XH), np.array(float(a.airfoil.camber(AIL_XH))))
        hb = b.point(np.array(AIL_XH), np.array(float(b.airfoil.camber(AIL_XH))))
        if sgn < 0:
            ha, hb = ha * [1, -1, 1], hb * [1, -1, 1]
        axis = (hb - ha) / np.linalg.norm(hb - ha)
        ai = Part(f"aileron_{side}", f"{'Right' if sgn > 0 else 'Left'} aileron", "controls_wing",
                  pivot=dict(origin=ha.tolist(), axis=(axis * sgn).tolist(), kind="aileron",
                             range=[-20.0, 15.0], sign=sgn),
                  explode=(0.8, sgn * 0.3, 0.2), group="Flight controls",
                  material_note="Mass-balanced, sealed gap")
        ai.add(mir(R["aileron"]), "paint_white")
        parts[ai.id] = ai
        tabm, (ta, tb) = R["ail_tab"]
        if sgn < 0:
            ta, tb = ta * [1, -1, 1], tb * [1, -1, 1]
        tax = (tb - ta) / np.linalg.norm(tb - ta)
        tp = Part(f"ail_tab_{side}", f"{'Right' if sgn > 0 else 'Left'} aileron Flettner tab"
                  + (" (electric trim)" if sgn < 0 else ""), "controls_wing", parent=ai.id,
                  pivot=dict(origin=ta.tolist(), axis=(tax * sgn).tolist(), kind="tab", gearing=-0.6),
                  explode=(0.35, 0, 0), group="Flight controls",
                  material_note="Geared balance tab, moves opposite to the aileron (POH 7-3)")
        tp.add(mir(tabm), "paint_white")
        parts[tp.id] = tp
    return parts


if __name__ == "__main__":
    m, ym, lemac = mac()
    print("SEMI %.3f  C_ROOT %.4f C_TIP %.4f" % (SEMI, C_ROOT, C_TIP))
    print("MAC %.4f m at y=%.3f, LEMAC STA %.4f  X_QC %.4f" % (m, ym, lemac, X_QC))
    S = 2 * SEMI * (C_ROOT + C_TIP) / 2
    print("reference area %.2f m2" % S)
    arr, seg = winglet_path()
    print("winglet top y=%.3f  (span = %.3f m)" % (arr[-1, 0], 2 * arr[-1, 0]))
