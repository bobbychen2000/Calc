"""
SF50 powerplant installation: Williams FJ33-5A in a dorsal nacelle "nestled in the V" (AOPA), bleed-air heated inlet
lip (AOPA: "Bleed air warms the engine inlet"), fan (spin pivot), mixed-flow exhaust nozzle with plug, inlet diverter,
pylon NACA inlets and louver (AFM walk-around 'Pylon NACA Inlet', 'Pylon Louver'), exhaust tray on the tail cone.
Engine envelope: FAA TCDS E3GL (length 42.7 in, height 25.1 in, forward flange OD 18.4 in).
"""
from __future__ import annotations
import numpy as np

from sf50_kernel import Mesh, grid_surface, trim, revolve, disk, superellipsoid, box, cylinder, planar_cap, Part
import sf50_geom as G
import sf50_fuselage as FU

N_PHI = 112
FAN_X = 6.205
FAN_ZC = 2.362
FAN_R = 0.205          # [inf: inside the 18.4 in (0.467 m) fan-case flange of TCDS E3GL]
INNER_LIP = (0.272, 0.128)
ENG_AXIS = np.array([np.cos(np.radians(4.0)), 0.0, -np.sin(np.radians(4.0))])   # [inf: follows the nacelle centre line]


def _dirs(n_exp, phis):
    c, s = np.cos(phis), np.sin(phis)
    return np.sign(c) * np.abs(c) ** (2.0 / n_exp), np.sign(s) * np.abs(s) ** (2.0 / n_exp)


# Cowl cross-section (fix round 1 of Phase 3a; before: one super-ellipse tube lying on the spine, inlet the size of the
# tube). AFM Fig 8-1 isometric and the Cirrus product-page photos show a raised, D-shaped polished inlet lip ahead of a
# fuller cowl whose lower flanks fair down into the fuselage. Kept: the AFM Fig 1-1 side top line and plan width (the
# section's upper half and its half-width at the centre line are G.nac_* as before). Changed [inf: shapes]:
#   - lower half: a flatter D (super-ellipse exponent NAC_N_BOT) at the inlet, blending aft into concave FILLETS that leave
#     the cowl side vertically and meet the fuselage crown tangentially FILLET_W outboard of the cowl side;
#   - a WAIST just behind the inlet highlight, so the polished lip ring stands proud of the cowl;
#   - the inlet opening (inner lip) is a D: flat bottom (exponent INNER_N_BOT).
NAC_N_BOT = 3.6
INNER_N_BOT = 5.0
FILLET = [(5.98, 0.0), (6.10, 0.0), (6.40, 0.13), (7.30, 0.13), (7.80, 0.09), (8.01, 0.07)]   # (FS, fillet width m) [inf]
WAIST = dict(x=6.03, w=0.07, depth=0.085)    # relative dip of the outer contour behind the highlight [inf]


def fillet_w(x):
    xs, ws = zip(*FILLET)
    return float(np.interp(x, xs, ws))


def waist(x):
    return 1.0 - WAIST["depth"] * np.exp(-((x - WAIST["x"]) / WAIST["w"]) ** 2) * (x > G.NAC_X0 + 0.03)


def _crown_point(x, y):
    """(z, tangent) of the fuselage OML upper surface at butt line y >= 0 (station x)."""
    zt, zm = float(G.z_top(x)), float(G.z_mw(x))
    lo, hi = zm, zt
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if float(G.side_y(x, mid)) > y:
            lo = mid
        else:
            hi = mid
    z = 0.5 * (lo + hi)
    dz = 1e-3
    dy = float(G.side_y(x, z - dz)) - float(G.side_y(x, z))
    t = np.array([dy, -dz])
    return z, t / np.linalg.norm(t)          # tangent pointing outward-down


def _bez(p0, p1, p2, p3, u):
    u = np.asarray(u)[:, None]
    return (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u ** 2 * p2 + u ** 3 * p3


def section_yz(x, zc, hw, hh, n_top, n_bot, fw, phis):
    """Section points (y, z) at the angles phis (0 = starboard side, pi/2 = top, 3pi/2 = bottom)."""
    c, s = np.cos(phis), np.sin(phis)
    up = s >= 0
    n = np.where(up, n_top, n_bot)
    y = hw * np.sign(c) * np.abs(c) ** (2.0 / n)
    z = zc + hh * np.sign(s) * np.abs(s) ** (2.0 / n)
    if fw <= 1e-4:
        return y, z
    # fillet version of the lower half, blended in by the fillet width (w -> 1 at 6 cm)
    wgt = min(fw / 0.06, 1.0)
    yf = hw + fw
    zf, tf = _crown_point(x, yf)
    p0 = np.array([hw, zc])
    p3 = np.array([yf, zf])
    drop = max(zc - zf, 0.05)
    p1 = p0 + [0.0, -0.55 * drop]
    p2 = p3 - tf * (0.55 * fw + 0.25 * drop)
    lo = ~up
    v = np.where(c >= 0, (2 * np.pi - phis) / (np.pi / 2), (phis - np.pi) / (np.pi / 2))   # 0 at the side .. 1 at the bottom
    v = np.clip(v, 0, 1)
    uf = np.clip(v / 0.8, 0, 1)
    B = _bez(p0, p1, p2, p3, uf)
    # beyond the fillet (v > 0.8): back under the crown to the centre line, inside the fuselage (trimmed away later)
    under = v > 0.8
    k = np.clip((v - 0.8) / 0.2, 0, 1)
    B[under, 0] = yf * (1 - k[under])
    B[under, 1] = zf - 0.08 * np.sin(np.pi / 2 * k[under])
    yF = np.sign(c) * B[:, 0]
    zF = B[:, 1]
    y = np.where(lo, (1 - wgt) * y + wgt * yF, y)
    z = np.where(lo, (1 - wgt) * z + wgt * zF, z)
    return y, z


def cowl_rows():
    """Meridian rows (aft outer -> lip -> duct -> fan face) as (x, zc, hw, hh, n_top, n_bot, fillet, tag)."""
    rows = []
    xs = np.r_[np.linspace(G.NAC_X1, 6.20, 34), np.linspace(6.18, 5.905, 14)]
    for x in xs:
        k = float(waist(x))
        rows.append((x, float(G.nac_zc(x)), float(G.nac_hw(x)) * k, float(G.nac_hh(x)) * k, G.NAC_N, NAC_N_BOT, fillet_w(x), "outer"))
    xo, zo, wo, ho = 5.905, float(G.nac_zc(5.905)), float(G.nac_hw(5.905)), float(G.nac_hh(5.905))
    wi, hi = INNER_LIP
    zi = 2.442
    for a in np.linspace(0, np.pi, 17)[1:-1]:
        f = 0.5 * (1 + np.cos(a))           # 1 = outer, 0 = inner
        x = xo - 0.040 * np.sin(a)
        rows.append((x, zi + (zo - zi) * f, wi + (wo - wi) * f, hi + (ho - hi) * f, G.NAC_N * f + 2.2 * (1 - f),
                     NAC_N_BOT * f + INNER_N_BOT * (1 - f), 0.0, "lip"))
    for u in np.linspace(0, 1, 12):
        x = 5.905 + (FAN_X - 5.905) * u
        s = 0.5 - 0.5 * np.cos(np.pi * u)
        rows.append((x, zi + (FAN_ZC - zi) * s, wi + (FAN_R - wi) * s, hi + (FAN_R - hi) * s, 2.2 - 0.2 * s,
                     INNER_N_BOT + (2.0 - INNER_N_BOT) * s, 0.0, "duct"))
    return rows


def build_cowl():
    phis = np.linspace(0, 2 * np.pi, N_PHI, endpoint=False)
    rows = cowl_rows()
    P = np.zeros((len(rows), N_PHI, 3))
    for i, (x, zc, hw, hh, nt, nb, fw, tag) in enumerate(rows):
        y, z = section_yz(x, zc, hw, hh, nt, nb, fw, phis)
        P[i, :, 0] = x
        P[i, :, 1] = y
        P[i, :, 2] = z
    UVu = np.arange(len(rows), dtype=float)
    UV = np.stack(np.meshgrid(UVu, phis, indexing="ij"), -1)
    m = grid_surface(P, close_v=True, UV=UV)
    # outward on the outer skin: check a top point of the first row
    top = np.argmin(np.linalg.norm(m.V - P[0, N_PHI // 4], axis=1))
    if m.N[top, 2] < 0:
        m = m.flipped()
    tags = np.array([r[-1] for r in rows])
    n_outer = int((tags == "outer").sum())
    n_lip = int((tags == "lip").sum())
    # material bands by row index: white outer (up to 6 cm behind the highlight), metal lip, dark duct
    u = m.UV[:, 0]
    i_lipstart = n_outer - 3.0
    i_duct = n_outer + n_lip + 1.5
    outer = trim(m, i_lipstart - u, "positive")
    rest = trim(m, u - i_lipstart, "positive")
    lip = trim(rest, i_duct - rest.UV[:, 0], "positive")
    duct = trim(rest, rest.UV[:, 0] - i_duct, "positive")
    outer = trim(outer, G.inside_fuselage(outer.V), "positive")
    return outer, lip, duct


def build_nozzle():
    """Exit: cowl trailing edge rolls into the nozzle wall, a mixer plug inside."""
    phis = np.linspace(0, 2 * np.pi, N_PHI, endpoint=False)
    x1 = G.NAC_X1
    zc, hw, hh = float(G.nac_zc(x1)), float(G.nac_hw(x1)), float(G.nac_hh(x1))
    rows = [(x1, zc, hw, hh), (x1 + 0.004, zc, hw * 0.985, hh * 0.98), (x1, zc, hw * 0.94, hh * 0.92),
            (7.85, zc + 0.008, hw * 0.92, hh * 0.92), (7.72, zc + 0.012, hw * 0.88, hh * 0.90)]
    P = np.zeros((len(rows), N_PHI, 3))
    for i, (x, z, w, h) in enumerate(rows):
        dy, dz = _dirs(2.2, phis)
        P[i, :, 0], P[i, :, 1], P[i, :, 2] = x, w * dy, z + h * dz
    wall = grid_surface(P, close_v=True)
    # mixer plug (cone) and back wall
    zc2 = zc + 0.01
    plug = revolve([(0.0, 0.0), (0.0, 0.085), (0.18, 0.070), (0.30, 0.030), (0.35, 0.0)], n=40,
                   axis_origin=(7.73, 0, zc2), axis_dir=(1, 0, 0))
    back = disk((7.725, 0, zc2), (1, 0, 0), max(hw, hh) * 0.95, n=40)
    lobes = []
    for k in range(12):   # mixer lobes [inf: FJ33 'exhaust mixer' (TCDS E3GL)]
        a = 2 * np.pi * k / 12
        c = np.array([7.80, 0.11 * np.cos(a), zc2 + 0.085 * np.sin(a)])
        lobes.append(superellipsoid(c, (0.07, 0.022, 0.022), e=(0.6, 0.6), nu=8, nv=10))
    return wall, Mesh.merge([plug] + lobes), back


def build_fan(nb=18):
    hub = revolve([(0.0, 0.0), (0.03, 0.040), (0.08, 0.066), (0.13, 0.078), (0.16, 0.078)], n=48,
                  axis_origin=(FAN_X - 0.135, 0, FAN_ZC), axis_dir=(1, 0, 0))
    blades = []
    for k in range(nb):
        a0 = 2 * np.pi * k / nb
        rr = np.linspace(0.076, FAN_R - 0.004, 8)
        quads = []
        for r in rr:
            pitch = np.radians(62 - 30 * (r - 0.076) / (FAN_R - 0.076))   # twist [inf]
            ch = 0.055 + 0.015 * (r - 0.076) / (FAN_R - 0.076)
            ang = a0 + np.array([-0.5, 0.5]) * ch * np.cos(pitch) / r
            xs = FAN_X + np.array([-0.5, 0.5]) * ch * np.sin(pitch)
            quads.append(np.stack([xs, r * np.cos(ang), FAN_ZC + r * np.sin(ang)], 1))
        P = np.array(quads)
        blade = grid_surface(P)
        blades.append(blade)
        blades.append(blade.offset(-0.002).flipped())
    face = disk((FAN_X + 0.04, 0, FAN_ZC), (-1, 0, 0), FAN_R, n=48)
    return Mesh.merge([hub]), Mesh.merge(blades), face


def build_pylon(n_phi=48):
    """Aft pylon fairing between the nacelle underside and the tail-cone crown (AFM Fig 1-1 'pylon panels')."""
    xs = np.linspace(7.15, 8.32, 30)
    phis = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)
    rows = []
    for x in xs:
        crown = float(G.z_top(x))
        if x <= G.NAC_X1:
            top = float(G.nac_zc(x) - G.nac_hh(x)) + 0.008
        else:
            u = (x - G.NAC_X1) / (8.32 - G.NAC_X1)
            top = float(G.nac_zc(G.NAC_X1) - G.nac_hh(G.NAC_X1)) * (1 - u) + (crown + 0.005) * u
        bot = crown - 0.05
        hw = float(np.interp(x, [7.15, 7.6, 8.0, 8.32], [0.20, 0.17, 0.13, 0.04]))
        zc, hh = 0.5 * (top + bot), max(0.5 * (top - bot), 0.004)
        dy, dz = _dirs(2.6, phis)
        rows.append(np.stack([np.full(n_phi, x), hw * dy, zc + hh * dz], 1))
    P = np.array(rows)
    m = grid_surface(P, close_v=True)
    top = np.argmin(np.linalg.norm(m.V - P[5, n_phi // 4], axis=1))
    if m.N[top, 2] < 0:
        m = m.flipped()
    return trim(m, G.inside_fuselage(m.V), "positive")


def build(parts):
    outer, lip, duct = build_cowl()
    wall, plug, back = build_nozzle()
    # inlet diverter / pylon nose under the inlet lip
    div = superellipsoid((5.985, 0.0, 2.200), (0.125, 0.10, 0.050), e=(0.5, 0.5), nu=14, nv=24)
    div = trim(div, G.inside_fuselage(div.V), "positive")
    # pylon NACA inlets (both sides) and louver (left) [inf: positions]
    naca = []
    phis = np.radians([-28.0])
    for sgn in (-1, 1):
        for x0 in (6.95,):
            pts = []
            for dx, w in ((0.0, 0.010), (0.13, 0.034)):
                x = x0 + dx
                zc, hw, hh = float(G.nac_zc(x)), float(G.nac_hw(x)), float(G.nac_hh(x))
                for dphi in (-w, w):
                    phi = phis[0] + dphi / 0.3
                    dy, dz = _dirs(G.NAC_N, np.array([phi]))
                    pts.append([x, sgn * hw * dy[0] * 1.004, zc + hh * dz[0] * 1.004])
            q = np.array([pts[0], pts[1], pts[3], pts[2]])
            naca.append(planar_cap(q, (0, sgn, -0.4)))
    zc, hw, hh = float(G.nac_zc(7.35)), float(G.nac_hw(7.35)), float(G.nac_hh(7.35))
    louv = []
    for k in range(5):
        x = 7.28 + 0.03 * k
        dy, dz = _dirs(G.NAC_N, np.radians(np.array([-25.0])))
        c = np.array([x, -hw * dy[0] * 1.005, float(G.nac_zc(x)) + float(G.nac_hh(x)) * dz[0]])
        louv.append(box(c, (0.012, 0.004, 0.06)))
    p = Part("nacelle", "Engine nacelle, inlet & exhaust (FJ33-5A)", "powerplant", group="Powerplant",
             material_note="Composite cowls; bleed-air heated inlet lip; exhaust mixer",
             info={"engine": "Williams International FJ33-5A, 1,846 lbf take-off (TCDS A00018CH / E3GL)",
                   "engine envelope": "42.7 x 25.1 in, fwd flange OD 18.4 in (TCDS E3GL)",
                   "inlet": f"FS {G.NAC_X0:.3f}, exit FS {G.NAC_X1:.3f} [inf: AFM Fig 1-1]"})
    p.add(outer, "paint_white").add(lip, "inlet_lip").add(duct, "inlet_dark").add(wall, "exhaust")
    p.add(plug, "exhaust").add(back, "inlet_dark").add(div, "paint_white")
    p.add(Mesh.merge(naca), "inlet_dark").add(Mesh.merge(louv), "metal_dark").add(build_pylon(), "paint_white")
    # exhaust tray on the tail-cone crown behind the nozzle [inf]
    tray = FU.skin_patch(7.98, 8.70, -0.045, 0.045, 0.012)
    tray.UV = None
    tray = tray.offset(0.0015)
    p.add(tray, "metal")
    parts[p.id] = p
    hub, blades, face = build_fan()
    f = Part("fan", "FJ33-5A fan & spinner", "powerplant",
             pivot=dict(origin=[FAN_X, 0.0, FAN_ZC], axis=ENG_AXIS.tolist(), kind="spin", rpm=None),
             group="Powerplant", material_note="Fan: 18 blades [inf: count], spins with state.rotorAng",
             info={"fan diameter": f"{2 * FAN_R:.2f} m [inf]"})
    f.add(hub, "metal_dark").add(blades, "fan")
    parts[f.id] = f
    fb = Part("fan_face", "Fan case / engine face (dark)", "powerplant", group="Powerplant")
    fb.add(face, "inlet_dark")
    parts[fb.id] = fb
