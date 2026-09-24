"""Landing-gear bay openings (shared by wing, fuselage and gear builders)."""
import numpy as np
from cad import sdf2d

# right-side plan-view rounded rectangles (x, y) -- mirrored by |y|
# main wheel well: round, sized to the 22 x 8.50-10 tyre lying flat (POH: no wheel door, the tyre protrudes
# ~1 in when retracted), centred on gear.retracted_wheel() (STA 6.4105, BL 1.474); leg slot along the
# retracted leg (x 5.93-6.10) from the trunnion (BL 2.265) inboard, closed by the single leg-mounted door.
# Stage 2 (rev B): follow the moved gear (gear.MAIN_AXLE / MAIN_TRUNNION); nose bay = the drawn nose-door
# rectangle (STA 2.887-4.252, 0.30 wide) moved aft with the nose gear by gear.GEAR_SHIFT.
WELL = dict(cx=6.4105, cy=1.474, hx=0.300, hy=0.300, r=0.300)
SLOT = dict(cx=6.020, cy=1.970, hx=0.120, hy=0.370, r=0.05)
NOSE_BAY = dict(cx=3.5866, cy=0.0, hx=0.6825, hy=0.150, r=0.05)       # nose wheel bay


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
