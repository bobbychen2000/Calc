"""
PC-12 fuselage outer mould line (OML).

The fuselage is lofted the way aircraft lofts were drawn on the mould-loft
floor: a set of longitudinal control lines (crown, keel, maximum-breadth
half-width and its water line) plus a super-ellipse "section law" that turns
those lines into a cross-section at any fuselage station.

Stations (x) are metres aft of the weight-and-balance datum, which Pilatus
places 3.000 m (118 in) ahead of the firewall.  Water line z = 0 is the ground
with the aircraft static on its gear.

Official anchors used: overall length 14.40 m, cabin 5.16 x 1.52 x 1.47 m,
cabin floor width 1.30 m, propeller ground clearance 0.32 m (2.67 m prop).
The 1.69 m x 1.83 m external section follows from the cabin interior plus
structure and matches the fuselage dimensions shown on the POH three-view.
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
    cowl_front=0.95,
    firewall=3.00,
    windshield_base=3.30,
    windshield_top=3.93,
    cockpit_aft=4.40,
    aft_pressure_bulkhead=9.85,
    fin_root_le=11.95,
    tail_end=14.36,
)
PROP_AXIS_Z = 1.655        # 0.32 m clearance + 1.335 m radius
SPINNER_R = 0.29

# ----------------------------------------------------------------------------
# longitudinal control lines
# ----------------------------------------------------------------------------
_top = [(0.95, PROP_AXIS_Z + SPINNER_R), (1.20, 1.985), (1.60, 2.035), (2.20, 2.100),
        (2.80, 2.160), (3.30, 2.215), (3.50, 2.352), (3.70, 2.478), (3.90, 2.576),
        (4.10, 2.620), (4.40, 2.630), (9.90, 2.630), (10.50, 2.605), (11.20, 2.530),
        (11.90, 2.440), (12.60, 2.345), (13.30, 2.260), (13.90, 2.195), (14.36, 2.140)]
_bot = [(0.95, PROP_AXIS_Z - SPINNER_R), (1.20, 1.315), (1.60, 1.225), (2.00, 1.140),
        (2.60, 1.020), (3.00, 0.945), (3.50, 0.855), (4.00, 0.812), (4.40, 0.800),
        (8.80, 0.800), (9.40, 0.838), (10.00, 0.925), (10.80, 1.095), (11.60, 1.310),
        (12.40, 1.540), (13.20, 1.770), (13.90, 1.945), (14.36, 2.045)]
_hw = [(0.95, SPINNER_R), (1.20, 0.370), (1.60, 0.462), (2.20, 0.580), (2.80, 0.680),
       (3.30, 0.752), (3.80, 0.812), (4.40, 0.842), (5.00, 0.845),
       (9.40, 0.845), (10.00, 0.830), (10.80, 0.765), (11.60, 0.650), (12.40, 0.505),
       (13.20, 0.345), (13.90, 0.195), (14.36, 0.045)]
_zmw = [(0.95, PROP_AXIS_Z), (2.00, 1.662), (3.00, 1.700), (4.40, 1.780), (9.80, 1.780),
        (11.00, 1.860), (12.20, 1.960), (13.40, 2.040), (14.36, 2.092)]
_ntop = [(0.95, 2.0), (2.00, 2.12), (3.00, 2.34), (3.80, 2.38), (4.60, 2.24), (9.80, 2.20), (12.5, 2.05), (14.36, 2.0)]
_nbot = [(0.95, 2.0), (2.00, 2.18), (4.00, 2.45), (9.00, 2.45), (12.0, 2.25), (14.36, 2.0)]

z_top = pchip(*zip(*_top))
z_bot = pchip(*zip(*_bot))
half_w = pchip(*zip(*_hw))
z_mw = pchip(*zip(*_zmw))
n_top = pchip(*zip(*_ntop))
n_bot = pchip(*zip(*_nbot))

CONTROL_LINES = dict(crown=_top, keel=_bot, half_breadth=_hw, max_breadth_wl=_zmw)


def section(x, t):
    """Point(s) on the OML.  t in [0,1): 0 = crown, 0.25 = starboard max breadth,
    0.5 = keel, 0.75 = port max breadth.  Broadcasts over x and t."""
    x = np.asarray(x, float)
    t = np.asarray(t, float)
    a = 2 * np.pi * t
    s, c = np.sin(a), np.cos(a)
    upper = c >= 0
    ntop, nbot = n_top(x), n_bot(x)
    n = np.where(upper, ntop, nbot)
    hw = half_w(x)
    zm = z_mw(x)
    hz = np.where(upper, z_top(x) - zm, zm - z_bot(x))
    y = hw * np.sign(s) * np.abs(s) ** (2.0 / n)
    z = zm + hz * np.sign(c) * np.abs(c) ** (2.0 / n)
    return np.stack(np.broadcast_arrays(x, y, z), -1)


def side_y(x, z):
    """|y| of the OML at station x and water line z (0 outside the section)."""
    x = np.asarray(x, float)
    z = np.asarray(z, float)
    zm = z_mw(x)
    upper = z >= zm
    n = np.where(upper, n_top(x), n_bot(x))
    hz = np.where(upper, z_top(x) - zm, zm - z_bot(x))
    r = np.clip(np.abs(z - zm) / hz, 0, 1)
    return half_w(x) * (1 - r ** n) ** (1.0 / n)


def t_of(x, z, side=-1):
    """Inverse of section(): circumferential parameter at (x, z) on the given side."""
    x = np.asarray(x, float)
    z = np.asarray(z, float)
    zm = z_mw(x)
    upper = z >= zm
    n = np.where(upper, n_top(x), n_bot(x))
    hz = np.where(upper, z_top(x) - zm, zm - z_bot(x))
    r = np.clip((z - zm) / hz, -1, 1)
    # c = sign(r)|r|^(n/2) ; a = arccos(c)
    c = np.sign(r) * np.abs(r) ** (n / 2.0)
    a = np.arccos(np.clip(c, -1, 1))
    t = a / (2 * np.pi)
    return t if side > 0 else 1.0 - t


def perimeter(x, n=400):
    t = np.linspace(0, 1, n + 1)
    p = section(np.full_like(t, x), t)
    return np.linalg.norm(np.diff(p, axis=0), axis=1).sum()


def station_grid(max_step_fwd=0.035, max_step_aft=0.05, extra=()):
    from cad.mesh import densify
    keys = [0.95, 1.2, 1.6, 2.0, 2.6, 3.0, 3.3, 3.93, 4.4, 9.85, 14.36] + list(extra)
    fwd = densify([k for k in keys if k <= 9.85] + [9.85], max_step_fwd)
    aft = densify([9.85] + [k for k in keys if k >= 9.85], max_step_aft)
    return np.unique(np.concatenate([fwd, aft]))


if __name__ == "__main__":
    for x in (1.0, 2.0, 3.0, 4.4, 6.0, 9.85, 12.0, 14.0):
        print(f"x={x:5.2f} top={float(z_top(x)):.3f} bot={float(z_bot(x)):.3f} "
              f"hw={float(half_w(x)):.3f} zmw={float(z_mw(x)):.3f} perim={perimeter(x):.3f}")
    # cabin floor width check (z = 1.12)
    print("OML width at floor (z=1.12, x=6):", 2 * float(side_y(6.0, 1.12)))
    print("OML width at z=1.10:", 2 * float(side_y(6.0, 1.10)))
