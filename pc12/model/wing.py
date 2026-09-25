"""
PC-12 wing: tapered, (almost) unswept quarter-chord, LS(1)-0417MOD root -> LS(1)-0313 tip,
single-piece Fowler flap, aileron with Flettner geared balance tab, blended winglet,
pneumatic de-ice boots, flap-track fairings.

Planform (Stage 2, rev B): taken from the Pilatus NGX model drawing 190.10.40.432 (plan view,
registered to model coordinates by refs/mbp.py), which is the primary geometric source:
    leading edge   x = 5.3302 + 0.0400 y          (straight, 2.3 deg sweep; BL 1000 -> STA 5370)
    trailing edge  x = 7.5666 - 0.1139 y          (flap span), kinked at the flap / aileron junction
                   BL 5680 to 0.0771 / m outboard (constant 440 mm aileron chord)
    tip rib        BL 7430 (winglet root), chord 1,151 mm (1,087 mm on the straight trailing edge)
    -> root chord 2,224 mm at BL 0 (solved, see below; the drawn lines give 2,236), taper 0.489
       (straight trailing edge), MAC 1,724 mm at BL 3,306 (panel 0..7430, kink included),
       LEMAC STA 5,462, quarter chord of the MAC STA 5,893 (the drawing's wing reference line,
       2,820 aft of FR10, is STA 5,901; the quarter-chord line is within 12 mm of it root to tip).
    Reference area: the published 25.81 m^2 is reproduced (0.1 %) by the drawing's TOTAL projected
    plan area -- both halves through the fuselage, including the aileron trailing-edge kink and the
    winglets' plan projection -- so AREA_REF is held by solving the root chord with that definition
    (planform_area()).  The earlier rev A planform was solved from an assumed 46 % MAC aft-CG limit
    (LEMAC 5.323); against the drawing that put the wing 130-160 mm too far forward.  The POH aft CG
    limit STA 6,107 now lies at 37 % MAC.
Heights (front view of the drawing + its wing sections WR1-WR4): the wing chord plane has 6.23 deg
dihedral from BL 700 outboard, with a flat carry-through inside the fuselage (quarter chord at WL 1,023).
The drawing's WR dimension line reads 5.0 deg, but the drawn upper / lower surfaces and the Pilatus front
render both give ~6 deg: least-squares fit of the front-view upper / lower silhouettes BL 1300-7300 with the
rev B airfoils, rms 1.7 mm, max 3.1 mm (with the rev A airfoils the fit had given 6.15 deg / WL 1,036).
Incidence +1.45 deg at BL 0 -> -0.91 at BL 5.56 -> -2.64 at the tip (WR1 +1.05, WR2 -0.91, WR3 -1.88,
WR4 -2.61 deg measured LE-TE on the drawn sections).
Sections: LS(1)-0417MOD root -> LS(1)-0313 tip (model/airfoil.py, rev B: CST fits to the drawn WR1-WR4, each
normalised by its own LE / TE; our outlines within 3.9 mm of every drawn section), blended linearly in span
from BL 600 to the tip rib (airfoil_at).
Winglet: cant, bend and plan shape as drawn (51 deg from vertical, 0.77 m bend radius); the drawing's
span is 16.137 m (label 16.114 m) against the official 16.28 m -- the wing panel is kept as drawn and the
straight part of the winglet is lengthened (72 mm per side laterally) so the outer skin reaches BL 8,140.  That
also lifts the winglet top ~47 mm above the drawn WL 2,133: an ACCEPTED fixed-fact deviation pending the owner's
decision (the alternative, a 7,502 panel semi-span, puts the top within 4 mm but the tip rib / aileron end 72 mm
outboard; no split keeps both within 20 mm -- sheet L4, note 5).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, trim, planar_cap, grid_surface, cap_ring, superellipsoid, rotation_matrix, band
from model.airfoil import ls0417mod, ls0313, naca00
from model.lifting import Section, skin, strip, curve_patch, closed_body, bezier, cos_pts
from model.parts import Part

# ---- design constraints (official data) ---------------------------------
SPAN_TOTAL = 16.28          # m, over the winglets (Pilatus)
AREA_REF = 25.81            # m^2 (Pilatus); total projected plan area, see planform_area()
AFT_CG = 6.107              # m aft of datum at MTOW (POH); reference only (no longer sets the planform)
AFT_CG_MAC = 0.46           # rev A assumption (the drawing's planform puts STA 6.107 at 37 % MAC)

# ---- planform (Stage 2 fit to the Pilatus drawing, plan view) ------------
SEMI = 7.430                # tip-rib butt line = winglet root (drawn BL 7,430)
X_LE0 = 5.3302              # leading-edge station extrapolated to BL 0
LE_SWEEP = np.arctan(0.0400)  # straight leading edge (dx/dy = 0.040)
TAPER = 0.4887              # tip / root chord of the straight-trailing-edge trapezoid
Y_KINK = 5.680              # trailing-edge kink at the flap / aileron junction
TE_KINK = 0.0368            # outboard of Y_KINK the trailing edge sweeps back 0.0368 m/m less

# ---- winglet ("PC-21 style", Series 10A onward; POPA variant guide) ------------
# Shape from the drawing (front + plan + side views): large-radius blend from the wing's dihedral into
# a straight part canted 51 deg from vertical; chord 1.15 m at the tip rib -> 0.74 m at the end of the
# blend -> 0.37 m at the top; trailing edge sweeps back 0.26 m, mostly on the straight part.  Fitted with the
# drawn outer extreme (BL 8,050); the straight part is then lengthened to the official span.
WL_BEND_R = 0.770
WL_CANT = np.radians(51.0)       # from vertical, outward
WL_MID_CHORD = 0.740             # chord at the end of the blend
WL_TIP_CHORD = 0.370
WL_TE_SWEEP = 0.260              # trailing edge moves aft by this much tip-to-top (m)
WL_TE_EXP = 2.35                 # ... as (s / L)^WL_TE_EXP of the path length
WL_TIP_AF_T = 0.09               # winglet top section NACA 0009
WL_LE_SWEEP = np.radians(63.0)   # nominal plan-view LE sweep of the straight part, for reporting

# ---- heights / incidence (front view + WR sections of the drawing) --------------
DIHEDRAL = np.radians(6.23)      # front-view silhouettes (rev A airfoils: 6.15)
Y_DIH0 = 0.70                    # dihedral starts here: flat carry-through inside the fuselage (see z_ref)
Z_QC0 = 1.0233                   # WL of the chord line at the quarter chord on the flat centre section (rev A: 1.036)
TWIST = ((0.0, 1.45), (5.56, -0.91), (SEMI, -2.64))   # (BL, incidence deg), + = leading edge up
INC_ROOT, INC_TIP = np.radians(TWIST[0][1]), np.radians(TWIST[-1][1])

Y_FLAP = (0.450, 5.667)          # flap ends (inboard end under the wing-root fairing, dashed in the plan)
Y_AIL = (5.690, 7.400)           # aileron ends (drawn 5,690 - 7,450; kept inside the tip rib)
# Fowler flap (plan view of the drawing): the flap leading edge (hidden) lies at 69.2-69.9 % chord and the visible
# upper-surface shroud trailing edge ("lip") at a constant 92.7-93.4 % chord from BL 1500 to 5600 (least-squares
# 93.15 %, max 7 mm); section WR1 shows the upper skin unbroken to the lip.  The retracted flap stows under the long
# shroud: flap_cove() / flap_loop() below.
FLAP_X_LO, FLAP_X_LIP = 0.695, 0.9315
FLAP_SHROUD_T = (0.016, 0.004)   # shroud depth below the upper surface (chord units): at the cove top / at the lip
FLAP_COVE_TOP = 0.760            # chord station where the cove meets the shroud underside
FLAP_GAP = 0.002                 # flap upper surface below the shroud underside (chord units)
FLAP_TRAVEL = (0.24, -0.035)     # Fowler translation at full deflection (chord units: aft, down)
# Aileron (plan view of the drawing): the visible upper-surface gap line runs parallel to the trailing edge, a
# constant 439 mm ahead of it (BL 5750 - 7395, +/-0.1 mm) -> constant-chord aileron on the tapered wing, straight
# hinge line; the hinge chord fraction therefore varies along the span (ail_xh(y)).
AIL_GAP_TE = 0.439               # upper-surface gap line to trailing edge (m)
BOOT_Y = (0.95, 7.43)
GAP = 0.012   # spanwise gap between control surface and wing (m)

ROOT_AF, TIP_AF = ls0417mod(), ls0313()


# ---------------------------------------------------------------------------
# planform
# ---------------------------------------------------------------------------
def _chord_law(y, c_root):
    y = np.clip(np.asarray(y, float), 0, SEMI)
    return c_root * (1 - (1 - TAPER) * y / SEMI) + TE_KINK * np.maximum(y - Y_KINK, 0.0)


def x_le(y):
    """Leading-edge station of the wing panel at butt line |y| (before twist)."""
    return X_LE0 + np.clip(np.abs(np.asarray(y, float)), 0, SEMI) * np.tan(LE_SWEEP)


def _winglet_frame(c_tip, n_bend=14, n_straight=8):
    """Winglet chord path in the (y, z - z_tip) plane and the plan-view chord law along it.
    Returns (arr (N, 3) = y, dz, path angle; s arc length; chord c(s); straight length)."""
    a0, a1 = DIHEDRAL, np.pi / 2 - WL_CANT
    th = np.linspace(a0, a1, n_bend)
    cy, cz = SEMI - WL_BEND_R * np.sin(a0), WL_BEND_R * np.cos(a0)
    bend = np.stack([cy + WL_BEND_R * np.sin(th), cz - WL_BEND_R * np.cos(th), th], 1)
    # straight part: long enough for the outer skin of the top section to reach SPAN_TOTAL / 2
    skin_out = WL_TIP_AF_T / 2 * 0.99 * WL_TIP_CHORD * np.sin(a1)     # lower-surface offset outboard
    L_s = (SPAN_TOTAL / 2 - skin_out - bend[-1, 0]) / np.cos(a1)
    d = L_s * np.arange(1, n_straight + 1) / n_straight
    straight = np.stack([bend[-1, 0] + d * np.cos(a1), bend[-1, 1] + d * np.sin(a1), np.full(n_straight, a1)], 1)
    arr = np.vstack([bend, straight])
    s = np.r_[0, np.cumsum(np.hypot(np.diff(arr[:, 0]), np.diff(arr[:, 1])))]
    s1 = WL_BEND_R * (a1 - a0)
    u = np.clip(s / s1, 0, 1)
    blend = u * u * (3 - 2 * u)
    c = np.where(s <= s1, c_tip + (WL_MID_CHORD - c_tip) * blend,
                 WL_MID_CHORD + (WL_TIP_CHORD - WL_MID_CHORD) * (s - s1) / max(s[-1] - s1, 1e-9))
    return arr, s, c, L_s


def _tip_area(c_tip):
    arr, s, c, _ = _winglet_frame(c_tip, 60, 40)
    return float(np.trapezoid(c, arr[:, 0]))


def _solve_root_chord():
    """Root chord such that the total projected plan area (both halves: panel 0..SEMI incl. the aileron
    kink + the winglets' plan projection) equals AREA_REF."""
    ys = np.linspace(0, SEMI, 801)
    kink = float(np.trapezoid(TE_KINK * np.maximum(ys - Y_KINK, 0.0), ys))
    c_root = 2.2
    for _ in range(8):
        c_tip = float(_chord_law(SEMI, c_root))
        c_root = (AREA_REF / 2 - kink - _tip_area(c_tip)) / (SEMI * (1 + TAPER) / 2)
    return c_root


C_ROOT = _solve_root_chord()                          # chord at BL 0 (straight trailing edge = actual there)
C_TIP_TRAP = TAPER * C_ROOT                           # straight trailing edge extended to the tip rib
C_TIP = float(_chord_law(SEMI, C_ROOT))               # actual tip-rib chord (with the aileron kink)
# rev A names kept for compatibility: straight-part length, winglet lateral extent beyond the tip rib (chord path)
# and the outer-skin allowance at the top section
_wl_arr, _, _, WL_HEIGHT = _winglet_frame(C_TIP)
WL_LATERAL = float(_wl_arr[-1, 0] - SEMI)
WL_SKIN = SPAN_TOTAL / 2 - SEMI - WL_LATERAL


def chord(y):
    return _chord_law(np.abs(np.asarray(y, float)), C_ROOT)


def x_te(y):
    """Trailing-edge station of the wing panel at butt line |y| (before twist)."""
    return x_le(y) + chord(y)


def twist(y):
    """Incidence (rad, + = leading edge up) at butt line |y|."""
    ys, ds = zip(*TWIST)
    return np.radians(np.interp(np.abs(np.asarray(y, float)), ys, ds))


def z_ref(y):
    """WL of the chord line at the quarter chord (the dihedral reference line).  The centre section is flat
    out to BL Y_DIH0 (inside the fuselage): the drawn wing-root fairing bottoms out at WL ~870, which a
    straight 6 deg dihedral line continued to the centre line (wing lower surface WL 794) would pierce."""
    return Z_QC0 + np.maximum(np.abs(np.asarray(y, float)) - Y_DIH0, 0.0) * np.tan(DIHEDRAL)


def _mac_numeric():
    ys = np.linspace(0, SEMI, 2001)
    c = chord(ys)
    S = np.trapezoid(c, ys)
    m = np.trapezoid(c * c, ys) / S
    ym = np.trapezoid(c * ys, ys) / S
    lemac = np.trapezoid(c * x_le(ys), ys) / S
    return float(m), float(ym), float(lemac)


MAC, Y_MAC, LEMAC = _mac_numeric()                    # wing panel 0..SEMI (winglets excluded)
X_QC = LEMAC + 0.25 * MAC                             # quarter chord of the MAC (the QC line is ~unswept)


def planform_area():
    """Total projected plan area (m^2): both halves, panel incl. the kink, plus the winglets' projection."""
    ys = np.linspace(0, SEMI, 2001)
    return float(2 * (np.trapezoid(chord(ys), ys) + _tip_area(C_TIP)))


def airfoil_at(y):
    w = np.clip((y - 0.6) / (SEMI - 0.6), 0, 1)
    return ROOT_AF.blend(TIP_AF, w)


def section_at(y):
    """Right-wing section at butt line y (>= 0)."""
    c = float(chord(y))
    return Section(le=np.array([float(x_le(y)), y, float(z_ref(y))]), chord=c, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 0, 1.0]), twist=float(twist(y)), airfoil=airfoil_at(y))


def mac():
    """(MAC, its butt line, LEMAC station) of the wing panel 0..SEMI."""
    return MAC, Y_MAC, LEMAC


# ---------------------------------------------------------------------------
# aileron hinge line (constant-chord aileron, straight hinge)
# ---------------------------------------------------------------------------
def _xh_for_gap(y):
    """Hinge chord fraction at butt line y that puts the upper cove end (x_end_of_plain) AIL_GAP_TE ahead of the TE."""
    sec = section_at(y)
    target = 1.0 - AIL_GAP_TE / sec.chord
    a, b = 0.45, 0.85
    for _ in range(40):
        m = 0.5 * (a + b)
        if x_end_of_plain(sec, m)[1] < target:
            a = m
        else:
            b = m
    return 0.5 * (a + b)


def _hinge_line():
    ends = []
    for y in Y_AIL:
        ends.append((y, float(x_le(y) + _xh_for_gap(y) * chord(y))))
    return tuple(ends)


def ail_xh(y):
    """Aileron hinge chord fraction at butt line |y|: straight hinge line AIL_HINGE (plan stations at the aileron
    ends), i.e. a constant-chord aileron whose upper gap line is AIL_GAP_TE ahead of the trailing edge."""
    (y0, x0), (y1, x1) = AIL_HINGE
    y = np.abs(np.asarray(y, float))
    xh = x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    return (xh - x_le(y)) / chord(y)


def ail_gap_x(y, upper=True):
    """Plan station of the aileron's gap line (the cove end of the upper skin, or of the lower skin with
    upper=False) at butt line |y| (from the parameters)."""
    y = float(abs(y))
    return float(x_le(y) + x_end_of_plain(section_at(y), float(ail_xh(y)))[0 if not upper else 1] * chord(y))


def flap_lines(y, upper=True):
    """Plan stations of the flap bay's visible chordwise line at butt line |y|: the shroud lip FLAP_X_LIP seen from
    above, the lower-skin cove edge FLAP_X_LO seen from below."""
    y = np.abs(np.asarray(y, float))
    return x_le(y) + (FLAP_X_LIP if upper else FLAP_X_LO) * chord(y)


# ---------------------------------------------------------------------------
# control-surface section geometry (chord units)
# ---------------------------------------------------------------------------

def shroud_underside(af, x):
    """Chord-unit z of the flap shroud's lower surface at chord station(s) x (FLAP_COVE_TOP .. FLAP_X_LIP)."""
    x = np.asarray(x, float)
    u = np.clip((x - FLAP_COVE_TOP) / (FLAP_X_LIP - FLAP_COVE_TOP), 0, 1)
    return af.upper(x) - (FLAP_SHROUD_T[0] + (FLAP_SHROUD_T[1] - FLAP_SHROUD_T[0]) * u)


def flap_cove(sec, n=14):
    """Flap cove (chord units): from the lower skin end FLAP_X_LO round the flap nose up to the shroud underside at
    FLAP_COVE_TOP, aft along the shroud underside to the lip at FLAP_X_LIP, closed at the upper surface there."""
    af = sec.airfoil
    lo = np.array([FLAP_X_LO, float(af.lower(FLAP_X_LO))])
    top = np.array([FLAP_COVE_TOP, float(shroud_underside(af, FLAP_COVE_TOP))])
    c = bezier(lo, lo + [-0.045, 0.004], [0.650, top[1]], top, n=n)
    xs = np.linspace(FLAP_COVE_TOP, FLAP_X_LIP, max(8, n))[1:]
    under = np.stack([xs, shroud_underside(af, xs)], 1)
    return np.vstack([c, under, [[FLAP_X_LIP, float(af.upper(FLAP_X_LIP))]]])


def flap_upper(af, x):
    """Chord-unit z of the retracted flap's upper surface: FLAP_GAP below the shroud underside up to the lip, then
    converging on the wing contour at the trailing edge (the lip sits proud of the flap by its own thickness)."""
    x = np.asarray(x, float)
    d_lip = FLAP_SHROUD_T[1] + FLAP_GAP
    under = af.upper(x) - shroud_underside(af, np.minimum(x, FLAP_X_LIP)) + FLAP_GAP
    off = np.where(x <= FLAP_X_LIP, under, d_lip * (1.0 - x) / (1.0 - FLAP_X_LIP))
    return af.upper(x) - off


def flap_loop(sec, n=18):
    """Retracted Fowler-flap section (chord units): nose inside the cove, upper surface stowed under the shroud
    (flap_upper), lower surface flush with the wing lower contour from 0.708."""
    af = sec.airfoil
    x_nt = FLAP_COVE_TOP + 0.004
    xu = cos_pts(n, 0.0, 1.0) * (1 - x_nt) + x_nt
    zu = flap_upper(af, xu)
    xl = (cos_pts(n, 0.0, 1.0) * (1 - 0.708) + 0.708)[::-1]
    zl = af.lower(xl)
    nose_top = np.array([xu[0], zu[0]])
    nose_bot = np.array([0.708, float(af.lower(0.708))])
    nose = bezier(nose_bot, nose_bot + [-0.030, 0.008], [0.672, nose_top[1] - 0.004], nose_top, n=12)
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
    """Control surface split around a tab cut-out (xh: hinge chord fraction, or a callable of the section).
    Returns (body, tab_body, tab_hinge_pts)."""
    t0, t1, xt = tab
    xh_of = xh if callable(xh) else (lambda s, _x=xh: _x)          # xh: chord fraction or callable(section)
    bodies = [closed_body(section_fn, span_stations(s0, t0, step), lambda s: plain_surface_loop(s, xh_of(s))),
              closed_body(section_fn, span_stations(t0, t1, step), lambda s: plain_surface_loop(s, xh_of(s), x_end=xt)),
              closed_body(section_fn, span_stations(t1, s1, step), lambda s: plain_surface_loop(s, xh_of(s)))]
    tb = closed_body(section_fn, span_stations(t0 + gap, t1 - gap, step), lambda s: tab_loop(s, xt + 0.004))
    a, b = section_fn(t0), section_fn(t1)
    ha = a.point(np.array(xt + 0.004), np.array(float(a.airfoil.camber(xt))))
    hb = b.point(np.array(xt + 0.004), np.array(float(b.airfoil.camber(xt))))
    return Mesh.merge(bodies), tb, (ha, hb)


def x_end_of_plain(sec, xh, gap=0.010):
    _, (tu, tl, R) = plain_cove(sec, xh, gap)
    zh = float(sec.airfoil.camber(xh))
    return xh + R * np.cos(tu), xh + R * np.cos(tl)


AIL_HINGE = _hinge_line()        # ((BL, STA), (BL, STA)) of the straight aileron hinge line at the aileron ends
AIL_XH = float(ail_xh(0.5 * sum(Y_AIL)))   # compat: hinge chord fraction at mid-aileron (use ail_xh(y))


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

    # panel D: aileron bay (constant-chord aileron: the hinge fraction ail_xh(y) varies along the span)
    ys = span_stations(Y_AIL[0], Y_AIL[1], 0.2)
    add_skin(skin(section_at, ys, x_lo_end=lambda y: x_end_of_plain(section_at(y), float(ail_xh(y)))[0],
                  x_up_end=lambda y: x_end_of_plain(section_at(y), float(ail_xh(y)))[1], n=n))
    out["skin"].append(curve_patch(section_at, ys, lambda s: plain_cove(s, float(ail_xh(s.le[1])))[0],
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
        cove, _ = plain_cove(sec, float(ail_xh(y)))
        xl_e, xu_e = x_end_of_plain(sec, float(ail_xh(y)))
        pts = cut_rib(sec, cove[::-1], xl_e, xu_e)
        out["ribs"].append(planar_cap(pts, (0, sgn, 0)))

    # flap body
    ys = span_stations(Y_FLAP[0] + GAP, Y_FLAP[1] - GAP, 0.25)
    out["flap"] = closed_body(section_at, ys, flap_loop)
    # aileron body with the Flettner geared balance tab cut-out (inboard 40 %)
    body, tabm, hinge = segmented_surface(section_at, Y_AIL[0] + GAP, Y_AIL[1] - GAP, lambda s: float(ail_xh(s.le[1])),
                                          (Y_AIL[0] + 0.06, Y_AIL[0] + 0.72, 0.945), step=0.2)
    out["aileron"] = body
    out["ail_tab"] = (tabm, hinge)

    out["winglet"] = build_winglet()
    return out


# ---------------------------------------------------------------------------
# winglet
# ---------------------------------------------------------------------------
def winglet_path(n_bend=14, n_straight=8):
    """Winglet chord path: rows (y, z, path angle from horizontal) and arc length.  Starts at the tip rib
    (BL SEMI, on the dihedral reference line) tangent to the dihedral, bends with WL_BEND_R to the cant
    angle, then runs straight until the outer skin of the top section reaches SPAN_TOTAL / 2."""
    arr, s, _, _ = _winglet_frame(C_TIP, n_bend, n_straight)
    arr = arr.copy()
    arr[:, 1] += float(z_ref(SEMI))
    return arr, s


def winglet_sections(n_bend=14, n_straight=8):
    """Winglet sections along winglet_path() (parameter-derived; used by the 3-D loft and the drawings)."""
    arr, s, c, _ = _winglet_frame(C_TIP, n_bend, n_straight)
    z0 = float(z_ref(SEMI))
    L = s[-1]
    a0, a1 = DIHEDRAL, np.pi / 2 - WL_CANT
    s1 = WL_BEND_R * (a1 - a0)
    sec0 = section_at(SEMI)
    te0 = sec0.le[0] + sec0.chord
    tipaf = naca00(WL_TIP_AF_T)
    out = []
    for (y, dz, a), sk, ck in zip(arr, s, c):
        u = min(sk / s1, 1.0)
        blend = u * u * (3 - 2 * u)                  # smoothstep through the bend
        te = te0 + WL_TE_SWEEP * (sk / L) ** WL_TE_EXP
        at = a - DIHEDRAL * (1 - blend)              # thickness direction: vertical at the tip rib
        e_t = np.array([0.0, -np.sin(at), np.cos(at)])
        af = sec0.airfoil.blend(tipaf, blend)
        tw = INC_TIP * (1 - blend)
        out.append(Section(le=np.array([te - ck, y, z0 + dz]), chord=float(ck), e_c=np.array([1.0, 0, 0]),
                           e_t=e_t, twist=tw, airfoil=af))
    return out


def build_winglet():
    secs = winglet_sections()
    rows = []
    for sec in secs:
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
                       "dihedral": f"{np.degrees(DIHEDRAL):.1f} deg (drawing)",
                       "incidence": f"{TWIST[0][1]:+.2f} root / {TWIST[-1][1]:+.2f} tip (drawing WR1-WR4)"})
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
                            travel=[FLAP_TRAVEL[0] * cm, 0.0, FLAP_TRAVEL[1] * cm], max=40.0, settings=[0, 15, 30, 40]),
                 explode=(0.9, 0, -0.3), group="Flight controls",
                 material_note="Single-piece Fowler flap, 3 support arms")
        f.add(mir(R["flap"]), "paint_white")
        parts[f.id] = f
        a = section_at(Y_AIL[0])
        b = section_at(Y_AIL[1])
        xa, xb = float(ail_xh(Y_AIL[0])), float(ail_xh(Y_AIL[1]))
        ha = a.point(np.array(xa), np.array(float(a.airfoil.camber(xa))))
        hb = b.point(np.array(xb), np.array(float(b.airfoil.camber(xb))))
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
    print("SEMI %.3f  C_ROOT %.4f C_TIP %.4f (straight TE %.4f)  taper %.3f" % (SEMI, C_ROOT, C_TIP, C_TIP_TRAP, TAPER))
    print("MAC %.4f m at y=%.3f, LEMAC STA %.4f  X_QC %.4f;  POH aft CG %.3f = %.1f %% MAC"
          % (MAC, Y_MAC, LEMAC, X_QC, AFT_CG, 100 * (AFT_CG - LEMAC) / MAC))
    print("projected plan area %.3f m2 (AREA_REF %.2f)" % (planform_area(), AREA_REF))
    arr, seg = winglet_path()
    secs = winglet_sections()
    ymax = max(float(np.max(s.lower(cos_pts(40))[:, 1])) for s in secs)
    print("winglet path top y=%.3f z=%.3f; outer skin y=%.4f (span = %.3f m)" % (arr[-1, 0], arr[-1, 1], ymax, 2 * ymax))
