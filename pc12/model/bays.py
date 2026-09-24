"""Landing-gear bay openings (shared by wing, fuselage and gear builders)."""
import numpy as np
from cad import sdf2d

# right-side plan-view rounded rectangles (x, y) -- mirrored by |y|
# main wheel well: round, sized to the 22 x 8.50-10 tyre lying flat (POH: no wheel door,
# the tyre protrudes ~1 in when retracted); leg slot closed by the single leg-mounted door
WELL = dict(cx=6.43, cy=1.540, hx=0.300, hy=0.300, r=0.300)
SLOT = dict(cx=6.025, cy=1.975, hx=0.095, hy=0.360, r=0.05)
NOSE_BAY = dict(cx=3.64, cy=0.0, hx=0.62, hy=0.14, r=0.05)       # nose wheel bay


def _smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def main_opening_sdf(x, y):
    ya = np.abs(y)
    a = sdf2d.rrect(x, ya, WELL["cx"], WELL["cy"], WELL["hx"], WELL["hy"], WELL["r"])
    b = sdf2d.rrect(x, ya, SLOT["cx"], SLOT["cy"], SLOT["hx"], SLOT["hy"], SLOT["r"])
    return _smin(a, b, 0.12)


def nose_bay_sdf(x, y):
    return sdf2d.rrect(x, y, NOSE_BAY["cx"], NOSE_BAY["cy"], NOSE_BAY["hx"], NOSE_BAY["hy"], NOSE_BAY["r"])
