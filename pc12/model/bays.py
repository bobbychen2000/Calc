"""Landing-gear bay openings (shared by wing, fuselage and gear builders)."""
import numpy as np
from cad import sdf2d

# right-side plan-view shapes (x, y) -- mirrored by |y|
# main wheel well: round, sized to the 22 x 8.50-10 tyre lying flat (POH: no wheel door, the tyre protrudes
# ~1 in when retracted), centred on gear.retracted_wheel() (STA 6.4105, BL 1.474).
# Stage 3 (CONS-01 / M1 / M6): the leg slot is the plan footprint of the retracted leg door (gear.leg_door_footprint,
# the drawn door face turned 90 deg inboard with the leg), less DOOR_LAP so the door overlaps its edge; it also passes
# the shock strut and trailing arm.  The leg front, trunnion and side brace cross the lower skin just ahead of it
# (FWD_SLOT), and the folded brace links lie inside the wing inboard of the slot, in the liner pocket BRACE_POCKET.
# Nose bay = the drawn nose-door rectangle (STA 2.887-4.252, 0.30 wide) moved aft with the nose gear by
# gear.GEAR_SHIFT.
WELL = dict(cx=6.4105, cy=1.474, hx=0.300, hy=0.300, r=0.300)
DOOR_LAP = 0.004                                                  # door overlap over the slot edge (m)
# the leg's forward half (the drawn door's forward edge is at the leg axis), the trunnion fitting and the side brace's
# lower link cross the lower skin just ahead of the door footprint: a forward slot, uncovered when retracted
FWD_SLOT = dict(cx=5.9585, cy=1.8975, hx=0.1035, hy=0.4475, r=0.040)     # x 5.855-6.062, BL 1.45-2.345
BRACE_POCKET = dict(cx=5.978, cy=1.500, hx=0.084, hy=0.350, r=0.040)     # x 5.894-6.062, BL 1.15-1.85 (liner)
MAIN_BAY_Y = (1.10, 2.45)                                         # BL range of the main bay (dense wing span rows)
NOSE_BAY = dict(cx=3.5866, cy=0.0, hx=0.6825, hy=0.150, r=0.05)       # nose wheel bay

_SLOT_POLY = None


def _smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def leg_slot_polygon():
    """Starboard plan outline (x, y) of the leg slot's footprint: gear.leg_door_footprint() (cached)."""
    global _SLOT_POLY
    if _SLOT_POLY is None:
        from model import gear as G
        _SLOT_POLY = np.asarray(G.leg_door_footprint(1), float)
    return _SLOT_POLY


def leg_slot_sdf(x, y):
    return sdf2d.polygon(x, np.abs(y), leg_slot_polygon()) + DOOR_LAP


def main_opening_sdf(x, y):
    """Main-gear opening in the wing lower skin (negative = hole): wheel well + leg slot (door footprint) + forward
    slot (leg front, trunnion, side brace)."""
    ya = np.abs(y)
    a = sdf2d.rrect(x, ya, WELL["cx"], WELL["cy"], WELL["hx"], WELL["hy"], WELL["r"])
    b = leg_slot_sdf(x, ya)
    c = sdf2d.rrect(x, ya, FWD_SLOT["cx"], FWD_SLOT["cy"], FWD_SLOT["hx"], FWD_SLOT["hy"], FWD_SLOT["r"])
    return _smin(_smin(a, b, 0.06), c, 0.04)


def main_bay_sdf(x, y):
    """Main-gear bay liner region in plan (negative inside): the opening plus the brace pocket inboard of it."""
    ya = np.abs(y)
    p = sdf2d.rrect(x, ya, BRACE_POCKET["cx"], BRACE_POCKET["cy"], BRACE_POCKET["hx"], BRACE_POCKET["hy"],
                    BRACE_POCKET["r"])
    return _smin(main_opening_sdf(x, ya), p, 0.04)


def nose_bay_sdf(x, y):
    return sdf2d.rrect(x, y, NOSE_BAY["cx"], NOSE_BAY["cy"], NOSE_BAY["hx"], NOSE_BAY["hy"], NOSE_BAY["r"])
