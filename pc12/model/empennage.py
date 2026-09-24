"""
PC-12 T-tail: swept fin with enlarged dorsal fillet, rudder, trimmable
(variable-incidence) tailplane with paired elevators and swept tips, fin/tailplane
bullet fairing, and twin ventral strakes.

Anchors: tailplane span 5.20 m (Pilatus), overall height 4.26 m (top of bullet),
overall length 14.40 m (spinner tip STA 0.39 -> aft-most point STA 14.79).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, grid_surface, planar_cap, revolve, cap_ring, trim
from model.airfoil import naca00
from model.lifting import Section, skin, strip, curve_patch, closed_body, cos_pts
from model.wing import plain_cove, plain_surface_loop, x_end_of_plain, span_stations
from model.parts import Part
from model import fuselage as F

# ---------------------------------------------------------------- fin
FIN_Z0, FIN_Z1 = 2.00, 4.07            # root (buried in the tail cone) / tip (in the bullet)
FIN_LE = ((11.85, 2.35), (13.22, 4.07))
FIN_TE = ((14.40, 2.10), (14.70, 4.07))
RUD_Z = (2.26, 3.96)
RUD_XH = 0.64                           # hinge at 64 % local chord
FIN_AF_ROOT, FIN_AF_TIP = naca00(0.13), naca00(0.10)


def _lin(p, q, z):
    return p[0] + (q[0] - p[0]) * (z - p[1]) / (q[1] - p[1])


def fin_section(z):
    xl = _lin(*FIN_LE, z)
    xt = _lin(*FIN_TE, z)
    w = np.clip((z - FIN_Z0) / (FIN_Z1 - FIN_Z0), 0, 1)
    af = FIN_AF_ROOT.blend(FIN_AF_TIP, w)
    return Section(le=np.array([xl, 0.0, z]), chord=xt - xl, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=af)


# ---------------------------------------------------------------- tailplane
STAB_Z = 4.125
STAB_ROOT_LE = 13.36
STAB_ROOT_C = 1.22
STAB_SWEEP = np.radians(14.0)
STAB_TIP_Y = 2.60                      # 5.20 m span
STAB_TAPER_C = 0.74                    # chord at y = 2.30 before the swept tip
ELEV_Y = (0.155, 2.40)
ELEV_XH = 0.70
STAB_INC = np.radians(-1.0)
STAB_AF = naca00(0.11)


def stab_le(y):
    y = abs(y)
    base = STAB_ROOT_LE + y * np.tan(STAB_SWEEP)
    k = np.clip((y - 2.22) / (STAB_TIP_Y - 2.22), 0, 1)
    return base + 0.30 * k ** 2


def stab_te(y):
    y = abs(y)
    c_lin = STAB_ROOT_C + (STAB_TAPER_C - STAB_ROOT_C) * min(y, 2.30) / 2.30
    te_lin = STAB_ROOT_LE + min(y, 2.30) * np.tan(STAB_SWEEP) + c_lin
    k = np.clip((y - 2.30) / (STAB_TIP_Y - 2.30), 0, 1)
    return te_lin + 0.06 * k


def stab_section(y):
    xl, xt = stab_le(y), stab_te(y)
    c = max(xt - xl, 0.02)
    return Section(le=np.array([xl, y, STAB_Z]), chord=c, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 0, 1.0]), twist=STAB_INC, airfoil=STAB_AF)


# ---------------------------------------------------------------- dorsal fin
def dorsal_section(z):
    # leading edge: concave curve from the fuselage crown at STA 10.45 up to the fin LE
    z0, z1 = 2.50, 3.05
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    x_start = 10.35 + (12.10 - 10.35) * (1 - (1 - t) ** 2.2)
    x_end = _lin(*FIN_LE, z) + 0.45
    af = naca00(0.055 + 0.03 * t)
    return Section(le=np.array([x_start, 0.0, z]), chord=x_end - x_start, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=af)


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
                     "section": "NACA 0013 -> 0010 (est.)"})
    fm = Mesh.merge(meshes)
    fin.add(fm, "paint_white")
    parts[fin.id] = fin

    # rudder (single piece, two hinges) with an electric trim tab low on the trailing edge
    from model.wing import segmented_surface
    rud, rtab, (rta, rtb) = segmented_surface(fin_section, RUD_Z[0] + 0.01, RUD_Z[1] - 0.01, RUD_XH,
                                              (2.36, 2.86, 0.915), step=0.12)
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
              explode=(0.3, 0, 0), group="Flight controls", material_note="Electric trim (tab location est.)")
    tp.add(rtab, "paint_white")
    parts[tp.id] = tp

    # dorsal fin
    zd = span_stations(2.28, 3.05, 0.06)
    dm = Mesh.merge([skin(dorsal_section, zd, n=40), strip(dorsal_section, zd, 1.0, 1.0)])
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
                    "LE sweep": "14 deg + raked tips (est.)"})
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
    L0, L1 = 12.95, 14.79
    zc = 4.26 - 0.135
    prof = []
    for t in np.linspace(0, 1, 40):
        x = L0 + (L1 - L0) * t
        # ogive nose, cylindrical middle, cone tail
        if t < 0.35:
            r = 0.135 * np.sqrt(1 - ((0.35 - t) / 0.35) ** 2)
        elif t < 0.72:
            r = 0.135
        else:
            u = (t - 0.72) / 0.28
            r = 0.135 * (1 - u ** 1.6) + 0.012 * u
        prof.append((x - L0, r))
    prof[0] = (0.0, 0.0)
    m = revolve(prof, n=36, axis_origin=(L0, 0, zc), axis_dir=(1, 0, 0), cap_ends=True)
    p = Part("tail_bullet", "Fin / tailplane bullet fairing", "empennage_h", explode=(1.2, 0, 1.9),
             group="Empennage", material_note="Composite fairing, tail nav/strobe light")
    p.add(m, "paint_white")
    return p


def build_strakes():
    ms = []
    for sgn in (1, -1):
        cant = np.radians(38.0)
        def sec(s, sgn=sgn):
            # s: 0 at root (on skin) -> 1 at tip; chord runs aft along x
            x0 = 12.35 + 0.35 * s
            x1 = 13.75 - 0.10 * s
            xm = 0.5 * (x0 + x1)
            yb = sgn * 0.13
            zb = float(F.z_bot(xm)) + 0.05
            depth = 0.26
            y = yb + sgn * depth * s * np.sin(cant)
            z = zb - depth * s * np.cos(cant)
            e_t = np.array([0.0, np.cos(cant), np.sin(cant) * sgn])
            e_t = e_t / np.linalg.norm(e_t)
            return Section(le=np.array([x0, y, z]), chord=x1 - x0, e_c=np.array([1.0, 0, 0]),
                           e_t=e_t, twist=0.0, airfoil=naca00(0.04))
        ss = np.linspace(0, 1, 6)
        m = Mesh.merge([skin(sec, ss, n=24), strip(sec, ss, 1.0, 1.0)])
        last = sec(1.0)
        xx = cos_pts(24)
        loop = np.vstack([last.lower(xx[::-1]), last.upper(xx[1:-1])])
        m = Mesh.merge([m, cap_ring(loop, np.array([0, sgn * np.sin(cant), -np.cos(cant)]))])
        ms.append(m)
    p = Part("strakes", "Ventral strakes (2)", "empennage_v", explode=(0.6, 0, -0.8), group="Empennage",
             qty=2, material_note="Kevlar / honeycomb sandwich")
    p.add(Mesh.merge(ms), "paint_white")
    return p
