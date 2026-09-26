"""
External details: wing-to-body belly fairing, flap-track canoes, weather-radar
pod (right wing tip, standard on PC-12s), navigation/strobe/beacon lights,
antennas, pitot-static probes and static dischargers.
"""
from __future__ import annotations
import numpy as np

from cad.mesh import (Mesh, grid_surface, revolve, cylinder, superellipsoid, sweep_tube, cap_ring,
                      rotation_matrix, box, trim)
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
# Stage 3 (CONS2-05, parameter decision): the drawn nose edge ran up through the airstair door's lower aft corner (door
# panel to STA 5290, hinge WL 1254, opens 160 deg: below the hinge the open slab sweeps everything more than 20 deg
# outboard of the downward vertical).  The builder had to cut the nose bump there by up to 58 mm (a pinched crease
# at the corner, the 3-D edge up to 83 mm under the drawn one).  The edge is redrawn clear of that wedge: it stays
# under WL ~1.185 to the door edge + ROOT_FILLET_DOOR_CLEAR (the wedge limit meets the fuselage side at WL ~1.19
# there) and rejoins the drawn line at STA 5406 -- up to 73 mm under the Pilatus line over STA 5.22-5.40
# (rev: (5.205, 1.162), (5.251, 1.213), (5.323, 1.288)).
BELLY_FAIRING_NOSE_EDGE = [(5.153, 1.052), (5.159, 1.082), (5.175, 1.119), (5.205, 1.148), (5.251, 1.168),
                           (5.300, 1.180), (5.345, 1.232), (5.406, 1.360), (5.470, 1.407), (5.509, 1.432)]
BELLY_FAIRING_TAIL = [(6.972, 1.631), (7.325, 1.605), (7.610, 1.574), (7.844, 1.531), (8.048, 1.483),
                      (8.251, 1.412), (8.436, 1.313), (8.567, 1.219), (8.581, 1.197), (8.585, 1.170),
                      (8.574, 1.141), (8.555, 1.124), (8.541, 1.118), (8.395, 1.104), (8.111, 1.078),
                      (7.852, 1.046), (7.682, 1.023), (7.613, 1.013), (7.535, 1.004), (7.499, 1.019)]
# VQA r3 (SHP2-06 / RQ2-02): the drawn plan edge turns out along the wing LE in a sharp corner ((5.357, 0.901),
# (5.362, 0.928), (5.366, 0.987), (5.397, 0.994)); the fillet foot is tangent to the wing, so the tangent-continuous
# blend (ROOT_FILLET_FOOT_SMOOTH) rounds it anyway -- the corner is now that rounded edge (up to 22 mm inside the
# drawn corner point, 0 from STA 5.42 aft), so the foot no longer jumps at the LE (the ridge / lump of the renders).
BELLY_FAIRING_PLAN = [(5.343, 0.862), (5.355, 0.901), (5.365, 0.928), (5.375, 0.949), (5.385, 0.968), (5.395, 0.982),
                      (5.405, 0.990), (5.420, 0.996), (5.459, 1.003), (5.552, 1.009), (5.699, 1.012), (6.038, 1.012), (6.360, 1.015),
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


def wing_lower_z(x, y, behind_te=False):
    """WL of the wing's lower surface at plan station x, butt line |y| (nan outside the chord; with behind_te=True
    the trailing-edge WL behind the chord)."""
    x, y = np.broadcast_arrays(np.asarray(x, float), np.abs(np.asarray(y, float)))
    out = np.full(x.shape, np.nan)
    for i in np.ndindex(x.shape):
        s = W.section_at(float(min(y[i], W.SEMI)))
        xc = (x[i] - s.le[0]) / s.chord
        if 0.0 <= xc <= 1.0 or (behind_te and xc > 1.0):
            out[i] = float(s.lower(np.array(min(xc, 1.0)))[2])
    return out


def belly_fairing():
    """Lower wing-to-body fairing: flat-bottomed shell lofted through belly_fairing_section() (drawn bottom WL and
    footprint), its side walls trimmed where they enter the fuselage and the wing's lower surface -- so the upper
    edges lie on the fuselage side ahead of / behind the wing and on the wing root, and the carry-through (flattened
    in model/wing.py) is enclosed; behind the wing it ends at the trailing-edge WL.  The upper root fillet and the
    fairing nose above it are root_fillet()."""
    from model.empennage import oml_field
    x0, x1 = BELLY_FAIRING_BOT[0][0], BELLY_FAIRING_HW[-1][0]
    xs = np.linspace(x0 + 0.002, x1 - 0.002, 90)
    rows = [belly_fairing_section(x, n=96, z_top=1.30) for x in xs]
    m_ = min(len(r) for r in rows)
    P = np.array([r[:m_] for r in rows])
    m = grid_surface(P, close_v=True)
    cen = P.mean(1)
    if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
        m = m.flipped()
    m = Mesh.merge([m, cap_ring(P[0], (-1, 0, 0)), cap_ring(P[-1], (1, 0, 0))])
    m = trim(m, oml_field(m.V) + 0.002, "positive")                      # outside the fuselage
    zl = wing_lower_z(m.V[:, 0], m.V[:, 1], behind_te=True)        # below the wing lower surface (behind the
    m = trim(m, np.where(np.isnan(zl), -1.0, m.V[:, 2] - zl - 0.002), "negative")   # chord: below its TE WL)
    # and never above the drawn upper edge (nose edge / tail lobe): ahead of the wing the box walls (vertical up to
    # WL 1.30) stood out of the fuselage side above the (redrawn, CONS2-05) fairing nose
    z_up = root_fillet_lines()[0]
    m = trim(m, m.V[:, 2] - z_up(np.clip(m.V[:, 0], BELLY_FAIRING_X[0], BELLY_FAIRING_X[1])), "negative")
    # ahead of the wing the fairing nose (root_fillet) is the drawn shape: above its foot the box's walls stay inside
    # it (they stood out of the nose near its upper edge, where the nose bump runs down to the fuselage side)
    V = m.V
    zj, _, _, zl, _ = _fillet_frame(V[:, 0])
    zt, fch = wing_top(V[:, 0], V[:, 1])                # above the fillet foot, where the nose / fillet mesh exists
    ahead = (V[:, 0] < 6.0) & (V[:, 2] > zj + 0.005) & ((fch > 0.0) | (V[:, 2] > zt + 0.004))
    ys = F.side_y(np.clip(V[:, 0], F.STA["cowl_front"], F.STA["tail_end"]), V[:, 2])
    f = np.where(ahead, ys + root_fillet_standoff(V[:, 0], V[:, 2]) - 0.008 - np.abs(V[:, 1]), 1.0)
    if (f < 0).any():
        m = trim(m, f, "positive")
    return m


# ---- upper wing-root fillet + fairing nose (Stage 3, sheet L4 item 3) -------------------------------------------
# The fairing above / ahead of the wing root is a horizontal offset of the fuselage OML: at (x, z) its surface lies at
# y = side_y(x, z) + d(x, z) (d >= 0), so its side-view outline is exactly the drawn one:
#   upper edge on the fuselage side  BELLY_FAIRING_NOSE_EDGE (nose -> STA 5509), then a monotone run up to the tail
#                                    lobe's upper edge BELLY_FAIRING_TAIL (STA 6972, WL 1631 ...)
#   lower edge of the nose           BELLY_FAIRING_BOT (the nose tip STA 5153, WL 1052)
#   plan edge on the wing            BELLY_FAIRING_PLAN (BL ~1010 over the chord, fillets into the side at 5343 / 7641)
# Cross-section law: a concave elliptic fillet from the wing upper surface (tangent, at the plan edge) to the fuselage
# side (tangent, at the upper edge); ahead of the wing leading edge the same standoff fades into a round-nosed bump
# between the drawn nose edge and the fairing's lower silhouette.  Everything inside the wing (or under it, inside
# the chord) is trimmed away -- the lower belly fairing is there.
# The drawn tail lobe runs on aft over the cargo-door panel (D2, STA 7540-8940) to STA 8585; sheet L3 note 7: the
# fairing must not cut into the D2 panel, and the Pilatus NGX cargo-door photo shows the fairing ending at the door's
# forward seam -- so the fillet fades out between ROOT_FILLET_TAPER and the D2 seam (both sides, symmetric).
ROOT_FILLET_TAPER = 7.400          # STA where the aft fade-out starts (over ~0.13 m to the D2 seam); rev 7.150 left
#                                    the drawn plan edge from STA 7.20, 0.26 m ahead of its knee at 7.457 (CONS2-04)
ROOT_FILLET_GAP = 0.012            # m ahead of the D2 panel seam where the standoff has reached zero
ROOT_FILLET_MIN_D = 0.0015         # standoffs below this are left to the fuselage skin (no z-fighting)
ROOT_FILLET_BLEND = (0.000, 0.300) # m ahead of / behind the wing LE over which the nose bump turns into the fillet
#                                    (VQA r2 SHP2-06 / RQ2-02: over 0.08 m the convex bump -> concave fillet change stood
#                                    up as a sharp triangular ridge from the LE to the upper edge; now gradual, on the wing)
ROOT_FILLET_TIP_RUNIN = 0.030     # m behind the nose tip over which the standoff runs in from zero (smoothstep)
ROOT_FILLET_TE_BLEND = (0.050, 0.030)   # m ahead of / behind the wing TE over which the fillet turns back into the bump
ROOT_FILLET_DOOR_CLEAR = 0.015     # m between the fairing nose and the open airstair door (door slab included)
ROOT_FILLET_DOOR_RELAX = 4.0       # m of standoff per m of STA by which that limit relaxes aft of the door edge
ROOT_FILLET_DOOR_SOFT = 0.012      # m, width of the soft minimum that applies the limit without a crease
_WTOP = {}


def _wing_top_table():
    """Lookup of the wing's upper surface near the root: (ys, le_x, chord, RegularGridInterpolator z(y, xc))."""
    if not _WTOP:
        from scipy.interpolate import RegularGridInterpolator
        ys = np.linspace(0.30, 1.40, 23)
        xc = np.r_[0.0, cos_pts(160, 0.0, 1.0)[1:]]
        secs = [W.section_at(float(y)) for y in ys]
        le = np.array([s.le[0] for s in secs])
        ch = np.array([s.chord for s in secs])
        zu = np.array([s.upper(xc)[:, 2] for s in secs])
        _WTOP.update(ys=ys, le=le, ch=ch, f=RegularGridInterpolator((ys, xc), zu))
    t = _WTOP
    return t["ys"], t["le"], t["ch"], t["f"]


def wing_top(x, y):
    """(upper-surface WL at (x, clip(x into the chord)), chord field max(le - x, x - te)) of the wing near the root:
    the field is > 0 ahead of / behind the section at butt line |y|, <= 0 inside the chord."""
    ys, le, ch, f = _wing_top_table()
    x, y = np.broadcast_arrays(np.asarray(x, float), np.clip(np.abs(np.asarray(y, float)), ys[0], ys[-1]))
    lx, c = np.interp(y, ys, le), np.interp(y, ys, ch)
    xc = np.clip((x - lx) / c, 0.0, 1.0)
    return f(np.stack([y.ravel(), xc.ravel()], 1)).reshape(x.shape), np.maximum(lx - x, x - (lx + c))


def _pchip(pts):
    from cad.mesh import pchip
    P = np.array(sorted(pts))
    return pchip(P[:, 0], P[:, 1])


def root_fillet_lines():
    """(z_up(x), z_lo(x), y_out(x), x-range) of the fillet: upper edge on the fuselage side, lower edge of the nose
    (below the wing the value only has to lie under it), plan edge on the wing; all from the drawn tables."""
    T = BELLY_FAIRING_TAIL
    z_up = _pchip(list(BELLY_FAIRING_NOSE_EDGE) + list(T[:10]))
    lo = [p for p in BELLY_FAIRING_BOT if p[0] <= 5.34] + [(7.40, 0.930)] + [p for p in T[10:] if p[0] >= 7.53]
    z_lo = _pchip(lo)
    Pp = np.array(BELLY_FAIRING_PLAN)
    y_out = _pchip([tuple(p) for p in Pp])            # C1 through the drawn points (np.interp kinked the foot, MQ2-01)
    from model.fuselage_parts import CARGO, door_panel
    pan = door_panel(CARGO)
    x_end = pan["cx"] - pan["hx"] - ROOT_FILLET_GAP
    return z_up, z_lo, y_out, (BELLY_FAIRING_X[0], x_end)


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


ROOT_FILLET_FOOT_SMOOTH = 0.038    # m, Gaussian width over which the foot WL / standoff are smoothed along x (MQ2-01;
#                                    VQA r2 SHP2-06: 0.010 -> 0.038, 41 kernel samples: the standoff peaked 0.33 m at the
#                                    wing LE -- a lump with a ridge up to the upper edge -- where the foot jumps from
#                                    the LE WL onto the upper surface)


def _foot(x, y_out):
    """(WL, standoff) of the fillet foot at station(s) x: the wing's upper surface at the plan edge (clipped into the
    chord) and the plan edge's standoff from the fuselage side there, both smoothed along x (Gaussian,
    ROOT_FILLET_FOOT_SMOOTH) -- the raw foot jumps ~45 mm in WL and ~50 mm in standoff over ~10 mm where it rounds the
    leading-edge nose (the drawn plan edge runs out along the unswept LE there) and kinks at the trailing edge, which
    folded the surface in its 6 mm grid (MQ2-01).  Where the smoothed foot dips under the wing just aft of the LE nose
    the fillet is trimmed by the wing."""
    Pp = np.array(BELLY_FAIRING_PLAN)
    ys, le, ch, _ = _wing_top_table()
    x = np.asarray(x, float)
    k = np.linspace(-2.0, 2.0, 41)
    w = np.exp(-0.5 * k * k)
    w /= w.sum()
    x1 = root_fillet_lines()[3][1]
    zj, S = np.zeros(x.shape), np.zeros(x.shape)
    # the wide smoothing is for the leading-edge nose; toward the aft fade-out it narrows back to the rev B 10 mm, so
    # the plan edge still follows the drawn one up to ROOT_FILLET_TAPER (the fade itself is not smeared forward)
    sig = ROOT_FILLET_FOOT_SMOOTH + (0.010 - ROOT_FILLET_FOOT_SMOOTH) * _smooth((x - 6.4) / (ROOT_FILLET_TAPER - 0.1 - 6.4))
    for kk, ww in zip(k, w):
        xx = x + kk * sig
        xf = np.clip(xx, F.STA["cowl_front"], F.STA["tail_end"])
        yo = y_out(np.clip(xx, Pp[0, 0], Pp[-1, 0]))
        lo, te = np.interp(yo, ys, le), np.interp(yo, ys, le + ch)
        z = wing_top(np.clip(xx, lo, te), yo)[0]
        # aft fade-out (ROOT_FILLET_TAPER -> the D2 seam): the foot moves in towards the fuselage side -- keep it ON the
        # wing at its faded butt line (the wing is lower inboard) instead of floating at the plan-edge WL
        fade = 1.0 - _smooth((xx - ROOT_FILLET_TAPER) / (x1 - ROOT_FILLET_TAPER))
        for _ in range(2):
            ys_ = F.side_y(xf, z)
            yf = np.maximum(ys_ + fade * (yo - ys_), ys[0])
            lo, te = np.interp(yf, ys, le), np.interp(yf, ys, le + ch)
            z = np.where(fade < 1.0, wing_top(np.clip(xx, lo, te), yf)[0], z)
        zj += ww * z
        # the nose ramp ahead of the plan outline (s^2 from the nose tip to its first point) inside the smoothing, so
        # the standoff has no slope kink where the ramp meets the plan edge (VQA r2 SHP2-06)
        sr = np.clip((xx - BELLY_FAIRING_X[0]) / (Pp[0, 0] - BELLY_FAIRING_X[0]), 0.0, 1.0)
        S += ww * fade * sr * sr * np.maximum(yo - F.side_y(xf, z), 0.0)
    return zj, S


def _fillet_frame(x):
    """Per-station frame of the fillet at x: (z_j foot WL on the wing at the plan edge, S standoff there, z_up upper
    edge, z_lo lower edge, a = weight of the fillet law vs the nose bump)."""
    z_up, z_lo, y_out, (x0, x1) = root_fillet_lines()
    x = np.asarray(x, float)
    Pp = np.array(BELLY_FAIRING_PLAN)
    xp0 = Pp[0, 0]
    xq = np.clip(x, xp0, Pp[-1, 0])
    yo = y_out(xq)
    ys, le, ch, _ = _wing_top_table()
    le_o = np.interp(yo, ys, le)
    zj, S = _foot(x, y_out)                                  # the fillet foot: wing upper surface at the plan edge
    # (incl. the nose ramp ahead of the plan outline -- slender: the open airstair door hangs next to it, see below)
    # and a short C1 run-in at the very tip (the in-kernel ramp alone left ~2 mm of standoff 2 mm behind the tip: a
    # blunt tip ahead of the drawn nose point)
    S = S * _smooth((x - x0) / ROOT_FILLET_TIP_RUNIN)
    # (the fade-out ahead of the D2 seam, ROOT_FILLET_TAPER -> x1, is applied in _foot)
    zu, zl = z_up(x), np.minimum(z_lo(x), zj - 1e-3)
    a = 1.0 - _smooth((le_o - x + ROOT_FILLET_BLEND[1]) / (ROOT_FILLET_BLEND[0] + ROOT_FILLET_BLEND[1]))
    # aft half: the fillet law, turning back into the round bump over ROOT_FILLET_TE_BLEND behind the wing's trailing
    # edge at the (faded) foot -- with no wing left to be tangent to, the fillet met its closure below the foot in a
    # 90 deg crease along the TE (MQ2-01)
    yf = F.side_y(np.clip(x, F.STA["cowl_front"], F.STA["tail_end"]), zj) + S
    te_f = np.interp(yf, ys, le + ch)
    b0, b1 = ROOT_FILLET_TE_BLEND
    a_te = 1.0 - _smooth((x - te_f + b0) / (b0 + b1))
    a = np.where(x > 0.5 * (xp0 + Pp[-1, 0]), a_te, a)
    return zj, S, zu, zl, a


# VQA r3 (SHP2-06 / RQ2-02): the foot standoff S peaks at the wing LE (0.29 m at STA 5.39 against the 0.235 m plateau
# aft: the drawn plan edge turns out along the LE while the foot is still at the low LE WL, where the fuselage is
# narrow) -- above the foot that peak stood out as a dome over the LE with a groove behind it (zebra test).  Above the
# foot the law uses S_up = S's monotone envelope from aft (running minimum, smoothed) plus the excess S - S_up decaying
# as (1 - u)^ROOT_FILLET_PEAK_DECAY, so the foot (plan edge on the wing) is unchanged and the dome fades out upward.
ROOT_FILLET_PEAK_DECAY = 6.0
ROOT_FILLET_PEAK_SMOOTH = 0.05     # m, Gaussian width of the envelope's smoothing
ROOT_FILLET_PEAK_END = 6.0         # STA: the envelope covers the leading-edge region ahead of this (S's plateau there)
_SUP = {}


def _standoff_envelope(x):
    """S_up(x): the foot standoff's monotone (non-increasing from aft) lower envelope, smoothed (see above)."""
    x0, x1 = root_fillet_lines()[3]
    key = (x0, x1, ROOT_FILLET_PEAK_SMOOTH, ROOT_FILLET_FOOT_SMOOTH, ROOT_FILLET_PEAK_END)
    if _SUP.get("key") != key:
        xs = np.arange(x0 - 0.3, x1 + 0.3, 0.002)
        S = _fillet_frame(xs)[1]
        i = int(np.searchsorted(xs, ROOT_FILLET_PEAK_END))     # running minimum from aft, over the LE region only
        env = S.copy()                                          # (not into the aft fade-out, where S -> 0)
        env[:i] = np.minimum.accumulate(S[:i][::-1])[::-1]
        sig = ROOT_FILLET_PEAK_SMOOTH / 0.002
        k = np.arange(-int(3 * sig), int(3 * sig) + 1)
        w = np.exp(-0.5 * (k / sig) ** 2)
        w /= w.sum()
        env = np.convolve(np.pad(env, len(k) // 2, mode="edge"), w, mode="valid")
        _SUP.update(key=key, xs=xs, env=np.minimum(env, S))
    return np.interp(x, _SUP["xs"], _SUP["env"])


def root_fillet_standoff(x, z):
    """Horizontal standoff d(x, z) >= 0 of the fillet / fairing nose from the fuselage side (starboard)."""
    x0, x1 = root_fillet_lines()[3]
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    zj, S, zu, zl, a = _fillet_frame(x)
    u = np.clip((z - zj) / np.maximum(zu - zj, 1e-6), 0.0, 1.0)
    v = np.clip((zj - z) / np.maximum(zj - zl, 1e-6), 0.0, 1.0)
    fil = 1.0 - np.sqrt(np.clip(u * (2.0 - u), 0.0, 1.0))  # concave elliptic fillet (tangent to wing and side)
    bump = (1.0 - u) ** 2 * (1.0 + 2.0 * u)                 # smooth bump (nose)
    # below the foot (kept only outside the chord): the bump's round lower half (nose; tail behind the TE)
    P = np.where(z >= zj, a * fil + (1.0 - a) * bump, np.sqrt(np.clip(1.0 - v * v, 0.0, 1.0)))
    if ROOT_FILLET_PEAK_DECAY:
        # decay measured from the VISIBLE foot: where the smoothed foot lies under the wing's upper surface (just aft
        # of the LE nose) from that surface at the plan edge, so the plan edge on the wing keeps the full standoff
        Pp = np.array(BELLY_FAIRING_PLAN)
        yo = root_fillet_lines()[2](np.clip(x, Pp[0, 0], Pp[-1, 0]))
        zt, fch = wing_top(x, yo)
        z0 = np.where(fch <= 0.0, np.maximum(zj, zt), zj)
        ue = np.clip((z - z0) / np.maximum(zu - z0, 1e-6), 0.0, 1.0)
        Su = _standoff_envelope(x)
        S = np.where(z >= zj, Su + (S - Su) * (1.0 - ue) ** ROOT_FILLET_PEAK_DECAY, S)
    inside = (x >= x0) & (x <= x1) & (z <= zu) & (z >= zl)
    d = np.where(inside, S * P, 0.0)
    # the fairing nose overlaps the airstair door panel in x (door to STA 5290, nose from 5153): below the hinge
    # the open door sweeps everything within (180 - open_deg) of the downward vertical, so there the fairing keeps
    # out of that wedge (+ ROOT_FILLET_DOOR_CLEAR)
    xd1, yh, zh, a_open, t_door = _airstair_sweep()
    env = yh + (zh - z) * np.tan(np.pi - a_open) - (t_door + ROOT_FILLET_DOOR_CLEAR) / np.cos(np.pi - a_open) - F.side_y(
        np.clip(x, F.STA["cowl_front"], F.STA["tail_end"]), z)
    # aft of the door's edge the limit relaxes at ROOT_FILLET_DOOR_RELAX (m per m of x) so the surface stays
    # continuous, and a soft minimum (width ROOT_FILLET_DOOR_SOFT) avoids a crease where the limit takes over
    kx = ROOT_FILLET_DOOR_SOFT                               # softplus: no slope kink at the door edge (MQ2-01)
    env = env + ROOT_FILLET_DOOR_RELAX * kx * np.logaddexp(0.0, (x - (xd1 + ROOT_FILLET_DOOR_CLEAR)) / kx)
    env = np.where(z < zh, env, 1.0)
    k = ROOT_FILLET_DOOR_SOFT
    m = np.minimum(d, env)
    soft = m - k * np.log(np.exp(-(d - m) / k) + np.exp(-(env - m) / k))
    return np.where(d > 0.0, np.clip(soft, 0.0, d), 0.0)



def _airstair_sweep():
    """(aft edge STA of the airstair door panel, |BL| and WL of its hinge line, open angle rad, slab thickness: the
    slab lies on the outboard side of the hinge plane when the door is open)."""
    from model.fuselage_parts import AIRSTAIR, DOOR_T, door_panel, door_pivot
    pan = door_panel(AIRSTAIR)
    pv = door_pivot(AIRSTAIR)
    return pan["cx"] + pan["hx"], abs(pv["origin"][1]), pv["origin"][2], abs(pv["open"]), DOOR_T


def root_fillet(step=0.006, n_up=44, n_lo=22):
    """Upper wing-root fillet + fairing nose, both sides (see root_fillet_standoff).  Sampled per station on the
    section law's own parameters (rows at fixed u above the foot z_j, clustered at the foot where the elliptic fillet
    is singular, and at fixed v below it), so the foot line is a grid row: inside the chord the part below it is
    dropped exactly there (a geometric wing intersection would be ill-conditioned -- the fillet is tangent to the
    wing), ahead of / behind the chord the nose bump's lower half is kept outside the wing."""
    x0, x1 = root_fillet_lines()[3]
    xs = np.linspace(x0, x1, int((x1 - x0) / step) + 2)
    zj, _, zu, zl, _ = _fillet_frame(xs)
    tu = np.linspace(0.0, 1.0, n_up) ** 2                      # u rows, clustered at the foot
    tv = 1.0 - (1.0 - np.linspace(0.0, 1.0, n_lo)) ** 2        # v rows, clustered at the lower edge
    out = []
    for rows, zfun in ((tu, lambda t: zj[:, None] + (zu - zj)[:, None] * t[None, :]),
                       (tv, lambda t: zj[:, None] - (zj - zl)[:, None] * t[None, :])):
        Z = zfun(rows)
        X = np.broadcast_to(xs[:, None], Z.shape)
        D = root_fillet_standoff(X, Z)
        Y = F.side_y(np.clip(X, F.STA["cowl_front"], F.STA["tail_end"]), Z) + D
        m = grid_surface(np.stack([X, Y, Z], -1))
        m.UV = None
        m = trim(m, root_fillet_standoff(m.V[:, 0], m.V[:, 2]) - ROOT_FILLET_MIN_D, "positive")
        zt, fch = wing_top(m.V[:, 0], m.V[:, 1])
        if rows is tu:        # above the foot: only the wing's leading-edge region can reach into it
            m = trim(m, np.maximum(fch, m.V[:, 2] - zt + 0.004), "positive")
        else:                 # below the foot: kept only ahead of / behind the chord
            m = trim(m, fch, "positive")
        if m.nf:
            if np.mean(m.N[:, 1]) < 0:
                m = m.flipped()
            out.append(m)
    m = Mesh.merge(out)
    return Mesh.merge([m, m.mirrored_y()])


def boot_under_fillet(parts):
    """Trim the wings' de-ice boot band (wing.BOOT_Y from BL 0.95, offset 1.5 mm) where it runs under the root fillet /
    fairing nose: inboard of the fillet's plan edge on the wing (root_fillet_lines' y_out, the foot line the fillet is
    tangent to the wing along).  The fillet lies 0.2-0.4 mm above the boot there and crossed it at a grazing angle --
    a sawtooth edge at the root LE (MQ2-01); now the boot ends in its own 1.5 mm step on the fillet's foot line, round
    the LE and on the lower band too (so it does not end in a notch at the LE; BL 0.95 -> ~0.99 underneath)."""
    y_out = root_fillet_lines()[2]
    Pp = np.array(BELLY_FAIRING_PLAN)
    for pid in ("wing_R", "wing_L"):
        if pid not in parts:
            continue
        new = []
        for m, mat in parts[pid].meshes:
            if mat == "deice_boot" and m.nf:
                f = np.abs(m.V[:, 1]) - y_out(np.clip(m.V[:, 0], Pp[0, 0], Pp[-1, 0]))
                if (f < 0).any():
                    under = trim(m, f, "negative")      # the band IS the wing skin there: back onto the surface,
                    m = trim(m, f, "positive")          # as plain (painted) skin under the fillet
                    if under.nf:
                        new.append((under.offset(-0.0015), "paint_white"))
            new.append((m, mat))
        parts[pid].meshes = new


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
# Stage 3 (M9): each canoe is split at the flap-cove lower lip (wing.FLAP_X_LO): the forward part is fixed to the wing,
# the aft part rides on the flap (added to the flap parts, so it follows the Fowler rotation + travel).  Both are
# flattened against the surface they hang from (the hidden upper half no longer reaches into the cove / flap).
# VQA r1 (SHP-02 / R1-03): the real fairings are fat canoe bodies, not fins -- sized by projecting candidates through
# the N81DW air-to-air camera (cams.json 'stbd_air', rms 5.3 px) onto the three canoes under the starboard wing:
# a pointed nose at 0.39 chord, 0.72 chords long (the blunt, rounded tail 0.11 chord aft of the trailing edge),
# 0.20 m wide and hanging 0.25 m below the axis (just under the lower skin at 75 % chord), the deepest section at 64 %
# of its length (CANOE_SHAPE: r ~ t^a (1 - t)^b); aft of the trailing edge its top rises only CANOE_UP of that
# above the axis (rev A: 0.55 / 0.60 chord, 0.10 m wide, 0.09 m deep -- knife-thin fins in every render).
CANOE_X = (0.39, 0.72)                 # start (chord fraction) and length (chords)
CANOE_DEPTH, CANOE_HW = 0.25, 0.10     # max radius below the axis / max half-width (m)
CANOE_SHAPE = (0.9, 0.5)               # nose / tail exponents of the meridian law (max at a / (a + b) = 0.64)
CANOE_UP = 0.25                        # upper half (where not flattened against the wing) = CANOE_UP x the lower half
CANOE_AXIS_GAP = 0.005                 # canoe axis below the lower skin at 75 % chord (m)
CANOE_SPLIT_GAP = 0.005                # chord fraction between the fixed and the flap-carried part
CANOE_SURF_GAP = 0.0015                # canoe top under the skin it hangs from (m)


def canoe_law(t):
    """Meridian law of the canoes, 0..1 (1 at the deepest section), t = 0 nose .. 1 tail."""
    a, b = CANOE_SHAPE
    tm = a / (a + b)
    t = np.clip(np.asarray(t, float), 0.0, 1.0)
    return t ** a * (1.0 - t) ** b / (tm ** a * (1.0 - tm) ** b)


def canoe_plan(y, n=60):
    """Plan-view outline (x, half-width) of the canoe at butt line y (flaps retracted)."""
    sec = W.section_at(y)
    t = np.linspace(0.0, 1.0, n)
    return sec.le[0] + (CANOE_X[0] + CANOE_X[1] * t) * sec.chord, CANOE_HW * canoe_law(t)


def _canoe_profile(t0, t1, L, depth, n=40):
    """Meridian (x, r) over t in [t0, t1] of the canoe (canoe_law), closed by flat ends."""
    t = np.linspace(t0, t1, max(4, int(np.ceil(n * (t1 - t0))) + 1))
    r = depth * canoe_law(t)
    prof = list(zip(t * L, r))
    if r[0] > 1e-9:
        prof = [(t[0] * L, 0.0)] + prof
    if r[-1] > 1e-9:
        prof = prof + [(t[-1] * L, 0.0)]
    return prof


def _lower_surface_z(sec, x):
    xc = np.clip((x - sec.le[0]) / sec.chord, 0.0, 1.0)
    return sec.lower(xc)[:, 2]


def flap_canoes():
    """(fixed forward parts, {side: flap-carried aft parts}) of the flap-track canoes, flaps retracted."""
    fixed, aft = [], {"R": [], "L": []}
    x_split = W.FLAP_X_LO
    for y in FLAP_CANOE_Y:
        sec = W.section_at(y)
        x0 = sec.le[0] + CANOE_X[0] * sec.chord
        L = CANOE_X[1] * sec.chord
        zl = float(sec.lower(np.array(0.75))[2])
        ts = (x_split - CANOE_X[0]) / CANOE_X[1]
        ta = (x_split + CANOE_SPLIT_GAP - CANOE_X[0]) / CANOE_X[1]
        te = sec.le[0] + sec.chord
        for (t0, t1), dst in (((0.0, ts), "fixed"), ((ta, 1.0), "aft")):
            c = revolve(_canoe_profile(t0, t1, L, CANOE_DEPTH), n=40, axis_origin=(0, 0, 0), axis_dir=(1, 0, 0))
            zc = zl - CANOE_AXIS_GAP
            c = c.scaled((1.0, CANOE_HW / CANOE_DEPTH, 1.0), origin=(0, 0, 0)).translated((x0, y, zc))
            V = c.V.copy()
            V[:, 2] = np.where(V[:, 2] > zc, zc + CANOE_UP * (V[:, 2] - zc), V[:, 2])
            # flatten against the wing (fixed part) / the retracted flap's lower surface (aft part, = the section's
            # lower contour aft of the lip); aft of the trailing edge the tail stays round
            zs = _lower_surface_z(sec, V[:, 0]) - CANOE_SURF_GAP
            clamp = (V[:, 0] <= te) & (V[:, 2] > zs)
            V[:, 2] = np.where(clamp, zs, V[:, 2])
            c = Mesh(V, c.F)
            if dst == "fixed":
                fixed += [c, c.mirrored_y()]
            else:
                aft["R"].append(c)
                aft["L"].append(c.mirrored_y())
    return Mesh.merge(fixed), {k: Mesh.merge(v) for k, v in aft.items()}


# weather-radar pod: at the STARBOARD WING TIP, on the leading edge just inboard of the winglet (Pilatus drawing
# plan + front views; photos ngx_kenia_stbd_pilatus, pro3008_stbd34_pilatus; Pilatus tech-data front render).
# Round pod, black radome ahead of the joint, body faired into the winglet root.  PRO: radome enlarged for the
# 12-in GWX 8000 antenna -> R 0.165 (the NGX drawing shows 0.155).  Rev A had it at BL 3.90 (wrong).
POD_Y, POD_Z = 7.635, 1.760            # pod axis (butt line, water line)
POD_X_TIP, POD_X_JOINT = 5.150, 5.575
POD_R = 0.165
POD_NOSE_L = 0.305                     # elliptic nose length (tip -> full radius)
# VQA r2 (SHP2-02): the body does not end in a dome.  Photos IMG_0459 (from the cabin), N81DW (from below) and 048
# (from above) show the full-radius body running ~0.2 m aft of the radome joint and then tapering into a long 'swan
# neck' whose crown sweeps up into the winglet leading edge while its underside runs into the wing; the Pilatus plan
# view shows the pod's outboard side running aft to STA ~5.83 and curving into the winglet LE at STA ~6.0 / BL 7.75.
# The neck is a sweep along a spine (cubic Bezier) from the pod axis at POD_CYL_END (tangent +x) to a point inside
# the winglet's leading edge (section POD_NECK['sec'] of wing.winglet_sections(), on its chord line at 'frac' of the
# chord, tangent to the LE line), with circular sections normal to the spine whose radius falls from POD_R to
# 'r_end' (cosine law; the tangent lengths 't0' / 't1' shape the spine), so it ends hidden inside the winglet.
POD_CYL_END = 5.790                    # end of the cylindrical part (rev B 5.72, then an elliptic dome to 6.00)
POD_NECK = dict(sec=16, frac=0.07, r_end=0.010, t0=0.30, t1=0.24, q=1.3)


def radar_pod_profile(n=36):
    """(x, r) meridian of the pod's body of revolution (tip -> POD_CYL_END, x = station); the neck aft of it is
    pod_neck_rings()."""
    prof = []
    for x in np.linspace(POD_X_TIP, POD_CYL_END, n):
        if x < POD_X_TIP + POD_NOSE_L:
            r = POD_R * max(0.0, 1 - (1 - (x - POD_X_TIP) / POD_NOSE_L) ** 2) ** 0.5
        else:
            r = POD_R
        prof.append((float(x), float(r)))
    return prof


def pod_neck_spine(n=60):
    """Spine (n, 3) of the neck, its unit tangents (n, 3) and the section radius (n,) along it."""
    secs = W.winglet_sections()
    k = POD_NECK["sec"]
    sec = secs[k]
    B = sec.point(np.array(POD_NECK["frac"]), np.array(0.0))
    dle = secs[k + 1].le - secs[k - 1].le
    dle /= np.linalg.norm(dle)
    P0 = np.array([POD_CYL_END, POD_Y, POD_Z])
    P1 = P0 + [POD_NECK["t0"], 0.0, 0.0]
    P2 = B - POD_NECK["t1"] * dle
    u = np.linspace(0.0, 1.0, 400)[:, None]
    C = (1 - u) ** 3 * P0 + 3 * (1 - u) ** 2 * u * P1 + 3 * (1 - u) * u ** 2 * P2 + u ** 3 * B
    sl = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    t = np.linspace(0.0, 1.0, n)
    S = np.stack([np.interp(t * sl[-1], sl, C[:, i]) for i in range(3)], 1)
    T = np.gradient(S, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    re = POD_NECK["r_end"]
    r = re + (POD_R - re) * 0.5 * (1.0 + np.cos(np.pi * t ** POD_NECK["q"]))
    return S, T, r


def pod_neck_rings(n=60, m=48):
    """Section rings (n, m, 3) of the neck: circles of pod_neck_spine()'s radius normal to the spine, in a
    rotation-minimising frame that starts as the pod's (y, z) frame (so the first ring is the pod circle)."""
    S, T, r = pod_neck_spine(n)
    th = np.linspace(0, 2 * np.pi, m, endpoint=False)
    e1, e2 = np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    rings = []
    for i in range(n):
        if i:
            b = np.cross(T[i - 1], T[i])
            sb = np.linalg.norm(b)
            if sb > 1e-12:
                from cad.mesh import rotation_matrix
                R_ = rotation_matrix(b / sb, float(np.arctan2(sb, T[i - 1] @ T[i])))
                e1, e2 = R_ @ e1, R_ @ e2
        rings.append(S[i] + r[i] * (np.outer(np.cos(th), e1) + np.outer(np.sin(th), e2)))
    return np.array(rings)


def pod_outline(view="plan", nbin=120):
    """Closed silhouette of the whole pod (nose, cylinder and neck) in a view: 'plan' (x, y), 'side' (x, z) or
    'front' (y, z; the pod circle -- the neck lies behind it)."""
    if view == "front":
        a = np.linspace(0, 2 * np.pi, 97)
        return np.c_[POD_Y + POD_R * np.cos(a), POD_Z + POD_R * np.sin(a)]
    k = 1 if view == "plan" else 2
    c = POD_Y if view == "plan" else POD_Z
    prof = np.array(radar_pod_profile(80))
    Q = np.r_[np.c_[prof[:, 0], c + prof[:, 1]], np.c_[prof[:, 0], c - prof[:, 1]],
              pod_neck_rings(80, 72).reshape(-1, 3)[:, [0, k]]]
    u = Q[:, 0]
    ub = np.linspace(u.min(), u.max(), nbin + 1)
    idx = np.clip(np.digitize(u, ub) - 1, 0, nbin - 1)
    up, lo, uc = [], [], []
    for i in range(nbin):
        sel = idx == i
        if sel.any():
            uc.append(0.5 * (ub[i] + ub[i + 1]))
            up.append(Q[sel, 1].max())
            lo.append(Q[sel, 1].min())
    uc = np.array(uc)
    uc[0], uc[-1] = u.min(), u.max()
    P = np.r_[np.c_[uc, up], np.c_[uc[::-1], np.array(lo)[::-1]]]
    return np.vstack([P, P[:1]])


POD_X_END = float(pod_neck_spine(2)[0][-1, 0])      # aft end of the neck (inside the winglet)


def radar_pod(n_around=96):
    """(radome, body) meshes: body of revolution (radar_pod_profile) + the swan neck (pod_neck_rings), capped inside
    the winglet; fine enough (~11 mm) for the pod pinstripe (livery.POD_PIN)."""
    prof = [(x - POD_X_TIP, r) for x, r in radar_pod_profile(72)]
    prof[0] = (0.0, 0.0)
    body = revolve(prof, n=n_around, axis_origin=(POD_X_TIP, POD_Y, POD_Z), axis_dir=(1, 0, 0))
    R = pod_neck_rings(90, n_around)
    # the revolve's last ring and the neck's first are the same circle
    neck = grid_surface(R, close_v=True)
    if np.mean(np.sum((neck.V[:n_around] - R[0].mean(0)) * neck.N[:n_around], 1)) < 0:
        neck = neck.flipped()
    cap = cap_ring(R[-1], R[-1].mean(0) - R[-2].mean(0))
    body = Mesh.merge([body, neck, cap])
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


BEACON_TOP_X = 12.780           # red beacon on top of the bullet nose (its top stays under the 4.26 m bullet top)
BEACON_BELLY_X = 7.850          # red beacon on the keel, just aft of the wing-to-body fairing


def winglet_light_caps(sgn, split=0.45, lift=0.0008):
    """Nav (forward `split` of the chord) and strobe (aft) lenses on the winglet's top section, flush with its cap."""
    from model.wing import winglet_sections
    secs = winglet_sections()
    top, prev = secs[-1], secs[-2]
    d = top.le - prev.le
    d /= np.linalg.norm(d)
    out = []
    for a, b in ((0.0, split), (split, 1.0)):
        xx = cos_pts(24, a, b)
        loop = np.vstack([top.lower(xx[::-1]), top.upper(xx[1:-1])]) + lift * d
        m = cap_ring(loop, d)
        out.append(m if sgn > 0 else m.mirrored_y())
    return out


def build(parts):
    # -------- belly fairing (goes with the wing)
    bp = Part("belly_fairing", "Wing-to-body fairing: belly fairing + upper root fillet", "wing", explode=(0, 0, -0.9),
              group="Wing", material_note="Composite fairing over the wing carry-through and the root junction")
    bp.add(belly_fairing(), "paint_belly")            # recoloured by the livery (SURFACES['belly_fairing'])
    bp.add(root_fillet(), "paint_white")              # painted with the fuselage-side livery (livery.PAINTED)
    parts[bp.id] = bp
    boot_under_fillet(parts)

    # -------- flap track canoes
    fixed, aft = flap_canoes()
    cp = Part("flap_fairings", "Flap-track fairings, fixed forward parts (3 per side; the aft parts ride on the flaps)",
              "controls_wing", explode=(0.4, 0, -0.5),
              group="Flight controls", qty=6, material_note="Composite canoe fairings")
    cp.add(fixed, "paint_white")
    parts[cp.id] = cp
    for side in ("R", "L"):                       # aft canoe parts ride on the flap (child parts, no pivot of their own)
        if f"flap_{side}" in parts:
            ap = Part(f"flap_canoes_{side}", f"Flap-track fairings, aft parts on the {'right' if side == 'R' else 'left'}"
                      " flap (3)", "controls_wing", parent=f"flap_{side}", explode=(0.3, 0, -0.3),
                      group="Flight controls", qty=3, material_note="Composite canoe fairings, move with the flap")
            ap.add(aft[side], "paint_belly")              # recoloured by the livery (SURFACES['flap_fairings'])
            parts[ap.id] = ap

    # -------- weather radar pod (right wing)
    radome, body = radar_pod()
    rp = Part("radar_pod", "Weather-radar pod, right wing tip (GWX 8000, 12-in antenna)", "details",
              explode=(-0.7, 0.3, 0), group="Avionics", material_note="Radome enlarged on the PRO")
    rp.add(body, "paint_white").add(radome, "paint_belly")
    parts[rp.id] = rp

    # -------- lights (placed from the geometry: winglet top section, tail bullet, keel)
    reds, greens, whites = [], [], []
    for sgn, coll in ((1, greens), (-1, reds)):
        nav, strobe = winglet_light_caps(sgn)
        coll.append(nav)
        whites.append(strobe)
    T = np.array(E.BULLET)
    xe = T[-1, 0]
    whites.append(lens(np.array([xe - 0.012, 0, 0.5 * (T[-1, 1] + T[-1, 2])]), (0.012, 0.016, 0.016)))  # tail light
    xb = BEACON_TOP_X                                                                  # beacon on the bullet nose
    reds.append(lens(np.array([xb, 0, float(np.interp(xb, T[:, 0], T[:, 1])) - 0.006]), (0.040, 0.026, 0.022)))
    reds.append(lens(np.array([BEACON_BELLY_X, 0, float(F.z_bot(BEACON_BELLY_X)) + 0.006]), (0.05, 0.035, 0.022)))
    lp = Part("lights", "Navigation, strobe & beacon lights", "details", group="Lights",
              material_note="LED nav/strobe, red beacons")
    lp.add(Mesh.merge(reds), "light_red").add(Mesh.merge(greens), "light_green").add(Mesh.merge(whites), "light_white")
    parts[lp.id] = lp

    # -------- antennas
    ants = []
    top = lambda x: float(F.z_top(x)) - 0.004
    bot = lambda x: float(F.z_bot(x)) + 0.004
    ants.append(blade_antenna((5.25, 0, top(5.25)), 0.26, 0.20, 38))            # VHF COM 1
    ants.append(blade_antenna((8.70, 0, top(8.70)), 0.20, 0.16, 38))            # ELT / SATCOM (ahead of the dorsal)
    ants.append(blade_antenna((8.95, 0, bot(8.95)), 0.24, 0.18, 38, down=True))  # VHF COM 2
    ants.append(blade_antenna((8.35, 0, bot(8.35)), 0.10, 0.10, 20, down=True))  # transponder
    ants.append(blade_antenna((8.60, 0, bot(8.60)), 0.10, 0.10, 20, down=True))  # DME
    domes = [superellipsoid((4.70, 0, top(4.70) - 0.01), (0.09, 0.07, 0.035), (0.8, 0.9), 10, 14),
             superellipsoid((4.98, 0, top(4.98) - 0.01), (0.09, 0.07, 0.035), (0.8, 0.9), 10, 14),
             superellipsoid((8.40, 0, top(8.40) - 0.01), (0.07, 0.05, 0.03), (0.8, 0.9), 10, 14)]
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
