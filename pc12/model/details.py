"""
External details: wing-to-body belly fairing, flap-track canoes, weather-radar
pod (right wing tip, standard on PC-12s), navigation/strobe/beacon lights,
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


# ---- wing-to-body fairing (Stage 2 rev B: from the Pilatus drawing 190.10.40.432; the single source of these
# tables -- model/livery.py imports them).  The rev A fairing (bottom WL 735-805, STA 4920-8300) hung 136 mm too low.
#   side view   lower silhouette BELLY_FAIRING_BOT from the fairing nose (STA 5153, WL 1052) down to its lowest
#               point WL 871 at STA ~5850 and up again; drawn to STA 6465 (WL 897), hidden behind the main gear from
#               there to STA 7450 (assumed: a smooth run back to the keel, WL 939 at STA 7450-7550);
#               forward upper edge BELLY_FAIRING_NOSE_EDGE (nose -> the wing root upper surface);
#               tail lobe on the fuselage side BELLY_FAIRING_TAIL: from the wing root (STA 6972, WL 1631) aft and down
#               to a rounded end at STA 8585 (WL 1170), forward along its lower edge to the wing TE (STA 7535, WL 1004)
#   front view  flat bottom WL 871.5 out to BL +/-830 (BELLY_FAIRING_FLAT), radius into the wing lower surface
#   plan        the upper root fillet covers the wing to BL 1010 from STA 5366 to 7457 with fillets into the
#               fuselage side at STA 5343 and 7641 (BELLY_FAIRING_PLAN, starboard)
# The reconstructed centre-section airfoil is fuller aft than the drawn WR sections: its BL 0 lower surface lies
# 3-13 mm below the drawn fairing bottom between STA 6000 and 6600 (Stage 3: retune the airfoil or let the fairing
# enclose it).
BELLY_FAIRING_BOT = [(5.153, 1.052), (5.165, 1.011), (5.200, 0.980), (5.267, 0.951), (5.334, 0.930),
                     (5.461, 0.906), (5.573, 0.888), (5.690, 0.876), (5.850, 0.8715), (6.000, 0.873),
                     (6.200, 0.880), (6.465, 0.897), (6.800, 0.912), (7.100, 0.925), (7.450, 0.939), (7.550, 0.941)]
BELLY_FAIRING_BOT_HIDDEN = (6.465, 7.450)      # drawn behind the main gear: assumed there
BELLY_FAIRING_FLAT = dict(z=0.8715, hw=0.830, r=0.070)   # front view: flat bottom WL, its half-width, corner radius
# footprint half-width seen from below (flat bottom + corner radius; nose / aft closure assumed round)
BELLY_FAIRING_HW = [(5.153, 0.060), (5.200, 0.420), (5.300, 0.690), (5.450, 0.860), (5.650, 0.900),
                    (7.150, 0.900), (7.350, 0.860), (7.480, 0.700), (7.550, 0.420), (7.600, 0.060)]
BELLY_FAIRING_NOSE_EDGE = [(5.153, 1.052), (5.159, 1.082), (5.175, 1.119), (5.205, 1.162), (5.251, 1.213),
                           (5.323, 1.288), (5.406, 1.360), (5.470, 1.407), (5.509, 1.432)]
BELLY_FAIRING_TAIL = [(6.972, 1.631), (7.325, 1.605), (7.610, 1.574), (7.844, 1.531), (8.048, 1.483),
                      (8.251, 1.412), (8.436, 1.313), (8.567, 1.219), (8.581, 1.197), (8.585, 1.170),
                      (8.574, 1.141), (8.555, 1.124), (8.541, 1.118), (8.395, 1.104), (8.111, 1.078),
                      (7.852, 1.046), (7.682, 1.023), (7.613, 1.013), (7.535, 1.004), (7.499, 1.019)]
BELLY_FAIRING_PLAN = [(5.343, 0.862), (5.357, 0.901), (5.362, 0.928), (5.366, 0.987), (5.397, 0.994),
                      (5.459, 1.003), (5.552, 1.009), (5.699, 1.012), (6.038, 1.012), (6.360, 1.015),
                      (6.841, 1.013), (7.216, 1.009), (7.336, 1.006), (7.457, 0.991), (7.479, 0.954),
                      (7.515, 0.914), (7.566, 0.885), (7.641, 0.864)]
BELLY_FAIRING_X = (BELLY_FAIRING_BOT[0][0], BELLY_FAIRING_TAIL[9][0])   # nose / tail end stations (5153 / 8585)


def belly_fairing_bottom(x):
    """Lower silhouette WL of the wing-to-body fairing at station(s) x (side view)."""
    from cad.mesh import pchip
    return pchip(*zip(*BELLY_FAIRING_BOT))(np.asarray(x, float))


def belly_fairing_halfwidth(x):
    """Footprint half-width (seen from below) of the fairing at station(s) x."""
    from cad.mesh import pchip
    return np.maximum(pchip(*zip(*BELLY_FAIRING_HW))(np.asarray(x, float)), 0.0)


def belly_fairing_section(x, n=72, z_top=1.20):
    """Cross-section ring (n, 3) of the lower fairing at station x: flat bottom at belly_fairing_bottom(x), corner
    radius BELLY_FAIRING_FLAT['r'], vertical sides up to z_top (buried in the fuselage / wing root)."""
    zb = float(belly_fairing_bottom(x))
    hw = max(float(belly_fairing_halfwidth(x)), 0.02)
    r = min(BELLY_FAIRING_FLAT["r"], 0.9 * hw, 0.9 * max(z_top - zb, 0.01))
    # perimeter: bottom centre -> starboard corner -> up the side -> over the top -> port side -> back
    k = n // 4
    a = np.linspace(-np.pi / 2, 0.0, k)
    stbd = np.r_[np.c_[np.linspace(0.0, hw - r, k), np.full(k, zb)],
                 np.c_[hw - r + r * np.cos(a), zb + r + r * np.sin(a)],
                 np.c_[np.full(k, hw), np.linspace(zb + r, z_top, k)]]
    half = np.r_[stbd, np.c_[np.linspace(hw, 0.0, k), np.full(k, z_top)]]
    ring = np.r_[half, (half * [-1, 1])[::-1][1:-1]]
    return np.c_[np.full(len(ring), x), ring]


def belly_fairing():
    """Lower wing-to-body fairing (mesh) lofted through belly_fairing_section() -- the side-view tail lobe and the
    upper root fillet (BELLY_FAIRING_TAIL / _PLAN) are drawn on sheet L4 and follow in Stage 3."""
    x0, x1 = BELLY_FAIRING_BOT[0][0], BELLY_FAIRING_HW[-1][0]
    xs = np.linspace(x0 + 0.002, x1 - 0.002, 48)
    rows = [belly_fairing_section(x) for x in xs]
    m_ = min(len(r) for r in rows)
    P = np.array([r[:m_] for r in rows])
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


FLAP_CANOE_Y = (1.00, 3.07, 4.885)     # drawing front / plan views (rev A 1.55, 3.30, 5.15)


def flap_canoes():
    out = []
    for y in FLAP_CANOE_Y:
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


# weather-radar pod: at the STARBOARD WING TIP, on the leading edge just inboard of the winglet (Pilatus drawing
# plan + front views; photos ngx_kenia_stbd_pilatus, pro3008_stbd34_pilatus; Pilatus tech-data front render).
# Round pod, black radome ahead of the joint, body faired into the winglet root.  PRO: radome enlarged for the
# 12-in GWX 8000 antenna -> R 0.165 (the NGX drawing shows 0.155).  Rev A had it at BL 3.90 (wrong).
POD_Y, POD_Z = 7.635, 1.760            # pod axis (butt line, water line)
POD_X_TIP, POD_X_JOINT, POD_X_END = 5.150, 5.575, 6.000
POD_R = 0.165
POD_NOSE_L = 0.305                     # elliptic nose length (tip -> full radius)
POD_CYL_END = 5.720                    # end of the cylindrical part; tapers into the winglet root aft of it


def radar_pod_profile(n=36):
    """(x, r) meridian of the pod, x = station."""
    L = POD_X_END - POD_X_TIP
    prof = []
    for t in np.linspace(0, 1, n):
        x = POD_X_TIP + t * L
        if x < POD_X_TIP + POD_NOSE_L:
            r = POD_R * max(0.0, 1 - (1 - (x - POD_X_TIP) / POD_NOSE_L) ** 2) ** 0.5
        elif x < POD_CYL_END:
            r = POD_R
        else:
            u = (x - POD_CYL_END) / (POD_X_END - POD_CYL_END)
            r = POD_R * max(0.0, 1 - u ** 2) ** 0.5
        prof.append((x, r))
    return prof


def radar_pod():
    prof = [(x - POD_X_TIP, r) for x, r in radar_pod_profile()]
    prof[0] = (0.0, 0.0)
    body = revolve(prof, n=40, axis_origin=(POD_X_TIP, POD_Y, POD_Z), axis_dir=(1, 0, 0))
    radome = trim_x(body, POD_X_JOINT, keep_less=True)
    rest = trim_x(body, POD_X_JOINT, keep_less=False)
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
    rp = Part("radar_pod", "Weather-radar pod, right wing tip (GWX 8000, 12-in antenna)", "details",
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
