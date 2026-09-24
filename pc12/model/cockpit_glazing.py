"""
Flight-deck glazing of the PC-12 PRO, defined by geometric constraints.

Sourced facts:
  * two heated windshield panes with a centre post (POH airframe description)
  * one fixed acrylic side window per side; the PRO deletes the pilot's
    direct-vision (DV) window (Pilatus PC-12 PRO release)
  * NGX/PRO "dark windshield surround trim" (Pilatus NGX release)
Reconstructed (no published drawing): the exact sill, A-pillar and roof-edge
lines below, chosen so the design eye point (STA 3.98, BL +/-0.36, WL 2.36)
sees ~13 deg down over the sill and ~9 deg over the cowling.

All fields are signed distances in metres (negative inside the pane).
Coordinates: x station aft, s = signed arc length from the crown (+ starboard),
y butt line, z water line.
"""
import numpy as np

WS_POST = 0.034                  # half-width of the centre post
# windshield panes, plan view (x, |y|): straight sill and roof edge (flat heated panes)
WS_PLAN = [(3.215, WS_POST), (3.215, 0.43), (3.305, 0.565), (3.832, 0.62), (3.832, WS_POST)]
# A-pillar centre line in side projection (x, z): shared by the windshield's outer
# edge and the side window's front edge
PILLAR = ((3.300, 2.020), (3.800, 2.520))
PILLAR_HALF = 0.030
SW_BOTTOM = 1.985
SW_REAR = 4.268
SW_TOP = ((3.78, 2.445), (4.268, 2.475))
EYE = np.array([3.98, 0.335, 2.36])


def smax(*vals, k=0.05):
    """Smooth maximum (rounded intersection)."""
    out = vals[0]
    for b in vals[1:]:
        h = np.maximum(k - np.abs(out - b), 0.0) / k
        out = np.maximum(out, b) + h * h * k * 0.25
    return out


def smin(a, b, k=0.06):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def x_pillar(z):
    (x0, z0), (x1, z1) = PILLAR
    return x0 + (z - z0) * (x1 - x0) / (z1 - z0)


def z_sw_top(x):
    (x0, z0), (x1, z1) = SW_TOP
    return z0 + (x - x0) * (z1 - z0) / (x1 - x0)


def _poly(px, py, poly):
    from cad.sdf2d import polygon
    return polygon(px, py, poly)


def windshield_sdf(x, s, z, y=None):
    """Two flat-edged panes: plan-view outline intersected with 'forward of the A-pillar'."""
    ya = np.abs(y) if y is not None else np.abs(s)
    plan = _poly(x, ya, WS_PLAN)
    pillar = x - (x_pillar(z) - PILLAR_HALF)
    d = smax(plan, pillar, k=0.03)
    return np.where(z > 1.90, d, 10.0)


def sidewindow_sdf(x, y, z):
    h1 = (x_pillar(z) + PILLAR_HALF) - x
    h2 = SW_BOTTOM - z
    h3 = x - SW_REAR
    h4 = z - z_sw_top(x)
    d = smax(h1, h2, h3, h4, k=0.05)
    return np.where(np.abs(y) > 0.30, d, 10.0)


def surround_sdf(x, y, z, s, grow=0.034):
    a = windshield_sdf(x, s, z, y) - grow
    b = sidewindow_sdf(x, y, z) - grow
    d = smin(a, b, k=0.10)
    return np.where((x > 3.05) & (x < 4.5) & (z > 1.8), d, 10.0)
