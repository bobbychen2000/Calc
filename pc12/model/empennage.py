"""
PC-12 T-tail: swept fin with dorsal fin, rudder with trim tab, trimmable (variable-incidence) tailplane
with paired elevators and horn-balanced tips, fin/tailplane bullet fairing, and twin ventral strakes.

Stage 2 (rev B): positions and planforms from the Pilatus NGX model drawing 190.10.40.432 (side view,
plan, front view and the fin / tailplane sections VF1 WL 2609, VF2 WL 3919, HF1 BL 0, HF2 BL 2270):
  fin        straight LE 40.3 deg (through the VF1 / VF2 leading edges, meeting the crown at FR40),
             rudder TE 22.2 deg from the tail-cone closure (STA 13,568 WL 1,912) to the bullet; NACA 0018
             (VF1 17.8 %, VF2 17.9 %); rudder nose at 63.7 % chord, hinge (nose-circle centre) 69.7 %
  dorsal     straight top edge from the crown at FR33 (STA 9,000 WL 2,770) rising 0.134 m/m, blended
             into the fin LE at WL ~3,400; max half-width 114 mm (FR38 / FR40 sections)
  tailplane  chord plane WL 4,099 (zero dihedral, zero incidence as drawn), LE x = 13.0696 + 0.1267 y,
             TE x = 14.3996 - 0.0542 y, elevator hinge at a constant STA 14,000 (= 70 % chord), fixed
             tip rib BL 2,270, horn balance BL 2,270 - 2,600; NACA 0012 root -> 0009 tip (HF1 / HF2)
  bullet     STA 12,606 - 14,790 (drawn end 14,811, 21 mm aft: the official 14.40 m length wins),
             elliptic sections, WL 3,917 - 4,261, 289 mm wide
  strakes    root line STA 9,750 WL 1,365 -> STA 12,190 WL 1,955 on the tail-cone side, tip line
             STA 9,790 WL 1,335 -> STA 11,870 WL 1,530, canted 11 deg (tip outboard; FR38 / FR40)
Anchors: tailplane span 5.20 m (Pilatus), overall height 4.26 m (top of bullet), overall length 14.40 m
(spinner tip STA 0.39 -> aft-most point STA 14.79).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, grid_surface, planar_cap, revolve, cap_ring, trim
from model.airfoil import Airfoil, naca00, naca4_thickness
from model.lifting import Section, skin, strip, curve_patch, closed_body, cos_pts
from model.wing import plain_cove, plain_surface_loop, x_end_of_plain, span_stations
from model.parts import Part
from model import fuselage as F

# ---------------------------------------------------------------- fin
FIN_Z0, FIN_Z1 = 1.76, 4.05            # root (buried in the tail cone, ventral below it) / tip (in the bullet)
FIN_LE = ((11.868, 2.609), (12.978, 3.919))     # straight LE through the VF1 / VF2 leading edges
FIN_TE = ((13.568, 1.912), (14.386, 3.919))     # rudder trailing edge
RUD_Z = (1.80, 3.82)                    # rudder bottom / top (drawn edges slope 1.76-1.91 / 3.86-3.78)
# lower edge of the exposed ventral part of the fin and of the rudder below the tail cone (side view, from the
# strake's aft end to the lower rudder TE corner); the fin root sections run down to FIN_Z0 and Stage 3 trims
# them (and models the ventral fairing, FR40) to this line
VENTRAL_EDGE = ((11.950, 1.645), (13.568, 1.912))
RUD_XH = 0.697                          # hinge at 69.7 % local chord (rudder nose-circle centre)
RUD_TAB = (2.55, 3.60, 0.940)           # rudder trim tab: WL range and hinge chord fraction
FIN_AF_ROOT, FIN_AF_TIP = naca00(0.18), naca00(0.18)


def _lin(p, q, z):
    return p[0] + (q[0] - p[0]) * (z - p[1]) / (q[1] - p[1])


def fin_le(z):
    return _lin(*FIN_LE, z)


def fin_te(z):
    return _lin(*FIN_TE, z)


def fin_section(z):
    xl = fin_le(z)
    xt = fin_te(z)
    w = np.clip((z - FIN_Z0) / (FIN_Z1 - FIN_Z0), 0, 1)
    af = FIN_AF_ROOT.blend(FIN_AF_TIP, w)
    return Section(le=np.array([xl, 0.0, z]), chord=xt - xl, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=af)


# ---------------------------------------------------------------- tailplane
STAB_Z = 4.099                         # chord plane WL (front view / HF1 / HF2)
STAB_ROOT_LE = 13.0696                 # leading edge at BL 0
STAB_ROOT_C = 1.330                    # chord at BL 0
STAB_SWEEP = np.arctan(0.1267)         # leading edge 7.2 deg
STAB_TE_SLOPE = -0.0542                # trailing edge dx/dy (slightly forward-swept)
STAB_TIP_Y = 2.60                      # 5.20 m span
STAB_TIP_RIB = 2.27                    # fixed-stabiliser tip rib (HF2); horn balance outboard
STAB_TAPER_C = STAB_ROOT_C + (STAB_TE_SLOPE - np.tan(STAB_SWEEP)) * STAB_TIP_RIB   # chord at the tip rib
ELEV_Y = (0.120, 2.270)
ELEV_HORN = (2.270, 2.600, 13.650)     # horn balance: BL range, its leading-edge station
ELEV_XH = 0.70                         # hinge (= constant STA 14,000 with these LE / TE lines)
STAB_INC = np.radians(0.0)
STAB_AF_ROOT, STAB_AF_TIP = naca00(0.12), naca00(0.09)
STAB_AF = STAB_AF_ROOT


def _stab_le_lin(y):
    return STAB_ROOT_LE + abs(y) * np.tan(STAB_SWEEP)


def stab_le(y):
    """Leading edge (outer envelope in plan): straight to BL 2.30, then raked back along the fixed tip and
    the horn balance to the tip at STA ~14.0."""
    y = abs(y)
    k = np.clip((y - 2.30) / (STAB_TIP_Y - 2.30), 0, 1)
    return _stab_le_lin(y) + (14.00 - _stab_le_lin(STAB_TIP_Y)) * k ** 2


def stab_te(y):
    return STAB_ROOT_LE + STAB_ROOT_C + abs(y) * STAB_TE_SLOPE


def stab_section(y):
    xl, xt = stab_le(y), stab_te(y)
    c = max(xt - xl, 0.02)
    af = STAB_AF_ROOT.blend(STAB_AF_TIP, float(np.clip(abs(y) / STAB_TIP_RIB, 0, 1)))
    return Section(le=np.array([xl, y, STAB_Z]), chord=c, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 0, 1.0]), twist=STAB_INC, airfoil=af)


# ---------------------------------------------------------------- dorsal fin
DORSAL_X0, DORSAL_Z0 = 9.000, 2.770    # starts on the crown at FR33
DORSAL_SLOPE = 0.1338                  # straight top edge dz/dx
DORSAL_KNEE_X = 12.20                  # end of the straight edge; quadratic blend into the fin LE
DORSAL_HW = 0.114                      # max half-width (FR38 / FR40)
DORSAL_RAMP = 3.2                      # m behind the edge to full width (FR36: 74 mm at 0.75 m)
DORSAL_ZTOP = 3.40                     # the blend meets the fin LE here (approx.)


def _dorsal_curve(n=24):
    """Side-view top edge of the dorsal fin as (x, z) points: straight edge, then a quadratic Bezier tangent
    to the edge and to the fin LE line."""
    k = np.array([DORSAL_KNEE_X, DORSAL_Z0 + DORSAL_SLOPE * (DORSAL_KNEE_X - DORSAL_X0)])
    # corner C = intersection of the edge line with the fin LE line
    (x1, z1), (x2, z2) = FIN_LE
    g = (x2 - x1) / (z2 - z1)                          # fin LE dx/dz
    # z = z0 + s (x - x0)  and  x = x1 + g (z - z1)
    zc = (DORSAL_Z0 + DORSAL_SLOPE * (x1 - g * z1 - DORSAL_X0)) / (1 - DORSAL_SLOPE * g)
    c = np.array([x1 + g * (zc - z1), zc])
    d = np.linalg.norm(c - k)
    u = np.array([g, 1.0]) / np.hypot(g, 1.0)
    f = c + d * u
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * k + 2 * t * (1 - t) * c + t ** 2 * f


def dorsal_edge_x(z):
    """Station of the dorsal fin's top edge at water line z."""
    cur = _dorsal_curve(64)
    zk = cur[0, 1]
    if z <= zk:
        return DORSAL_X0 + (z - DORSAL_Z0) / DORSAL_SLOPE
    if z >= cur[-1, 1]:
        return fin_le(z)
    return float(np.interp(z, cur[:, 1], cur[:, 0]))


def dorsal_section(z):
    x_start = dorsal_edge_x(z)
    x_end = fin_le(z) + 0.45
    c = max(x_end - x_start, 0.05)

    def half(xc, c=c):
        u = np.clip(np.asarray(xc, float) * c / DORSAL_RAMP, 0, 1)
        return DORSAL_HW / c * np.sqrt(np.clip(1 - (1 - u) ** 2, 0, 1)) * np.clip((1 - np.asarray(xc, float)) / 0.05, 0, 1) ** 0.5

    af = Airfoil("dorsal", half, lambda x: 0.0 * np.asarray(x, float))
    return Section(le=np.array([x_start, 0.0, z]), chord=c, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=af)


# ---------------------------------------------------------------- bullet fairing (side view + plan of the drawing)
# station, top WL, bottom WL, half-width (aft of STA 13.5 compressed so the end is STA 14.790, drawn 14.811)
BULLET = ((12.606, 4.099, 4.099, 0.000), (12.650, 4.150, 4.048, 0.040), (12.700, 4.174, 4.022, 0.056),
          (12.800, 4.207, 3.984, 0.083), (12.900, 4.229, 3.958, 0.104), (13.000, 4.244, 3.939, 0.119),
          (13.100, 4.254, 3.926, 0.130), (13.200, 4.259, 3.919, 0.139), (13.300, 4.260, 3.917, 0.142),
          (13.400, 4.257, 3.920, 0.144), (13.500, 4.246, 3.927, 0.138), (13.600, 4.244, 3.929, 0.132),
          (13.800, 4.240, 3.938, 0.121), (14.000, 4.236, 3.951, 0.110), (14.200, 4.232, 3.970, 0.107),
          (14.400, 4.228, 4.000, 0.092), (14.500, 4.222, 4.019, 0.080), (14.600, 4.213, 4.039, 0.064),
          (14.700, 4.201, 4.062, 0.046), (14.790, 4.186, 4.090, 0.020))
BULLET_X = (BULLET[0][0], BULLET[-1][0])
BULLET_EXP = 2.3                       # section super-ellipse exponent


def bullet_section(x, n=48):
    """Bullet cross-section at station x (closed ring, n points)."""
    T = np.array(BULLET)
    zt, zb, w = (np.interp(x, T[:, 0], T[:, k]) for k in (1, 2, 3))
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    zc, hz = 0.5 * (zt + zb), 0.5 * (zt - zb)
    y = w * np.sign(np.sin(a)) * np.abs(np.sin(a)) ** (2 / BULLET_EXP)
    z = zc + hz * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** (2 / BULLET_EXP)
    return np.stack([np.full(n, x), y, z], 1)


# ---------------------------------------------------------------- ventral strakes (side view, FR38 / FR40)
STRAKE_ROOT = ((9.750, 1.365), (12.190, 1.955))   # attachment line on the tail-cone side (x, z)
STRAKE_TIP = ((9.790, 1.335), (11.870, 1.530))    # lower (tip) edge; aft edge from its end to the root end
STRAKE_CANT = np.radians(11.0)                      # from vertical, tip outboard
STRAKE_T = 0.022                                    # plate thickness


def strake_frame(x):
    """(root point, tip point) of the starboard strake in the cross-section at station x (None outside)."""
    (r0x, r0z), (r1x, r1z) = STRAKE_ROOT
    (t0x, t0z), (t1x, t1z) = STRAKE_TIP
    if x < r0x or x > r1x:
        return None
    zr = r0z + (r1z - r0z) * (x - r0x) / (r1x - r0x)
    if x <= t1x:
        zt = t0z + (t1z - t0z) * np.clip((x - t0x) / (t1x - t0x), 0, 1)
        zt = min(zt, zr)
    else:                                            # aft edge: straight from the tip end to the root end
        zt = t1z + (r1z - t1z) * (x - t1x) / (r1x - t1x)
    yr = float(F.side_y(x, zr))
    depth = (zr - zt) / np.cos(STRAKE_CANT)
    return np.array([x, yr, zr]), np.array([x, yr + depth * np.sin(STRAKE_CANT), zt])


def build(parts: dict):
    # ---------------- fin (fixed part) + rudder
    zs_all = span_stations(FIN_Z0, FIN_Z1, 0.12)
    meshes = []
    zA = span_stations(FIN_Z0, RUD_Z[0], 0.1)
    meshes.append(skin(fin_section, zA, n=48))
    meshes.append(strip(fin_section, zA, 1.0, 1.0))
    zB = span_stations(RUD_Z[0], RUD_Z[1], 0.12)
    xl_e, xu_e = x_end_of_plain(fin_section(np.mean(RUD_Z)), RUD_XH)
    meshes.append(skin(fin_section, zB, x_lo_end=xl_e, x_up_end=xu_e, n=48))
    meshes.append(curve_patch(fin_section, zB, lambda s: plain_cove(s, RUD_XH)[0], outward_hint=lambda s: s.e_c))
    zC = span_stations(RUD_Z[1], FIN_Z1, 0.05)
    meshes.append(skin(fin_section, zC, n=48))
    meshes.append(strip(fin_section, zC, 1.0, 1.0))
    from model.wing import cut_rib
    for z, sgn in ((RUD_Z[0], +1), (RUD_Z[1], -1)):
        sec = fin_section(z)
        cove, _ = plain_cove(sec, RUD_XH)
        xl, xu = x_end_of_plain(sec, RUD_XH)
        meshes.append(planar_cap(cut_rib(sec, cove[::-1], xl, xu), (0, 0, sgn)))
    fin = Part("fin", "Vertical stabiliser (fin)", "empennage_v", explode=(0.9, 0, 0.9),
               group="Empennage", material_note="Aluminium two-spar fin",
               info={"LE sweep": "%.0f deg" % np.degrees(np.arctan2(FIN_LE[1][0] - FIN_LE[0][0], FIN_LE[1][1] - FIN_LE[0][1])),
                     "section": "NACA 0018 (drawing VF1 / VF2)"})
    fm = Mesh.merge(meshes)
    fin.add(fm, "paint_white")
    parts[fin.id] = fin

    # rudder (single piece, two hinges) with an electric trim tab low on the trailing edge
    from model.wing import segmented_surface
    rud, rtab, (rta, rtb) = segmented_surface(fin_section, RUD_Z[0] + 0.01, RUD_Z[1] - 0.01, RUD_XH,
                                              RUD_TAB, step=0.12)
    a, b = fin_section(RUD_Z[0]), fin_section(RUD_Z[1])
    ha, hb = a.point(np.array(RUD_XH), np.array(0.0)), b.point(np.array(RUD_XH), np.array(0.0))
    ax = (hb - ha) / np.linalg.norm(hb - ha)
    rp = Part("rudder", "Rudder", "empennage_v", pivot=dict(origin=ha.tolist(), axis=ax.tolist(), kind="rudder",
                                                            range=[-25.0, 25.0]),
              explode=(1.5, 0, 0.9), group="Flight controls", material_note="Mass-balanced rudder")
    rp.add(rud, "paint_white")
    parts[rp.id] = rp
    tax = (rtb - rta) / np.linalg.norm(rtb - rta)
    tp = Part("rudder_tab", "Rudder trim tab (electric)", "empennage_v", parent="rudder",
              pivot=dict(origin=rta.tolist(), axis=tax.tolist(), kind="tab", gearing=0.0, range=[-12, 12]),
              explode=(0.3, 0, 0), group="Flight controls", material_note="Electric trim (tab location per drawing)")
    tp.add(rtab, "paint_white")
    parts[tp.id] = tp

    # dorsal fin
    zd = span_stations(2.40, float(_dorsal_curve()[-1, 1]) - 0.01, 0.06)
    dm = skin(dorsal_section, zd, n=40)            # closed trailing edge (buried in the fin)
    dp = Part("dorsal_fin", "Dorsal fin fillet", "empennage_v", explode=(0.6, 0, 0.7), group="Empennage",
              material_note="Glass-fibre fairing")
    dp.add(dm, "paint_white")
    parts[dp.id] = dp

    # ventral strakes
    parts["strakes"] = build_strakes()

    # ---------------- tailplane (one piece, trimmable) + elevators
    stab_meshes = []
    for sgn in (1, -1):
        def sec_fn(y, sgn=sgn):
            s = stab_section(abs(y))
            if sgn < 0:
                s = Section(le=s.le * [1, -1, 1], chord=s.chord, e_c=s.e_c, e_t=s.e_t, twist=s.twist,
                            airfoil=s.airfoil)
            return s
        ys0 = span_stations(0.0, ELEV_Y[0], 0.05)
        ys1 = span_stations(ELEV_Y[0], ELEV_Y[1], 0.15)
        ys2 = np.concatenate([span_stations(ELEV_Y[1], 2.30, 0.05), span_stations(2.30, STAB_TIP_Y - 0.004, 0.02)[1:]])
        ms = []
        ms.append(skin(sec_fn, ys0, n=48))
        ms.append(strip(sec_fn, ys0, 1.0, 1.0))
        xl_e, xu_e = x_end_of_plain(stab_section(1.2), ELEV_XH)
        ms.append(skin(sec_fn, ys1, x_lo_end=xl_e, x_up_end=xu_e, n=48))
        ms.append(curve_patch(sec_fn, ys1, lambda s: plain_cove(s, ELEV_XH)[0], outward_hint=lambda s: s.e_c))
        ms.append(skin(sec_fn, ys2, n=48))
        ms.append(strip(sec_fn, ys2, 1.0, 1.0))
        from model.wing import cut_rib
        for y, dsg in ((ELEV_Y[0], 1), (ELEV_Y[1], -1)):
            sec = sec_fn(y)
            cove, _ = plain_cove(sec, ELEV_XH)
            xl, xu = x_end_of_plain(sec, ELEV_XH)
            ms.append(planar_cap(cut_rib(sec, cove[::-1], xl, xu), (0, dsg * sgn, 0)))
        # rounded tip cap
        tip = sec_fn(STAB_TIP_Y - 0.004)
        xx = cos_pts(40)
        loop = np.vstack([tip.lower(xx[::-1]), tip.upper(xx[1:-1])])
        ms.append(cap_ring(loop, (0, sgn, 0)))
        m = Mesh.merge(ms)
        if sgn < 0:
            # skins built with mirrored sections have inverted orientation -> fix by normal test
            pass
        stab_meshes.append(m)
    # stabiliser pivots (variable incidence) about a spanwise axis at its rear spar
    piv = np.array([STAB_ROOT_LE + 0.62 * STAB_ROOT_C, 0.0, STAB_Z])
    sp = Part("stabilizer", "Horizontal stabiliser (variable incidence)", "empennage_h",
              pivot=dict(origin=piv.tolist(), axis=[0, 1.0, 0], kind="trim", range=[-4.0, 2.0]),
              explode=(0.9, 0, 1.5), group="Empennage", material_note="Electrically trimmed, dual actuators",
              info={"span": "5,200 mm", "root chord": f"{STAB_ROOT_C*1000:.0f} mm",
                    "LE sweep": f"{np.degrees(STAB_SWEEP):.1f} deg, horn-balanced tips (drawing)"})
    sp.add(Mesh.merge(stab_meshes), "paint_white")
    parts[sp.id] = sp

    for side, sgn in (("R", 1), ("L", -1)):
        ys = span_stations(ELEV_Y[0] + 0.012, ELEV_Y[1] - 0.012, 0.15)
        em = closed_body(stab_section, ys, lambda s: plain_surface_loop(s, ELEV_XH))
        a, b = stab_section(ELEV_Y[0]), stab_section(ELEV_Y[1])
        ha, hb = a.point(np.array(ELEV_XH), np.array(0.0)), b.point(np.array(ELEV_XH), np.array(0.0))
        if sgn < 0:
            em = em.mirrored_y()
            ha, hb = ha * [1, -1, 1], hb * [1, -1, 1]
        ax = (hb - ha) / np.linalg.norm(hb - ha) * sgn
        ep = Part(f"elevator_{side}", f"{'Right' if sgn > 0 else 'Left'} elevator", "empennage_h",
                  parent="stabilizer",
                  pivot=dict(origin=ha.tolist(), axis=ax.tolist(), kind="elevator", range=[-20.0, 15.0]),
                  explode=(0.5, sgn * 0.35, 0.0), group="Flight controls", material_note="Paired elevators")
        ep.add(em, "paint_white")
        parts[ep.id] = ep

    # bullet fairing
    parts["tail_bullet"] = build_bullet()
    return parts


def fix_orient(m: Mesh, zc):
    """Stabiliser skins: normals must point away from the chord plane."""
    up = m.V[:, 2] - zc
    # only correct patches where most normals point inward: approximate per-face test
    fn = m.face_normals()
    ctr = m.V[m.F].mean(1)
    s = np.sign(ctr[:, 2] - zc) * fn[:, 2]
    # flip faces whose normal points toward the chord plane on thick regions
    bad = s < -0.3
    if bad.mean() > 0.3:
        m = m.flipped()
    return m


def build_bullet():
    """Bullet fairing lofted through the elliptic sections of BULLET (drawing side view + plan)."""
    T = np.array(BULLET)
    xs = np.unique(np.concatenate([np.linspace(T[0, 0], T[-1, 0], 60), T[:, 0]]))
    rows = [bullet_section(x) for x in xs[1:]]
    P = np.array(rows)
    m = grid_surface(P, close_v=True)
    cen = P.mean(1)
    if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
        m = m.flipped()
    nose = np.array([T[0, 0], 0.0, T[0, 1]])
    # nose fan and aft end cap
    n = P.shape[1]
    V = np.vstack([P[0], nose[None]])
    k = np.arange(n)
    fan = Mesh(V, np.stack([np.full(n, n), (k + 1) % n, k], 1))
    if np.dot(fan.face_normals().mean(0), [-1, 0, 0]) < 0:
        fan = fan.flipped()
    m = Mesh.merge([m, fan, cap_ring(P[-1], (1, 0, 0))])
    p = Part("tail_bullet", "Fin / tailplane bullet fairing", "empennage_h", explode=(1.2, 0, 1.9),
             group="Empennage", material_note="Composite fairing, tail nav/strobe light")
    p.add(m, "paint_white")
    return p


def build_strakes():
    """Two canted ventral strakes: thin plates between the root line (on the tail-cone side) and the tip line."""
    ms = []
    (r0x, _), (r1x, _) = STRAKE_ROOT
    xs = np.linspace(r0x + 0.01, r1x - 0.005, 40)
    for sgn in (1, -1):
        rows = []
        for x in xs:
            fr = strake_frame(x)
            if fr is None:
                continue
            r, t = fr
            d = t - r
            L = max(np.linalg.norm(d), 1e-4)
            u = d / L
            nrm = np.array([0.0, u[2], -u[1]])          # plate normal (in the cross-section plane)
            ss = np.linspace(0, 1, 8)
            h = 0.5 * STRAKE_T * np.minimum(1.0, 6 * np.minimum(ss, 1 - ss) + 0.15) * min(1.0, L / 0.05)
            a = r[None] + ss[:, None] * d[None] + h[:, None] * nrm[None]
            b = (r[None] + ss[:, None] * d[None] - h[:, None] * nrm[None])[::-1]
            ring = np.vstack([a, b[1:-1]]) if len(a) > 2 else np.vstack([a, b])
            if sgn < 0:
                ring = ring * [1, -1, 1]
            rows.append(ring)
        P = np.array(rows)
        m = grid_surface(P, close_v=True)
        cen = P.mean(1)
        if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
            m = m.flipped()
        ms.append(Mesh.merge([m, cap_ring(P[0], (-1, 0, 0)), cap_ring(P[-1], (1, 0, 0))]))
    p = Part("strakes", "Ventral strakes (2)", "empennage_v", explode=(0.6, 0, -0.8), group="Empennage",
             qty=2, material_note="Kevlar / honeycomb sandwich")
    p.add(Mesh.merge(ms), "paint_white")
    return p
