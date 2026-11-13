"""
SF50 empennage: V-tail (38 deg dihedral, 4.48 m tip to tip) with ruddervators and their pitch servo / trim tabs,
de-ice boots, tip caps and static wicks; two ventral fins (strakes) with the yaw-SAS surfaces at their aft end
(AOPA: "Two small surfaces located on the aft end of the strakes below the ruddervators are moved automatically").
"""
from __future__ import annotations
import numpy as np

from sf50_kernel import (Mesh, trim, planar_cap, cap_ring, grid_surface, cylinder, Section, skin, strip,
                         curve_patch, closed_body, cos_pts, naca00, Part)
import sf50_geom as G
from sf50_wing import plain_cove, plain_surface_loop, tab_loop, x_end_of_plain, cut_rib, span_stations, segmented_surface

VT_AF = naca00(0.10, closed_te=True)
VF_AF = naca00(0.08, closed_te=True)
GAP = 0.008


def vt_frame(sgn=1):
    G_ = G.VT_DIHEDRAL
    e_s = np.array([0.0, sgn * np.cos(G_), np.sin(G_)])
    e_t = np.array([0.0, -sgn * np.sin(G_), np.cos(G_)])     # "upper" side = up / inboard
    return e_s, e_t


def vt_section(s, sgn=1):
    """V-tail section at span s (m along the surface from the root reference point)."""
    e_s, e_t = vt_frame(sgn)
    f = s / G.VT_S_TIP
    x_le = G.VT_LE_ROOT + (G.VT_LE_TIP - G.VT_LE_ROOT) * f
    x_te = G.VT_TE_ROOT + (G.VT_TE_TIP - G.VT_TE_ROOT) * f
    le = np.array([x_le, sgn * G.VT_ROOT_Y, G.VT_ROOT_Z]) + s * e_s
    if sgn < 0:
        e_t = -e_t * -1      # keep 'upper' = up/inboard on both sides
    return Section(le=le, chord=x_te - x_le, e_c=np.array([1.0, 0, 0]), e_t=e_t, twist=0.0, airfoil=VT_AF, pivot_frac=0.0)


def vt_tip(sgn, n_span=8, n_loop=48):
    s0 = G.VT_S_TIP
    sec = vt_section(s0, sgn)
    e_s, e_t = vt_frame(sgn)
    rows = []
    for u in np.sin(np.linspace(0, np.pi / 2, n_span)):
        k = np.sqrt(max(1 - u * u, 0.0))
        xs = cos_pts(n_loop // 2 + 1)
        lo = np.stack([xs[::-1], -VT_AF._t(xs[::-1]) * (0.15 + 0.85 * k)], 1)
        up = np.stack([xs[1:], VT_AF._t(xs[1:]) * (0.15 + 0.85 * k)], 1)
        loop = np.vstack([lo, up])
        c = sec.chord * (1 - 0.30 * (1 - k))
        x0 = sec.le[0] + sec.chord * 0.24 * (1 - k)
        base = sec.le + 0.035 * u * e_s
        P = np.array([[x0 + a * c, 0, 0] for a, b in loop])
        P = base[None, :] * [0, 1, 1] + P + (loop[:, 1:2] * c) * e_t[None, :]
        rows.append(P)
    P = np.array(rows)
    m = grid_surface(P)
    cen = P.mean(1)
    rad = (P - cen[:, None, :]).reshape(-1, 3)
    if np.mean(np.sum(rad * m.N[:len(rad)], 1)) < 0:
        m = m.flipped()
    return Mesh.merge([m, cap_ring(P[-1], e_s)])


def build(parts):
    for side, sgn in (("L", -1), ("R", 1)):
        fn = lambda s, sg=sgn: vt_section(s, sg)
        s_in = -0.14
        sk, other = [], []
        ss = span_stations(s_in, G.RV_S[0], 0.06)
        sk.append(skin(fn, ss, n=56))
        ss = span_stations(G.RV_S[0], G.RV_S[1], 0.12)
        xl, xu = x_end_of_plain(fn(1.0), G.RV_XH)
        sk.append(skin(fn, ss, x_lo_end=xl, x_up_end=xu, n=56))
        other.append(curve_patch(fn, ss, lambda sec: plain_cove(sec, G.RV_XH)[0], outward_hint=lambda sec: sec.e_c))
        ss = span_stations(G.RV_S[1], G.VT_S_TIP, 0.05)
        sk.append(skin(fn, ss, n=56))
        for s, sg in ((G.RV_S[0], 1), (G.RV_S[1], -1)):
            sec = fn(s)
            cove, _ = plain_cove(sec, G.RV_XH)
            a, b = x_end_of_plain(sec, G.RV_XH)
            e_s, _ = vt_frame(sgn)
            other.append(planar_cap(cut_rib(sec, cove[::-1], a, b), sg * e_s))
        # de-ice boots on the leading edge (AFM 'Stabilizer Deicers', AOPA 'Pneumatic deice boots') [inf: extent]
        boots, rests = [], []
        for m in sk:
            uvx, sv = m.UV[:, 1], m.UV[:, 0]
            fb = np.maximum(np.abs(uvx) - 0.07, np.maximum(0.05 - sv, sv - (G.VT_S_TIP - 0.05)))
            if (fb < 0).any():
                boots.append(trim(m, fb, "negative").offset(0.0012))
            rests.append(trim(m, fb, "positive") if (fb < 0).any() else m)
        rest = Mesh.merge(rests + other)
        boot = Mesh.merge(boots)
        f_in = lambda mm: G.inside_fuselage(mm.V)
        rest = trim(rest, f_in(rest), "positive")
        boot = trim(boot, f_in(boot), "positive")
        tip = vt_tip(sgn)
        p = Part(f"vtail_{side}", f"V-tail surface, {'left' if sgn < 0 else 'right'}", "empennage", group="Empennage",
                 material_note="Carbon composite stabiliser",
                 info={"dihedral": f"{np.degrees(G.VT_DIHEDRAL):.0f} deg [inf: AFM Fig 1-1 front view]",
                       "span (tip to tip)": f"{G.VTAIL_SPAN:.3f} m (AFM Fig 1-1, 14.7 ft)", "section": "NACA 0010 [inf]"})
        p.add(rest, "paint_white").add(boot, "deice_boot").add(tip, "paint_white")
        parts[p.id] = p
        # ruddervator with pitch servo / trim tab (AFM 'Ruddervators, Pitch Servo Tabs'; TCDS trim UP 7 / DOWN 18)
        body, tabm, (ta, tb) = segmented_surface(fn, G.RV_S[0] + GAP, G.RV_S[1] - GAP, G.RV_XH,
                                                 (G.RV_S[0] + 0.10, G.RV_S[0] + 0.85, 0.90), step=0.12)
        a, b = fn(G.RV_S[0]), fn(G.RV_S[1])
        ha = a.point(np.array(G.RV_XH), np.array(0.0))
        hb = b.point(np.array(G.RV_XH), np.array(0.0))
        axis = (hb - ha) / np.linalg.norm(hb - ha)
        # positive rotation = trailing edge toward the lower (outboard-down) side: about e_s on the right, -e_s on the left
        axis = axis * (1 if sgn > 0 else -1)
        rv = Part(f"ruddervator_{side}", f"Ruddervator, {'left' if sgn < 0 else 'right'}", "empennage",
                  pivot=dict(origin=ha.tolist(), axis=axis.tolist(), kind="ruddervator", range=[-20.0, 15.0],
                             pitchRange=[-20.0, 15.0], side=sgn, yawGain=9.0),
                  group="Flight controls", material_note="Aluminium, mass balanced",
                  info={"travel": "pitch UP 20 / DOWN 15 deg, yaw +-9 deg (FAA TCDS A00018CH)",
                        "mixing": "deflection = pitch term + side x yaw term (TE down positive) [inf: mixing law]"})
        rv.add(body, "paint_white")
        wicks = []
        for s in (G.RV_S[0] + 0.9, G.RV_S[1] - 0.45):
            sec = fn(s)
            te = sec.point(np.array(0.995), np.array(0.0))
            wicks.append(cylinder(te, te + [0.06, 0, -0.01], 0.0035, n=6))   # static wicks (AFM 'Static Wicks')
        rv.add(Mesh.merge(wicks), "black")
        parts[rv.id] = rv
        tax = (tb - ta) / np.linalg.norm(tb - ta) * (1 if sgn > 0 else -1)
        tp = Part(f"rv_tab_{side}", f"Ruddervator pitch servo / trim tab, {'left' if sgn < 0 else 'right'}", "empennage",
                  parent=rv.id, pivot=dict(origin=ta.tolist(), axis=tax.tolist(), kind="tab", gearing=-0.4,
                                           range=[-7.0, 18.0]),
                  group="Flight controls",
                  material_note="Pitch servo tab with trim (TCDS ruddervator trim UP 7 / DOWN 18 deg; + = trailing edge down, "
                                "the convention of every surface here, so range [-7, +18]; fix round 1: it was inverted) "
                                "[inf: gearing -0.4, opposite to the ruddervator as a servo tab moves]")
        tp.add(tabm, "paint_white")
        parts[tp.id] = tp
    build_ventral(parts)


# ------------------------------------------------------------------------------------------------ ventral fins
VF_CANT = np.radians(40.0)          # from vertical, outward [inf: AFM Fig 1-1 side view projection]
VF_ROOT = (0.0, 1.615)              # (y, z) of the span origin, inside the tail cone
VF_S = (0.30, 0.62)                 # visible span range along the fin
VF_LE = [(0.30, 8.05), (0.45, 8.15), (0.62, 9.40)]
VF_TE = 9.935
SAS_XH = 9.66                       # yaw-SAS hinge station [inf]


def vf_frame(sgn):
    e_s = np.array([0.0, sgn * np.sin(VF_CANT), -np.cos(VF_CANT)])
    e_t = np.array([0.0, sgn * np.cos(VF_CANT), np.sin(VF_CANT)])
    return e_s, e_t


def vf_section(s, sgn):
    e_s, e_t = vf_frame(sgn)
    xs, xl = zip(*VF_LE)
    x_le = float(np.interp(s, xs, xl))
    le = np.array([x_le, sgn * VF_ROOT[0], VF_ROOT[1]]) + s * e_s
    return Section(le=le, chord=VF_TE - x_le, e_c=np.array([1.0, 0, 0]), e_t=e_t, twist=0.0, airfoil=VF_AF,
                   pivot_frac=0.0)


def build_ventral(parts):
    for side, sgn in (("L", -1), ("R", 1)):
        fn = lambda s, sg=sgn: vf_section(s, sg)
        ss = np.r_[np.linspace(0.20, VF_S[0], 4)[:-1], span_stations(VF_S[0], VF_S[1] - 0.01, 0.025)]
        e_s, e_t = vf_frame(sgn)

        def xh_frac(sec):
            return np.clip((SAS_XH - sec.le[0]) / sec.chord, 0.3, 0.95)
        # fixed fin: everything forward of the SAS hinge on the outer part, full chord inboard of it
        s_sas = (0.47, VF_S[1] - 0.012)
        fixed = [skin(fn, np.linspace(0.20, s_sas[0], 12), n=40)]
        ss2 = np.linspace(s_sas[0], s_sas[1], 7)
        fixed.append(skin(lambda s: fn(s), ss2, x_lo_end=0.70, x_up_end=0.70, n=40))
        fixed.append(strip(fn, ss2, 0.70, 0.70))
        fixed.append(skin(fn, np.linspace(s_sas[1], VF_S[1], 3), n=40))
        tipsec = fn(VF_S[1])
        xs = cos_pts(21)
        loop = np.vstack([np.stack([xs[::-1], VF_AF.lower(xs[::-1])], 1), np.stack([xs[1:], VF_AF.upper(xs[1:])], 1)])
        fixed.append(planar_cap(tipsec.point(loop[:, 0], loop[:, 1]), e_s))
        m = Mesh.merge(fixed)
        m = trim(m, G.inside_fuselage(m.V), "positive")
        p = Part(f"ventral_fin_{side}", f"Ventral fin (strake), {'left' if sgn < 0 else 'right'}", "empennage",
                 group="Empennage", material_note="AFM walk-around 'Ventral Fins' [inf: shape, cant]")
        p.add(m, "paint_white")
        parts[p.id] = p
        # yaw-SAS surface (TCDS 'Yaw SAS UP 15 / DOWN 15 deg')
        sas = closed_body(fn, np.linspace(s_sas[0] + 0.006, s_sas[1] - 0.006, 6),
                          lambda sec: np.vstack([np.stack([np.linspace(0.705, 1.0, 10), VF_AF.upper(np.linspace(0.705, 1.0, 10))], 1),
                                                 np.stack([np.linspace(1.0, 0.705, 10)[1:-1], VF_AF.lower(np.linspace(1.0, 0.705, 10)[1:-1])], 1)]))
        a, b = fn(s_sas[0]), fn(s_sas[1])
        ha = a.point(np.array(0.705), np.array(0.0))
        hb = b.point(np.array(0.705), np.array(0.0))
        # TE to starboard for yaw right on both fins: axis points from the tip toward the root (see build notes)
        axis = (ha - hb) / np.linalg.norm(ha - hb)
        sp = Part(f"yaw_sas_{side}", f"Yaw-SAS surface, {'left' if sgn < 0 else 'right'} ventral fin", "empennage",
                  pivot=dict(origin=ha.tolist(), axis=axis.tolist(), kind="rudder", range=[-15.0, 15.0], role="yaw_sas"),
                  group="Flight controls", material_note="Servo-driven yaw stability augmentation surface (AOPA, TCDS)")
        sp.add(sas, "paint_white")
        parts[sp.id] = sp
