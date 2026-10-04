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
# (rev: (5.205, 1.162), (5.251, 1.213), (5.323, 1.288)).  The airstair has opened 145 deg since 2026-09-27 (photos
# 130 / 188): the swept wedge ends 35 deg outboard of the vertical, so the redrawn edge keeps clear with more margin
# (the builder's door limit, _airstair_sweep, moves the surface by <= 1.5 mm).
# VQA r3 (SHP3-01): the redrawn edge climbed 128 mm in 61 mm of STA ((5.345, 1.232) -> (5.406, 1.360), ~64 deg) from a
# knee at the door limit -- the fairing nose's upper part stood up as a steep face with a crease on that climb.  It now
# leaves the door limit gradually (max ~59 deg, no knee) and rejoins the drawn line at STA 5509; up to 30 mm under the
# CONS2-05 line over STA 5.37-5.44 (rev CONS2-05: (5.300, 1.180), (5.345, 1.232), (5.406, 1.360), (5.470, 1.407)).
BELLY_FAIRING_NOSE_EDGE = [(5.153, 1.052), (5.159, 1.082), (5.175, 1.119), (5.205, 1.148), (5.251, 1.168),
                           (5.300, 1.182), (5.335, 1.215), (5.370, 1.270), (5.406, 1.330), (5.440, 1.375),
                           (5.470, 1.402), (5.509, 1.432)]
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


def _belly_box_sdf(V, grow_down=0.0):
    """Signed distance-like field of the lower belly fairing's box (positive outside): flat bottom
    belly_fairing_bottom(x), footprint half-width belly_fairing_halfwidth(x) with the BELLY_FAIRING_FLAT corner radius;
    unbounded above (the walls end in the fuselage / fillet); outside BELLY_FAIRING_X it is positive.  grow_down: the
    bottom taken this much lower (so surfaces lying ON the flat bottom count as inside)."""
    V = np.asarray(V, float)
    x = V[:, 0]
    zb = belly_fairing_bottom(np.clip(x, BELLY_FAIRING_X[0], BELLY_FAIRING_HW[-1][0])) - grow_down
    hw = belly_fairing_halfwidth(np.clip(x, BELLY_FAIRING_X[0], BELLY_FAIRING_HW[-1][0]))
    r = np.minimum(BELLY_FAIRING_FLAT["r"], 0.9 * np.maximum(hw, 1e-3))
    qy = np.abs(V[:, 1]) - (hw - r)
    qz = (zb + r) - V[:, 2]
    d = np.hypot(np.maximum(qy, 0.0), np.maximum(qz, 0.0)) + np.minimum(np.maximum(qy, qz), 0.0) - r
    out = (x < BELLY_FAIRING_X[0]) | (x > BELLY_FAIRING_HW[-1][0])
    return np.where(out, 1.0, d)


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
# Nose half (ahead of the mid-chord), VQA r3 SHP3-01 / RQ3-01: above the foot the section is the concave elliptic fillet
# with a round-over at the foot, P_up(u) = 1 - sqrt(u (2 - u)) s(u / e) (s = C2 smoothstep): e is the round-over's
# share of the foot -> upper-edge height, from e_nose near the nose tip down to e_le at the wing LE (there the wing's
# own LE radius takes over) and to 0 within 'behind' aft of the LE, where the fillet sits on the wing.  So the nose is
# one round crest (vertical tangent at the foot, meeting the round lower half G1) that runs into the wing leading edge,
# with a smooth concave run-out into the fuselage side above it -- photo 0517: 'a smooth, slightly concave fillet'
# between the max-standoff line and the upper edge.  (rev r2 / r3: a convex bump (1 - u)^k (1 + k u) ahead of the LE,
# blended into the fillet over 0.08 / 0.2 m behind it: the bump either stood up as a ridge or left a dome on the wing,
# and its blend with the fillet (infinite slope at the foot) creased the foot line -- the knotted highlight of the
# hero / apron renders.)
ROOT_FILLET_ROUND = dict(e_nose=0.90, e_le=0.25, run=0.20, behind=0.10)   # run: m ahead of the LE over which e falls
ROOT_FILLET_TAIL_K = 3.0           # tail bump law (1 - u)^k (1 + k u) behind the wing TE (ROOT_FILLET_TE_BLEND; rev r2 k 2:
#                                    a sharper fold where the fillet turns back into the bump)
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
    edge, z_lo lower edge, a = weight of the fillet law vs the tail bump behind the TE; 1 over the nose half)."""
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
    # nose half: ROOT_FILLET_ROUND (in root_fillet_standoff), a = 1; aft half: the fillet law, turning back into the
    # round bump over ROOT_FILLET_TE_BLEND behind the wing's trailing edge at the (faded) foot -- with no wing left to
    # be tangent to, the fillet met its closure below the foot in a 90 deg crease along the TE (MQ2-01)
    yf = F.side_y(np.clip(x, F.STA["cowl_front"], F.STA["tail_end"]), zj) + S
    te_f = np.interp(yf, ys, le + ch)
    b0, b1 = ROOT_FILLET_TE_BLEND
    a_te = 1.0 - _smooth((x - te_f + b0) / (b0 + b1))
    a = np.where(x > 0.5 * (xp0 + Pp[-1, 0]), a_te, 1.0)
    return zj, S, zu, zl, a


# VQA r3 (SHP2-06 / RQ2-02): the foot standoff S peaks at the wing LE (0.29 m at STA 5.39 against the 0.235 m plateau
# aft: the drawn plan edge turns out along the LE while the foot is still at the low LE WL, where the fuselage is
# narrow) -- above the foot that peak stood out as a dome over the LE with a groove behind it (zebra test).  Above the
# foot the law uses S_up = S's monotone envelope from aft (running minimum, smoothed) plus the excess S - S_up decaying
# as (1 - u)^k (1 + k u), k = ROOT_FILLET_PEAK_DECAY, so the foot (plan edge on the wing) is unchanged and the dome
# fades out upward with no slope kink at the foot (VQA r3; rev (1 - u)^6).
ROOT_FILLET_PEAK_DECAY = 12.0
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


def _visible_foot(x, zj):
    """The VISIBLE foot WL z0 at stations x: inside the chord, where the smoothed foot zj lies under the wing's upper
    surface at the plan edge (just aft of the LE nose, up to 10 mm at STA 5.40), that surface (soft max, 2 mm); zj
    elsewhere.  The fillet law runs from z0, so the fillet meets the wing tangentially ON the drawn plan edge (VQA r3:
    measured from the buried foot the concave law had already fallen ~30 mm inboard where it came out of the wing)."""
    Pp = np.array(BELLY_FAIRING_PLAN)
    yo = root_fillet_lines()[2](np.clip(x, Pp[0, 0], Pp[-1, 0]))
    zt, fch = wing_top(x, yo)
    kz = 0.002
    w = 1.0 - _smooth((np.asarray(x, float) - 5.8) / 0.4)      # the LE region only (aft the two agree to ~1 mm)
    return np.where(fch <= 0.0, zj + w * kz * np.logaddexp(0.0, (zt - zj) / kz), zj)


def root_fillet_standoff(x, z):
    """Horizontal standoff d(x, z) >= 0 of the fillet / fairing nose from the fuselage side (starboard)."""
    x0, x1 = root_fillet_lines()[3]
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    zj, S, zu, zl, a = _fillet_frame(x)
    Pp = np.array(BELLY_FAIRING_PLAN)
    yo = root_fillet_lines()[2](np.clip(x, Pp[0, 0], Pp[-1, 0]))
    z0 = _visible_foot(x, zj)
    u = np.clip((z - z0) / np.maximum(zu - z0, 1e-6), 0.0, 1.0)
    v = np.clip((zj - z) / np.maximum(zj - zl, 1e-6), 0.0, 1.0)
    root = np.sqrt(np.clip(u * (2.0 - u), 0.0, 1.0))
    fil = 1.0 - root                                        # concave elliptic fillet (tangent to wing and side)
    k_ = ROOT_FILLET_TAIL_K                                 # aft of the TE: a round bump (zero slope at the foot and
    bump = (1.0 - u) ** k_ * (1.0 + k_ * u)                 # at the upper edge)
    # nose half: the fillet with a round-over at the foot (ROOT_FILLET_ROUND)
    q = ROOT_FILLET_ROUND
    ys_, le_, _, _ = _wing_top_table()
    le_o = np.interp(yo, ys_, le_)
    e = np.where(x <= le_o, q["e_le"] + (q["e_nose"] - q["e_le"]) * _smooth((le_o - x) / q["run"]),
                 q["e_le"] * (1.0 - _smooth((x - le_o) / q["behind"])))
    t_ = np.clip(u / np.maximum(e, 1e-9), 0.0, 1.0)
    s_ = np.where(e > 1e-9, t_ ** 3 * (10.0 - 15.0 * t_ + 6.0 * t_ * t_), 1.0)
    P_up = np.where(x <= 0.5 * (Pp[0, 0] + Pp[-1, 0]), 1.0 - root * s_, a * fil + (1.0 - a) * bump)
    # below the foot (kept only outside the chord): the bump's round lower half (nose; tail behind the TE)
    P = np.where(z >= zj, P_up, np.sqrt(np.clip(1.0 - v * v, 0.0, 1.0)))
    if ROOT_FILLET_PEAK_DECAY:
        # decay measured from the VISIBLE foot z0 (above), so the plan edge on the wing keeps the full standoff
        ue = u
        Su = _standoff_envelope(x)
        kd = ROOT_FILLET_PEAK_DECAY                  # (1 - u)^k (1 + k u): zero slope at the foot (VQA r3: the
        g = (1.0 - ue) ** kd * (1.0 + kd * ue)       # rev (1 - u)^6 dropped linearly -- a crease along the foot line)
        S = np.where(z >= zj, Su + (S - Su) * g, S)
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
    z0 = _visible_foot(xs, zj)                                 # the upper rows start at the visible foot
    tu = np.linspace(0.0, 1.0, n_up) ** 2                      # u rows, clustered at the foot
    tv = 1.0 - (1.0 - np.linspace(0.0, 1.0, n_lo)) ** 2        # v rows, clustered at the lower edge
    out = []
    for rows, zfun in ((tu, lambda t: z0[:, None] + (zu - z0)[:, None] * t[None, :]),
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
            # ... and outside the lower belly fairing: under the nose the lobe hugs the fuselage bottom 1-3 mm inside
            # the fairing's flat bottom (hidden, but its keel corner folded 60-80 deg in the mesh, VQA r3 RQ3-01)
            if m.nf:
                m = trim(m, _belly_box_sdf(m.V, grow_down=0.004) + 0.0015, "positive")
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
# review r2 RES2-01d: the axis runs straight at CANOE_AXIS_GAP under the skin at 75 % chord, so towards the nose (the
# lower skin drops ~6 cm forward of it) the first quarter metre of the body lay inside the wing and was flattened
# onto the skin into a zero-thickness sheet with spiky normals -- a dark artefact at every canoe's tip.  The axis now
# hangs CANOE_NOSE_DROP under the clamp height where it would rise above it (soft, CANOE_NOSE_SOFT; aft of the
# canoe's emergence it stays where it was, < 0.3 mm) and the lower half keeps at least CANOE_NOSE_DEPTH of its radius
# below that axis, so the nose is a real tapering body closing a few mm under the skin (the plan outline L5 draws,
# canoe_plan, unchanged)
CANOE_NOSE_DROP = 0.002                # m: nose axis under the clamp height
CANOE_NOSE_SOFT = 0.001                # m: softness of that drop
CANOE_NOSE_DEPTH = 0.4                 # lower half at the nose: >= this x the radius below the axis
CANOE_NOSE_BLEND = 0.15                # softness of the maximum of the two depths (x the radius: no crease, and
#                                        the lower half aft of the nose stays as it was to 0.3 %)


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


def _crease_split(m, top):
    """m with the faces lying flat on the skin (all three vertices flattened: `top`) as their own patch: the canoe body
    and its flattened top each carry their own normals, a crisp edge where the body meets the skin (review r3 RES3-04:
    averaged across that edge the body's vertex normals leaned up to ~45 deg off their faces -- the flap fairings 15 %
    and the canoes 12 % 'faceted' -- and drew a soft false highlight along the junction)."""
    ft = top[m.F].all(1)
    out = []
    for sel in (ft, ~ft):
        if not sel.any():
            continue
        F_ = m.F[sel]
        used = np.unique(F_)
        remap = np.full(len(m.V), -1, int)
        remap[used] = np.arange(len(used))
        out.append(Mesh(m.V[used], remap[F_]))
    return Mesh.merge(out)


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
            zs = _lower_surface_z(sec, V[:, 0]) - CANOE_SURF_GAP
            # the nose (RES2-01d, above): axis za, lower half depth D (>= CANOE_NOSE_DEPTH x the radius)
            r = CANOE_DEPTH * canoe_law((V[:, 0] - x0) / L)
            k, kb = CANOE_NOSE_SOFT, CANOE_NOSE_BLEND * np.maximum(r, 1e-9)
            za = zc - k * np.logaddexp(0.0, (zc - (zs - CANOE_NOSE_DROP)) / k)
            D = kb * np.logaddexp((r - (zc - za)) / kb, CANOE_NOSE_DEPTH * r / kb)     # soft max of the two depths
            dz = V[:, 2] - zc
            V[:, 2] = np.where(dz > 0, za + CANOE_UP * dz, za + dz / np.maximum(r, 1e-9) * D)
            # flatten against the wing (fixed part) / the retracted flap's lower surface (aft part, = the section's
            # lower contour aft of the lip); aft of the trailing edge the tail stays round
            clamp = (V[:, 0] <= te) & (V[:, 2] > zs)
            V[:, 2] = np.where(clamp, zs, V[:, 2])
            c = _crease_split(Mesh(V, c.F), clamp)
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
POD_CYL_END = 5.790                    # end of the cylindrical part (rev B 5.72, then an elliptic dome to 6.00)
# VQA r2 (SHP2-02) found the rev B elliptic dome too short (photos IMG_0459 from the cabin, N81DW from below, 048 from
# above: the full-radius body runs on aft of the radome joint and fairs into the winglet / wing); rev r2 answered with a
# 'swan neck' bent up into the winglet leading edge, which from below read as a short capsule with an up-turned elbow
# and from the cabin as a waisted neck.  VQA r3: the photos show the body running on STRAIGHT aft under the winglet
# root as a long tapering tail (N81DW: ~1.5 radome lengths behind the joint, its underside fading into the winglet
# lower skin; 0459: the crown line straight from the radome to where the winglet leading edge rises out of it; the
# Pilatus plan view: the outboard side running aft to STA ~5.83 and meeting the winglet LE at ~6.0 / BL 7.75).
# The tail: r = POD_R (1 - u^p)^q, u = 0 at POD_CYL_END .. 1 at x_end (pod_tail_r); the winglet rises out of it.
POD_TAIL = dict(x_end=6.60, p=2.2, q=0.7)


def pod_tail_r(x):
    """Radius of the straight tail (POD_TAIL) at stations x (POD_R ahead of POD_CYL_END, 0 aft of x_end)."""
    q = POD_TAIL
    u = np.clip((np.asarray(x, float) - POD_CYL_END) / (q["x_end"] - POD_CYL_END), 0.0, 1.0)
    return POD_R * (1.0 - u ** q["p"]) ** q["q"]


def radar_pod_profile(n=36, tail=True):
    """(x, r) meridian of the pod's body of revolution (tip -> POD_CYL_END, x = station; tail=True: on through the
    straight tail (pod_tail_r) to its point at POD_TAIL['x_end'])."""
    prof = []
    for x in np.linspace(POD_X_TIP, POD_CYL_END, n):
        if x < POD_X_TIP + POD_NOSE_L:
            r = POD_R * max(0.0, 1 - (1 - (x - POD_X_TIP) / POD_NOSE_L) ** 2) ** 0.5
        else:
            r = POD_R
        prof.append((float(x), float(r)))
    if tail:
        xs = POD_CYL_END + (POD_TAIL["x_end"] - POD_CYL_END) * np.sin(np.linspace(0, np.pi / 2, n))[1:]
        prof += [(float(x), float(pod_tail_r(x))) for x in xs]
    return prof


def pod_outline(view="plan", nbin=120):
    """Closed silhouette of the whole pod (nose, cylinder and tapering tail) in a view: 'plan' (x, y), 'side' (x, z) or
    'front' (y, z; the pod circle -- the tail lies behind it)."""
    if view == "front":
        a = np.linspace(0, 2 * np.pi, 97)
        return np.c_[POD_Y + POD_R * np.cos(a), POD_Z + POD_R * np.sin(a)]
    k = 1 if view == "plan" else 2
    c = POD_Y if view == "plan" else POD_Z
    prof = np.array(radar_pod_profile(80, tail=True))
    Q = np.r_[np.c_[prof[:, 0], c + prof[:, 1]], np.c_[prof[:, 0], c - prof[:, 1]]]
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


POD_X_END = POD_TAIL["x_end"]                         # aft end of the tail (under the winglet)


def radar_pod(n_around=192):
    """(radome, body) meshes: body of revolution (radar_pod_profile: nose, cylinder, straight tapering tail) that runs
    on under the winglet root; fine enough (~5 mm round, ~6 mm along) for the 10 mm pod pinstripe (livery.POD_PIN;
    VQA r3: the rev ~11 mm grid would break a 10 mm band into dashes)."""
    prof = [(x - POD_X_TIP, r) for x, r in radar_pod_profile(120, tail=True)]
    prof[0] = (0.0, 0.0)
    prof[-1] = (prof[-1][0], 0.0)
    body = revolve(prof, n=n_around, axis_origin=(POD_X_TIP, POD_Y, POD_Z), axis_dir=(1, 0, 0))
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


# ---- cowling panel lines, latches, oil-cooler exit and vent (VQA r3 RQ3-09; photo 188, MSN 3008 port nose close-up
# through the fitted camera nose_188: the cowl and forward fuselage are not one seamless skin).  Measured on 188:
#   * ring joints (constant STA, over the sides and the top; the nose-bay opening under STA 3.0 is left clear): the
#     cowling's aft edge at the firewall (STA 3.0) and the forward cowl ring's joint just aft of the exhaust stacks
#     (STA ~2.0);
#   * the upper / lower cowling split with its latches at WL ~1.60 between them (latch outlines ~26 x 88 mm at STA
#     ~2.21 / 2.72);
#   * the lower oil-cooler exit on the port lower cowl (a dark recess under a straight lip, STA 2.12-2.40, 35 mm tall
#     at its forward end, 92 mm at the aft end, lip WL 1.487) and a round louvred vent (~75 mm, STA ~2.80, WL ~1.48)
#     -- port side only (seen in 188; no starboard close-up).
# The ring joints and the split line are real grooves in the skin (review r3 RES3-01, COWL_GROOVES: the joints had
# been painted-on dark lines): a slot COWL_SEAMS['width'] wide cut out of the cowl skin, its walls -- painted with the
# skin by the livery -- COWL_GROOVES['depth'] deep, a dark sealant floor ('seam'); the firewall joint (STA 3.00, the
# cowl's aft edge against the forward fuselage) is the slot's width on the cowl side, walled on both.  The latch
# outlines (26 x 88 mm, smaller than a skin cell) and the louvred vent stay painted-on dark lines COWL_SEAMS['width']
# (latches 0.6 x) wide, 'lift' proud of the skin; the louvre is its dark opening on the skin under a small raised lip.
COWL_SEAMS = dict(rings=(2.00, 3.00), split_wl=1.600, split_x=(2.00, 3.00), width=0.0025, lift=0.0004,
                  bottom_gap=(0.44, 0.56), latches=((2.21, 1.620), (2.72, 1.625)), latch=(0.026, 0.088, 0.006))
# final judge r1 LIV-F1-03: the 280 x 92 mm pure-black patch read as a pasted decal next to photo 188's small recessed
# slot with lit lips -> ~30 % smaller (about its aft end, which the lip line keeps), the opening a dark GREY recess
# ('vent_dark') with a shadow band under the lip ('inlet_dark', the upper 40 %)
COWL_GROOVES = dict(depth=0.0012)
OIL_COOLER_EXIT = dict(x=(2.20, 2.40), top=1.487, h_fwd=0.025, h_aft=0.064, lip=(0.006, 0.003), side=-1, shade=0.40)
COWL_VENT = dict(x=2.80, wl=1.480, r=0.037, slats=4, side=-1)


def _oml_frame(x, z, side):
    """(point, outward normal, e_x-ish tangent, e_z-ish tangent) on the fuselage side at (x, z), side +-1."""
    x, z = np.asarray(x, float), np.asarray(z, float)
    h = 1e-4
    y = F.side_y(x, z)
    dyx = (F.side_y(x + h, z) - F.side_y(x - h, z)) / (2 * h)
    dyz = (F.side_y(x, z + h) - F.side_y(x, z - h)) / (2 * h)
    P = np.stack([x, side * y, z], -1)
    tx = np.stack([np.ones_like(x), side * dyx, np.zeros_like(x)], -1)
    tz = np.stack([np.zeros_like(x), side * dyz, np.ones_like(x)], -1)
    n = np.cross(tz, tx) * side
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    tx /= np.linalg.norm(tx, axis=-1, keepdims=True)
    tz /= np.linalg.norm(tz, axis=-1, keepdims=True)
    return P, n, tx, tz


def _surface_ribbon(P, N, w, lift):
    """Ribbon (Mesh) of width w along the polyline P (n, 3) lying on the surface with normals N, lifted by lift."""
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1), 1e-12)[:, None]
    B = np.cross(N, T)
    B /= np.maximum(np.linalg.norm(B, axis=1), 1e-12)[:, None]
    Q = P + lift * N
    m = grid_surface(np.stack([Q - 0.5 * w * B, Q + 0.5 * w * B], 1))
    if np.mean(m.face_normals() @ N.mean(0)) < 0:
        m = m.flipped()
    return m


def cowl_seams():
    """(upper, lower) seam-line meshes of the cowling (COWL_SEAMS, split at the model's cowl split WL)."""
    q = COWL_SEAMS
    out = []
    for side in (1, -1):                                    # the latch outlines (the joints are grooves: cowl_grooves)
        lw, lh, lr = q["latch"]
        for xc, zc in q["latches"]:
            a = np.linspace(0, 2 * np.pi, 80)
            u = np.clip(np.cos(a) * 1.4, -1, 1) * (0.5 * lw)          # a rounded rectangle outline
            v = np.clip(np.sin(a) * 1.15, -1, 1) * (0.5 * lh)
            P, N, _, _ = _oml_frame(xc + u, zc + v, side)
            P = np.vstack([P, P[:1]])
            N = np.vstack([N, N[:1]])
            out.append(_surface_ribbon(P, N, 0.6 * q["width"], q["lift"]))
    # round louvred vent (port): ring + slats
    v = COWL_VENT
    a = np.linspace(0, 2 * np.pi, 72)
    P, N, _, _ = _oml_frame(v["x"] + v["r"] * np.cos(a), v["wl"] + v["r"] * np.sin(a), v["side"])
    out.append(_surface_ribbon(P, N, q["width"], q["lift"]))
    for k in range(v["slats"]):
        zz = v["wl"] + v["r"] * (-0.75 + 1.5 * k / max(v["slats"] - 1, 1))
        hw = np.sqrt(max(v["r"] ** 2 - (zz - v["wl"]) ** 2, 0.0)) - 0.004
        xs = np.linspace(v["x"] - hw, v["x"] + hw, 12)
        P, N, _, _ = _oml_frame(xs, np.full(len(xs), zz), v["side"])
        out.append(_surface_ribbon(P, N, 1.8 * q["width"], q["lift"]))
    m = Mesh.merge(out)
    zc = F.PROP_AXIS_Z + 0.02                               # the parts' split (fuselage_parts.build)
    return trim(m, m.V[:, 2] - zc, "positive"), trim(m, m.V[:, 2] - zc, "negative")


def groove_fields():
    """The cowl joints of COWL_SEAMS as slots: per groove the half-space fields (negative inside) whose intersection is
    the slot -- the ring joints at constant STA over the sides and top (not across the nose-bay opening under the
    keel: |BL| < the section's BL at bottom_gap), the firewall joint on the cowl side of STA 3.00, the upper / lower
    split line at split_wl between the rings."""
    q = COWL_SEAMS
    w = q["width"]
    xf = float(F.STA["firewall"])
    out = []
    for xr in q["rings"]:
        yg = abs(float(F.section(np.array([xr]), np.array([q["bottom_gap"][0]]))[0, 1]))
        x0, x1 = (xr - w, xr + 1.0) if xr >= xf - 1e-9 else (xr - 0.5 * w, xr + 0.5 * w)
        out.append([lambda V, a=x0: a - V[:, 0], lambda V, b=x1: V[:, 0] - b,
                    lambda V, g=yg: np.minimum(g - np.abs(V[:, 1]), F.PROP_AXIS_Z - V[:, 2])])
    z0, z1 = q["split_wl"] - 0.5 * w, q["split_wl"] + 0.5 * w
    out.append([lambda V: z0 - V[:, 2], lambda V: V[:, 2] - z1,
                lambda V: q["split_x"][0] - V[:, 0], lambda V: V[:, 0] - q["split_x"][1]])
    return out


def _slot(m, fields):
    """(inside every field, the rest) of m by sequential single-sided trims (fields re-evaluated on each piece)."""
    piece, outs = m, []
    for f in fields:
        v = f(piece.V)
        if not (v < 0).any():
            return None, m
        if (v >= 0).any():
            outs.append(trim(piece, v, "positive"))
            piece = trim(piece, v, "negative")
        if piece.nf == 0:
            return None, m
    outs = [o for o in outs if o.nf]
    return piece, (Mesh.merge(outs) if outs else None)


def _open_edges(m):
    """Directed boundary edges (a, b) of m with the third vertex c of their face, internal seams (an edge whose
    reverse is a boundary edge at the same positions: duplicated cut vertices between merged pieces) left out."""
    F_ = m.F
    e = np.vstack([F_[:, [0, 1]], F_[:, [1, 2]], F_[:, [2, 0]]])
    c = np.concatenate([F_[:, 2], F_[:, 0], F_[:, 1]])
    key = np.sort(e, 1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    b = cnt[inv.ravel()] == 1
    e, c = e[b], c[b]
    q = np.round(m.V / 1e-8).astype(np.int64)
    fwd = {(tuple(q[i]), tuple(q[j])) for i, j in e}
    keep = np.array([(tuple(q[j]), tuple(q[i])) not in fwd for i, j in e], bool) if len(e) else np.zeros(0, bool)
    return e[keep], c[keep]


def _walls(m, e, c, depth, toward_c):
    """Groove walls hanging `depth` along -N from the edges e (with face apexes c) of m: one strip mesh (shared
    vertices along it, smooth along / flat across), facing away from (toward_c=False) or toward the face side."""
    if not len(e):
        return None
    used = np.unique(e)
    loc = np.full(len(m.V), -1, int)
    loc[used] = np.arange(len(used))
    top = m.V[used]
    bot = top - depth * m.N[used]
    n = len(used)
    a, b = loc[e[:, 0]], loc[e[:, 1]]
    F_ = np.vstack([np.stack([a, b, b + n], 1), np.stack([a, b + n, a + n], 1)])
    V = np.vstack([top, bot])
    fn = np.cross(V[F_[:, 1]] - V[F_[:, 0]], V[F_[:, 2]] - V[F_[:, 0]])
    side = np.einsum("ij,ij->i", fn, np.tile(m.V[c] - m.V[e[:, 0]], (2, 1)))
    flip = (side < 0) if toward_c else (side > 0)
    F_[flip] = F_[flip][:, ::-1]
    UV = None if m.UV is None else np.vstack([m.UV[used], m.UV[used]])
    w = Mesh(V, F_, UV=UV)
    return w


def cowl_grooves(m):
    """Cut the cowl joints (groove_fields) into the skin mesh m: (skin with the slots cut out and their walls, the
    slots' floor) -- the walls carry the skin's material (the livery paints them with it), the floor is the dark seam;
    (m, None) where no groove crosses m."""
    depth = COWL_GROOVES["depth"]
    groups = groove_fields()
    removed, rest = [], m
    for fields in groups:
        piece, r = _slot(rest, fields)
        if piece is None:
            continue
        removed.append(piece)
        rest = r
    if not removed:
        return m, None
    allf = [f for fs in groups for f in fs]
    on = np.zeros(len(rest.V), bool)
    for f in allf:
        on |= np.abs(f(rest.V)) < 1e-9
    e, c = _open_edges(rest)
    sel = on[e[:, 0]] & on[e[:, 1]]
    walls = [_walls(rest, e[sel], c[sel], depth, toward_c=False)]
    # the firewall joint: the slot's aft edge is the cowl's own end (STA 3.00), walled too (the fuselage side)
    xf = float(F.STA["firewall"])
    for p in removed:
        ep, cp = _open_edges(p)
        at = (np.abs(p.V[ep[:, 0], 0] - xf) < 1e-6) & (np.abs(p.V[ep[:, 1], 0] - xf) < 1e-6)
        walls.append(_walls(p, ep[at], cp[at], depth, toward_c=True))
    floor = Mesh.merge(removed)
    floor = Mesh(floor.V - depth * floor.N, floor.F, floor.N.copy(), floor.UV)
    return Mesh.merge([rest] + [w for w in walls if w is not None]), floor


def oil_cooler_exit(n=24):
    """(lip, dark opening) of the oil-cooler exit louvre (OIL_COOLER_EXIT): the opening is the dark recess seen in 188
    -- a quadrilateral, narrow at its forward end and 'h_aft' tall at the aft end x1 below the straight upper lip at
    WL 'top' -- lying on the skin; the lip is a small raised strip along its upper edge."""
    q = OIL_COOLER_EXIT
    x0, x1 = q["x"]
    xs = np.linspace(x0, x1, n)
    t = (xs - x0) / (x1 - x0)
    zt = np.full(n, q["top"])
    zb = q["top"] - (q["h_fwd"] + (q["h_aft"] - q["h_fwd"]) * t ** 0.8)
    holes = []
    fs = q.get("shade", 0.0)
    for f0, f1 in (((0.0, fs), (fs, 1.0)) if fs else ((0.0, 1.0),)):
        rows = [_oml_frame(xs, zt + f * (zb - zt), q["side"]) for f in np.linspace(f0, f1, 4)]
        P = np.stack([r[0] + 0.0005 * r[1] for r in rows], 1)
        hole = grid_surface(P)
        if np.mean(hole.face_normals() @ rows[0][1].mean(0)) < 0:
            hole = hole.flipped()
        holes.append(hole)
    Pl, Nl, _, Tz = _oml_frame(xs, zt + 0.5 * q["lip"][0], q["side"])
    lip = _surface_ribbon(Pl, Nl, q["lip"][0], q["lip"][1])
    return lip, holes


def build(parts):
    # -------- cowling panel lines, latches, vent, oil-cooler exit (VQA r3 RQ3-09)
    if "cowl_upper" in parts and "cowl_lower" in parts:
        for pid in ("cowl_upper", "cowl_lower"):      # the joints as grooves in the skin (RES3-01)
            new = []
            for m, mat in parts[pid].meshes:
                if mat == "paint_white":
                    m, floor = cowl_grooves(m)
                    if floor is not None:
                        new.append((floor, "seam"))
                new.insert(0, (m, mat)) if mat == "paint_white" else new.append((m, mat))
            parts[pid].meshes = new
        up, lo = cowl_seams()
        parts["cowl_upper"].add(up, "seam")
        parts["cowl_lower"].add(lo, "seam")
        lip, holes = oil_cooler_exit()
        parts["cowl_lower"].add(lip, "paint_white").add(holes[0], "inlet_dark")
        for h in holes[1:]:
            parts["cowl_lower"].add(h, "vent_dark")

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
