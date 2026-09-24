"""
External details: wing-to-body belly fairing, flap-track canoes, weather-radar
pod (right wing, standard on PC-12s), navigation/strobe/beacon lights,
antennas, pitot-static probes and static dischargers.
"""
from __future__ import annotations
import numpy as np

from cad.mesh import (Mesh, grid_surface, revolve, cylinder, superellipsoid, sweep_tube, cap_ring,
                      rotation_matrix, box)
from model.airfoil import naca00
from model.lifting import Section, skin, strip, cos_pts
from model.parts import Part
from model import wing as W
from model import fuselage as F
from model import empennage as E


def belly_fairing():
    xs = np.linspace(4.92, 8.30, 40)
    wk = [(4.92, 0.26), (5.35, 0.60), (6.2, 0.71), (7.2, 0.64), (7.9, 0.38), (8.30, 0.10)]
    bk = [(4.92, 0.805), (5.35, 0.752), (6.2, 0.735), (7.2, 0.748), (7.9, 0.79), (8.30, 0.805)]
    from cad.mesh import pchip
    wf, bf = pchip(*zip(*wk)), pchip(*zip(*bk))
    ts = np.linspace(0, 1, 72, endpoint=False)
    rows = []
    for x in xs:
        w, b = float(wf(x)), float(bf(x))
        zc = 0.99
        h = zc - b
        a = 2 * np.pi * ts
        n = 3.2
        y = w * np.sign(np.sin(a)) * np.abs(np.sin(a)) ** (2 / n)
        z = zc + h * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** (2 / n)
        rows.append(np.stack([np.full_like(y, x), y, z], 1))
    P = np.array(rows)
    m = grid_surface(P, close_v=True)
    cen = P.mean(1)
    if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
        m = m.flipped()
    m = Mesh.merge([m, cap_ring(P[0], (-1, 0, 0)), cap_ring(P[-1], (1, 0, 0))])
    return m


def teardrop(x0, length, depth, half_w, n=28, m=24):
    """Streamlined canoe body along +x from x0 (profile: max depth at 30 %)."""
    t = np.linspace(0, 1, n)
    r = depth * (2.2 * np.sqrt(t) * (1 - t) ** 1.25)
    r[0] = 0
    r[-1] = 0
    prof = list(zip(t * length, r))
    mm = revolve(prof, n=m, axis_origin=(x0, 0, 0), axis_dir=(1, 0, 0))
    return mm.scaled((1.0, half_w / depth, 1.0), origin=(x0, 0, 0))


def flap_canoes():
    out = []
    for y in (1.55, 3.30, 5.15):
        sec = W.section_at(y)
        x0 = sec.le[0] + 0.55 * sec.chord
        L = 0.60 * sec.chord
        c = teardrop(0.0, L, 0.115, 0.05)
        # place: axis slightly below the local lower surface
        zl = float(sec.lower(np.array(0.75))[2])
        c = c.translated((x0, y, zl - 0.005))
        for s in (1, -1):
            out.append(c if s > 0 else c.mirrored_y())
    return Mesh.merge(out)


def radar_pod():
    y = 3.90
    sec = W.section_at(y)
    zc = float(sec.camber_pt(np.array(0.12))[2])
    # PRO: Garmin GWX 8000 with a 12-in antenna -> radome slightly enlarged (Skies Mag)
    RP = 0.175
    x_tip = sec.le[0] - 0.46
    L = 1.18
    prof = []
    for t in np.linspace(0, 1, 36):
        if t < 0.40:
            r = RP * max(0.0, 1 - (1 - t / 0.40) ** 2) ** 0.5
        elif t < 0.85:
            r = RP
        else:
            r = RP * max(0.0, 1 - ((t - 0.85) / 0.15) ** 2) ** 0.5
        prof.append((t * L, r))
    prof[0] = (0.0, 0.0)
    body = revolve(prof, n=40, axis_origin=(x_tip, y, zc), axis_dir=(1, 0, 0))
    radome = trim_x(body, x_tip + 0.42, keep_less=True)
    rest = trim_x(body, x_tip + 0.42, keep_less=False)
    return radome, rest


def trim_x(m, x, keep_less=True):
    from cad.mesh import trim
    f = m.V[:, 0] - x
    return trim(m, f, "negative" if keep_less else "positive")


def lens(center, radii, R=None):
    return superellipsoid(center, radii, (0.9, 0.9), nu=12, nv=16, R=R)


def blade_antenna(base, height, chord, sweep_deg=35, down=False, thick=0.10):
    s = -1 if down else 1

    def sec(u):
        z = base[2] + s * height * u
        c = chord * (1 - 0.55 * u)
        xl = base[0] + height * u * np.tan(np.radians(sweep_deg))
        return Section(le=np.array([xl, base[1], z]), chord=c, e_c=np.array([1.0, 0, 0]),
                       e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=naca00(thick))
    us = np.linspace(0, 1, 6)
    m = Mesh.merge([skin(sec, us, n=14), strip(sec, us, 1.0, 1.0)])
    last = sec(1.0)
    xx = cos_pts(14)
    loop = np.vstack([last.lower(xx[::-1]), last.upper(xx[1:-1])])
    return Mesh.merge([m, cap_ring(loop, (0, 0, s))])


def build(parts):
    # -------- belly fairing (goes with the wing)
    bp = Part("belly_fairing", "Wing-to-body belly fairing", "wing", explode=(0, 0, -0.9), group="Wing",
              material_note="Composite fairing over the wing carry-through")
    bp.add(belly_fairing(), "paint_white")
    parts[bp.id] = bp

    # -------- flap track canoes
    cp = Part("flap_fairings", "Flap-track fairings (3 per side)", "controls_wing", explode=(0.4, 0, -0.5),
              group="Flight controls", qty=6, material_note="Composite canoe fairings")
    cp.add(flap_canoes(), "paint_white")
    parts[cp.id] = cp

    # -------- weather radar pod (right wing)
    radome, body = radar_pod()
    rp = Part("radar_pod", "Weather-radar pod, right wing (GWX 8000, 12-in antenna)", "details",
              explode=(-0.7, 0.3, 0), group="Avionics", material_note="Radome enlarged on the PRO")
    rp.add(body, "paint_white").add(radome, "paint_belly")
    parts[rp.id] = rp

    # -------- lights
    lights = []
    reds, greens, whites = [], [], []
    tip_sec = W.section_at(W.SEMI)
    for sgn, coll in ((1, greens), (-1, reds)):
        c = tip_sec.le + np.array([0.06, 0, 0])
        c = c * [1, sgn, 1]
        coll.append(lens(c + [0, sgn * -0.03, 0.02], (0.07, 0.03, 0.028)))
        # strobe (white) at the winglet trailing edge root
        whites.append(lens(np.array([tip_sec.le[0] + tip_sec.chord - 0.02, sgn * (W.SEMI + 0.02), tip_sec.le[2] + 0.05]),
                           (0.05, 0.02, 0.025)))
    whites.append(lens(np.array([14.772, 0, 4.125]), (0.018, 0.016, 0.016)))         # tail light (in the bullet tip)
    reds.append(lens(np.array([13.07, 0, 4.192]), (0.045, 0.03, 0.02)))              # beacon on bullet nose
    reds.append(lens(np.array([7.40, 0, 0.738]), (0.05, 0.035, 0.022)))             # lower beacon
    lp = Part("lights", "Navigation, strobe & beacon lights", "details", group="Lights",
              material_note="LED nav/strobe, red beacons")
    lp.add(Mesh.merge(reds), "light_red").add(Mesh.merge(greens), "light_green").add(Mesh.merge(whites), "light_white")
    parts[lp.id] = lp

    # -------- antennas
    ants = []
    top = lambda x: float(F.z_top(x)) - 0.004
    bot = lambda x: float(F.z_bot(x)) + 0.004
    ants.append(blade_antenna((5.25, 0, top(5.25)), 0.26, 0.20, 38))            # VHF COM 1
    ants.append(blade_antenna((9.05, 0, top(9.05)), 0.20, 0.16, 38))            # ELT / SATCOM
    ants.append(blade_antenna((8.95, 0, bot(8.95)), 0.24, 0.18, 38, down=True))  # VHF COM 2
    ants.append(blade_antenna((8.35, 0, bot(8.35)), 0.10, 0.10, 20, down=True))  # transponder
    ants.append(blade_antenna((8.60, 0, bot(8.60)), 0.10, 0.10, 20, down=True))  # DME
    domes = [superellipsoid((4.70, 0, top(4.70) - 0.01), (0.09, 0.07, 0.035), (0.8, 0.9), 10, 14),
             superellipsoid((4.98, 0, top(4.98) - 0.01), (0.09, 0.07, 0.035), (0.8, 0.9), 10, 14),
             superellipsoid((9.45, 0, top(9.45) - 0.01), (0.07, 0.05, 0.03), (0.8, 0.9), 10, 14)]
    ap = Part("antennas", "Antennas (VHF, GPS, XPDR, DME, ELT)", "details", group="Avionics",
              material_note="Blade & patch antennas")
    ap.add(Mesh.merge(ants), "paint_white").add(Mesh.merge(domes), "paint_belly")
    parts[ap.id] = ap

    # -------- pitot-static probes (both wings)
    pit = []
    for sgn in (1, -1):
        y = 5.05 * sgn
        sec = W.section_at(abs(y))
        xm = sec.le[0] + 0.22 * sec.chord
        zl = float(sec.lower(np.array(0.22))[2])
        mast = blade_antenna((xm, y, zl + 0.01), 0.14, 0.12, 25, down=True, thick=0.14)
        tube = cylinder((xm - 0.26, y, zl - 0.125), (xm + 0.07, y, zl - 0.125), 0.011, n=12)
        tip = revolve([(0, 0.0), (0.04, 0.011)], n=12, axis_origin=(xm - 0.30, y, zl - 0.125), axis_dir=(1, 0, 0))
        pit += [mast, tube, tip]
    pp = Part("pitot", "Pitot-static probes (heated, L & R)", "details", group="Avionics",
              material_note="Heated probes")
    pp.add(Mesh.merge(pit), "chrome")
    parts[pp.id] = pp

    # -------- static dischargers on moving surfaces (move with them)
    def wick(p, d=(1, 0, 0), L=0.08):
        p = np.asarray(p, float)
        d = np.asarray(d, float)
        return cylinder(p - 0.02 * d, p + L * d, 0.0035, n=6)

    for side, sgn in (("R", 1), ("L", -1)):
        # ailerons
        ws = []
        for y in np.linspace(W.Y_AIL[0] + 0.4, W.Y_AIL[1] - 0.15, 2):
            s = W.section_at(y)
            ws.append(wick(s.point(np.array(0.995), np.array(0.0)) * [1, sgn, 1]))
        parts[f"aileron_{side}"].add(Mesh.merge(ws), "black")
        # elevators
        ws = []
        for y in (0.9, 1.6, 2.25):
            s = E.stab_section(y)
            ws.append(wick(s.point(np.array(0.995), np.array(0.0)) * [1, sgn, 1]))
        parts[f"elevator_{side}"].add(Mesh.merge(ws), "black")
        # winglet top
        from model.wing import winglet_path
        arr, seg = winglet_path()
        yb, zb, _ = arr[-1]
        tip_te = W.section_at(W.SEMI).le[0] + W.C_TIP + W.WL_TE_SWEEP
        ws = [wick((tip_te - 0.01, sgn * yb, zb - 0.03))]
        parts[f"winglet_{side}"].add(Mesh.merge(ws), "black")
    ws = []
    for z in (2.9, 3.6):
        s = E.fin_section(z)
        ws.append(wick(s.point(np.array(0.995), np.array(0.0))))
    parts["rudder"].add(Mesh.merge(ws), "black")
    return parts
