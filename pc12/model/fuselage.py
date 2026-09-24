"""
PC-12 fuselage outer mould line (OML).

The fuselage is lofted the way aircraft lofts were drawn on the mould-loft
floor: a set of longitudinal control lines (crown, keel, maximum-breadth
half-width and its water line) plus a "section law" that turns those lines into
a cross-section at any fuselage station.

Section law (per half, upper half shown; the lower half uses the keel and the
lower exponents):

    |y / hw|^n  +  |(z - zmw) / (z_top - zmw)|^m  =  1

n controls the crown (keel) flatness -- larger n = flatter crown -- and m the
side flatness near the maximum breadth -- larger m = more vertical sides.  With
n = m this is the classic super-ellipse (n = m = 2: an ellipse).  All eight
lines (crown, keel, half-breadth, max-breadth WL, n_top, m_top, n_bot, m_bot)
are monotone piecewise-cubic (pchip) curves through the knot tables below.

Stations (x) are metres aft of the weight-and-balance datum, which Pilatus
places 3.000 m (118 in) ahead of the firewall.  Water line z = 0 is the ground
with the aircraft static on its gear.

Official anchors: overall length 14.40 m (spinner tip STA 0.39), cabin
5.16 x 1.52 x 1.47 m, cabin floor width 1.30 m, propeller ground clearance
0.32 m (2.67 m prop -> prop axis WL 1.655).  The knot values were fitted by
least squares (drawing/lines_plan.py 'fit') to the published Pilatus NGX model
drawing (profile, plan and eleven frame sections); the lines plan sheet L1
(drawing/lines_plan.py) documents the fit.  The drawing itself is not part of
this repository.
"""
from __future__ import annotations
import numpy as np
from cad.mesh import pchip

# ----------------------------------------------------------------------------
# key stations (m aft of datum)
# ----------------------------------------------------------------------------
STA = dict(
    spinner_tip=0.39,
    prop_plane=0.80,
    cowl_front=1.044,            # spinner / cowling joint (spinner base)
    firewall=3.00,
    windshield_base=3.30,
    windshield_top=3.93,
    cockpit_aft=4.40,
    cabin_fwd=4.40,              # crown reaches the constant cabin section
    aft_pressure_bulkhead=9.85,
    fin_root_le=11.95,
    tail_end=13.57,              # tail-cone closure (lower end of the rudder trailing edge)
)
PROP_AXIS_Z = 1.655        # 0.32 m clearance + 1.335 m radius
SPINNER_R = 0.250          # spinner base radius at the cowl front (drawing: 0.250)
# spinner profile r(t) = SPINNER_R * (1 - (1 - t)^a)^b, t = 0 at the tip (STA 0.39) .. 1 at the cowl front;
# fitted to the drawing (max 0.8 mm).  For model/powerplant.py (Stage 3; it still uses a = 2.1, b = 0.55).
SPINNER_SHAPE = (1.48, 0.53)

# Frame stations (labelled frames of the reference drawing; used for station grids and the body plan).
FRAMES = dict(EF1=1.200, EF2=2.075, FR10=3.080, FR12=3.580, FR14=4.080, FR16=4.590, FR19=5.340, FR21=5.890,
              FR23=6.451, FR25=6.971, FR27=7.471, FR29=7.971, FR30=8.230, FR31=8.471, FR33=9.000, FR36=9.750,
              FR38=10.800, FR40=11.850)

_X0, _X1 = STA["cowl_front"], STA["tail_end"]
_ZC, _R = PROP_AXIS_Z, SPINNER_R

# ----------------------------------------------------------------------------
# longitudinal control lines: (station, value) knots
# ----------------------------------------------------------------------------
# <fitted-tables> (written by python3 -m drawing.lines_fit fit --write)
_top = [(_X0, 1.905), (1.140, 1.952), (1.200, 1.960), (1.500, 2.011), (2.000, 2.072), (2.500, 2.126), (3.000, 2.180),
        (3.150, 2.207), (3.300, 2.284), (3.500, 2.388), (3.700, 2.497), (3.900, 2.607), (4.080, 2.696),
        (4.200, 2.742), (4.400, 2.769), (9.000, 2.769), (9.750, 2.748), (10.800, 2.694), (11.850, 2.613),
        (12.650, 2.532), (_X1, 2.300)]
_bot = [(_X0, 1.405), (1.140, 1.413), (1.200, 1.233), (1.250, 1.201), (1.350, 1.163), (1.500, 1.120), (1.800, 1.048),
        (2.075, 0.998), (2.500, 0.951), (2.850, 0.941), (8.200, 0.941), (8.600, 0.960), (9.000, 1.021),
        (9.400, 1.097), (10.000, 1.242), (10.800, 1.441), (11.850, 1.730), (12.650, 1.851), (_X1, 1.930)]
_hw = [(_X0, 0.250), (1.200, 0.278), (1.350, 0.305), (1.500, 0.336), (1.700, 0.401), (2.000, 0.513), (2.300, 0.589),
       (2.500, 0.632), (3.000, 0.724), (3.300, 0.769), (3.580, 0.802), (3.900, 0.828), (4.200, 0.841), (4.600, 0.844),
       (9.000, 0.844), (9.400, 0.822), (9.750, 0.773), (10.300, 0.686), (10.800, 0.604), (11.300, 0.514),
       (11.850, 0.415), (12.300, 0.323), (12.650, 0.234), (13.000, 0.151), (_X1, 0.035)]
_zmw = [(_X0, 1.655), (1.200, 1.678), (1.600, 1.608), (2.075, 1.490), (2.500, 1.478), (3.080, 1.564), (3.580, 1.696),
        (4.080, 1.813), (4.600, 1.861), (8.200, 1.861), (9.000, 1.806), (9.750, 1.902), (10.800, 2.035),
        (11.850, 2.146), (12.650, 2.294), (_X1, 2.270)]
# section-law exponents: n = crown/keel flatness, m = side flatness (upper / lower half)
_XN = [_X0, 1.200, 1.600, 2.075, 2.500, 3.080, 3.580, 4.080, 4.600, 8.200, 9.000, 9.750, 10.800, 11.850, _X1]
_ntop = list(zip(_XN, [2.00, 2.06, 2.24, 2.38, 2.34, 2.16, 2.00, 2.04, 2.10, 2.10, 2.10, 2.21, 2.25, 2.27, 2.00]))
_mtop = list(zip(_XN, [2.00, 2.12, 2.45, 2.75, 2.83, 2.81, 2.79, 2.58, 2.35, 2.35, 2.52, 2.19, 2.05, 2.06, 2.00]))
_nbot = list(zip(_XN, [2.00, 2.12, 2.41, 2.68, 2.77, 2.83, 2.95, 3.07, 3.14, 3.14, 3.31, 3.01, 2.52, 2.18, 2.00]))
_mbot = list(zip(_XN, [2.00, 2.04, 2.15, 2.28, 2.35, 2.53, 2.93, 3.22, 3.34, 3.34, 3.69, 3.29, 2.72, 2.33, 2.00]))
# </fitted-tables>

CONTROL_LINES = dict(crown=_top, keel=_bot, half_breadth=_hw, max_breadth_wl=_zmw,
                     n_top=_ntop, m_top=_mtop, n_bot=_nbot, m_bot=_mbot)


def _polar_radius(s, c, n, m, iters=48):
    """Radius r >= 0 with (r s)^n + (r c)^m = 1 (s, c >= 0: |sin|, |cos| of the polar angle)."""
    lo = np.zeros(np.broadcast(s, c, n, m).shape)
    hi = np.full_like(lo, 1.5)
    for _ in range(iters):
        r = 0.5 * (lo + hi)
        g = (r * s) ** n + (r * c) ** m - 1.0
        lo = np.where(g < 0, r, lo)
        hi = np.where(g < 0, hi, r)
    return 0.5 * (lo + hi)


# ----------------------------------------------------------------------------
# the loft
# ----------------------------------------------------------------------------
class OML:
    """Outer mould line from eight knot tables (see the module docstring).  The module-level
    functions below evaluate the default instance built from the tables above; the lines-plan fit
    builds trial instances from candidate knot values."""
    LINES = ("crown", "keel", "half_breadth", "max_breadth_wl", "n_top", "m_top", "n_bot", "m_bot")

    def __init__(self, tables):
        self.tables = {k: [(float(a), float(b)) for a, b in tables[k]] for k in self.LINES}
        f = {k: pchip(*zip(*self.tables[k])) for k in self.LINES}
        self.z_top, self.z_bot, self.half_w, self.z_mw = f["crown"], f["keel"], f["half_breadth"], f["max_breadth_wl"]
        self.n_top, self.m_top, self.n_bot, self.m_bot = f["n_top"], f["m_top"], f["n_bot"], f["m_bot"]
        self.x0 = min(t[0][0] for t in self.tables.values())
        self.x1 = max(t[-1][0] for t in self.tables.values())

    def _half(self, x, upper):
        zm = self.z_mw(x)
        n = np.where(upper, self.n_top(x), self.n_bot(x))
        m = np.where(upper, self.m_top(x), self.m_bot(x))
        hz = np.where(upper, self.z_top(x) - zm, zm - self.z_bot(x))
        return zm, n, m, hz

    def section(self, x, t):
        """Point(s) on the OML.  t in [0,1): 0 = crown, 0.25 = starboard max breadth,
        0.5 = keel, 0.75 = port max breadth.  Broadcasts over x and t.
        t is the polar angle (/2 pi) about (0, zmw) in coordinates normalised by the half-breadth and the
        half-depths, so points spread evenly round flat-sided sections too."""
        x, t = np.broadcast_arrays(np.asarray(x, float), np.asarray(t, float))
        a = 2 * np.pi * t
        s, c = np.sin(a), np.cos(a)
        zm, n, m, hz = self._half(x, c >= 0)
        r = _polar_radius(np.abs(s), np.abs(c), n, m)
        y = self.half_w(x) * r * s
        z = zm + hz * r * c
        return np.stack([x, y, z], -1)

    def side_y(self, x, z):
        """|y| of the OML at station x and water line z (0 outside the section)."""
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        zm, n, m, hz = self._half(x, z >= self.z_mw(x))
        r = np.clip(np.abs(z - zm) / hz, 0, 1)
        return self.half_w(x) * np.clip(1 - r ** m, 0, 1) ** (1.0 / n)

    def z_at(self, x, y, upper=True):
        """Water line of the OML surface at station x and butt line |y| (upper or lower half)."""
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        up = np.full(x.shape, bool(upper))
        zm, n, m, hz = self._half(x, up)
        u = np.clip(np.abs(y) / self.half_w(x), 0, 1)
        v = np.clip(1 - u ** n, 0, 1) ** (1.0 / m)
        return np.where(up, zm + hz * v, zm - hz * v)

    def t_of(self, x, z, side=-1):
        """Inverse of section(): circumferential parameter at (x, z) on the given side."""
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        zm, n, m, hz = self._half(x, z >= self.z_mw(x))
        v = np.clip((z - zm) / hz, -1, 1)
        u = np.clip(1 - np.abs(v) ** m, 0, 1) ** (1.0 / n)
        t = np.arctan2(u, v) / (2 * np.pi)
        return t if side > 0 else 1.0 - t

    def section_distance(self, x, y, z):
        """Approximate signed normal distance (m, + outside) of points (y, z) from the section at
        station x (first-order / Sampson distance of the implicit section law)."""
        x, y, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(z, float))
        zm, n, m, hz = self._half(x, z >= self.z_mw(x))
        hw = self.half_w(x)
        u = np.abs(y) / hw
        v = np.abs(z - zm) / hz
        Fv = u ** n + v ** m - 1.0
        gy = n * u ** (n - 1) / hw
        gz = m * v ** (m - 1) / hz
        return Fv / np.sqrt(gy ** 2 + gz ** 2 + 1e-12)


_OML = OML(CONTROL_LINES)
z_top, z_bot, half_w, z_mw = _OML.z_top, _OML.z_bot, _OML.half_w, _OML.z_mw
n_top, m_top, n_bot, m_bot = _OML.n_top, _OML.m_top, _OML.n_bot, _OML.m_bot


def section(x, t):
    """Point(s) on the OML.  t in [0,1): 0 = crown, 0.25 = starboard max breadth,
    0.5 = keel, 0.75 = port max breadth.  Broadcasts over x and t."""
    return _OML.section(x, t)


def side_y(x, z):
    """|y| of the OML at station x and water line z (0 outside the section)."""
    return _OML.side_y(x, z)


def z_at(x, y, upper=True):
    """Water line of the OML at station x and butt line y (upper or lower half)."""
    return _OML.z_at(x, y, upper)


def t_of(x, z, side=-1):
    """Inverse of section(): circumferential parameter at (x, z) on the given side."""
    return _OML.t_of(x, z, side)


def perimeter(x, n=400):
    t = np.linspace(0, 1, n + 1)
    p = section(np.full_like(t, x), t)
    return np.linalg.norm(np.diff(p, axis=0), axis=1).sum()


def station_grid(max_step_fwd=0.035, max_step_aft=0.05, extra=()):
    from cad.mesh import densify
    apb, x0, x1 = STA["aft_pressure_bulkhead"], STA["cowl_front"], STA["tail_end"]
    keys = [x0, 1.13, 1.2, 1.6, 2.0, 2.6, 3.0, 3.3, 3.93, 4.4, apb, x1] + list(extra)
    fwd = densify([k for k in keys if k <= apb] + [apb], max_step_fwd)
    aft = densify([apb] + [k for k in keys if k >= apb], max_step_aft)
    return np.unique(np.concatenate([fwd, aft]))


def cabin_numbers(x=6.0, floor_width=1.30, lining=0.045):
    """Cabin cross-section numbers at station x: crown / keel / max-breadth WL, and the WL at which
    the OML minus a lining allowance is `floor_width` wide (the floor line of the cabin)."""
    zs = np.linspace(float(z_bot(x)), float(z_mw(x)), 4001)
    w = 2 * (side_y(np.full_like(zs, x), zs) - lining)
    k = np.argmax(w >= floor_width)
    return dict(x=x, crown=float(z_top(x)), keel=float(z_bot(x)), zmw=float(z_mw(x)),
                max_breadth=2 * float(half_w(x)), depth=float(z_top(x) - z_bot(x)),
                floor_wl_at_width=float(zs[k]))


if __name__ == "__main__":
    for x in (1.1, 2.0, 3.0, 4.4, 6.0, 9.85, 12.0, 13.5):
        print(f"x={x:5.2f} top={float(z_top(x)):.3f} bot={float(z_bot(x)):.3f} "
              f"hw={float(half_w(x)):.3f} zmw={float(z_mw(x)):.3f} perim={perimeter(x):.3f}")
    print(cabin_numbers())
