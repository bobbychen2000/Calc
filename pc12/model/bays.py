"""Landing-gear bay openings (shared by wing, fuselage and gear builders)."""
import numpy as np
from cad import sdf2d

# right-side plan-view shapes (x, y) -- mirrored by |y|
# Main gear, Stage 3 leg-door decision LD-1 (see model/gear.py): the opening in the wing lower skin is exactly what the
# retracted gear closes, so the underside is flush with only the tyre showing:
#   * the leg slot = the plan footprint of the retracted leg door (gear.leg_door_footprint: the door face, scalloped
#     round the tyre, with the forward tab over the leg's skin crossing) plus DOOR_GAP all round (a panel gap: the
#     closed door's outer face lies in the skin surface, so the two never overlap / z-fight);
#   * the wheel well = a circle WELL_R about the retracted wheel centre (gear.retracted_wheel): the tyre protrudes
#     ~1 in through it (POH), the door's scallop is its other half;
#   * no forward slot any more: the leg now passes the skin behind the door's forward edge (gear.MAIN_TRUNNION), and
#     the trunnion pin, the leg top and the swinging door tab stay inside the wing (liner pocket TRUNNION_POCKET only).
# The bay LINER (main_bay_sdf) is the opening plus liner-only pockets above the intact skin: BRACE_POCKET (folded side
# brace links / knee) and TRUNNION_POCKET.
# Nose bay = the drawn nose-door rectangle (STA 2.887-4.252, 0.30 wide) moved aft with the nose gear by
# gear.GEAR_SHIFT.
DOOR_GAP = 0.003                                                  # closed leg door -> skin cut-out edge (m)
WELL_R = 0.292 + DOOR_GAP              # main wheel well: the door's tyre scallop (gear.LEG_DOOR scallop_r) + the gap
#                                        (the stowed tyre, tilted 4 deg, is 287 mm half-wide in plan: 8 mm clear)
TRUNNION_POCKET = dict(cx=5.995, cy=2.300, hx=0.100, hy=0.115, r=0.040)  # x 5.895-6.095, BL 2.185-2.415 (liner)
BRACE_POCKET = dict(cx=6.040, cy=1.480, hx=0.070, hy=0.370, r=0.040)     # x 5.970-6.110, BL 1.11-1.85 (liner)
MAIN_BAY_Y = (1.04, 2.46)                                         # BL range of the main bay (dense wing span rows)
NOSE_BAY = dict(cx=3.5866, cy=0.0, hx=0.6825, hy=0.150, r=0.05)       # nose wheel bay

_SLOT_POLY = None
_WELL_C = None


def _smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def well_centre():
    """Plan centre (x, y) of the starboard main wheel well: the retracted wheel centre (cached)."""
    global _WELL_C
    if _WELL_C is None:
        from model import gear as G
        _WELL_C = np.asarray(G.retracted_wheel(1), float)[:2]
    return _WELL_C


def leg_slot_polygon():
    """Starboard plan outline (x, y) of the leg slot's footprint: gear.leg_door_footprint() (cached)."""
    global _SLOT_POLY
    if _SLOT_POLY is None:
        from model import gear as G
        _SLOT_POLY = np.asarray(G.leg_door_footprint(1), float)
    return _SLOT_POLY


_SLOT_TREE = None


def footprint_sdf(x, y):
    """Signed distance (m, negative inside) to the leg door's retracted footprint (starboard, |y| used): distance to
    the outline resampled at 0.5 mm (KD-tree; < 0.1 mm off the exact segment distance at the gap) signed by a
    point-in-polygon test -- the exact sdf2d.polygon is O(points x vertices), too slow for the liner contour."""
    global _SLOT_TREE
    from scipy.spatial import cKDTree
    from matplotlib.path import Path
    if _SLOT_TREE is None:
        P = leg_slot_polygon()
        Q = [a + (b - a) * (np.arange(max(1, int(np.ceil(np.linalg.norm(b - a) / 0.0005)))) /
                            max(1, int(np.ceil(np.linalg.norm(b - a) / 0.0005))))[:, None]
             for a, b in zip(P, np.roll(P, -1, 0))]
        _SLOT_TREE = (cKDTree(np.vstack(Q)), Path(P))
    tree, path = _SLOT_TREE
    x, y = np.broadcast_arrays(np.asarray(x, float), np.abs(np.asarray(y, float)))
    q = np.c_[x.ravel(), y.ravel()]
    d = tree.query(q)[0]
    inside = path.contains_points(q)
    return np.where(inside, -d, d).reshape(x.shape)


def leg_slot_sdf(x, y):
    """Leg slot in the lower skin (negative inside): the retracted door's footprint + DOOR_GAP."""
    return footprint_sdf(x, y) - DOOR_GAP


def well_sdf(x, y):
    c = well_centre()
    return np.hypot(x - c[0], np.abs(y) - c[1]) - WELL_R


def main_opening_sdf(x, y):
    """Main-gear opening in the wing lower skin (negative = hole): wheel well + leg slot (door footprint + gap).  A
    plain union (no blend): every part of the hole is closed by the door or filled by the tyre when retracted."""
    ya = np.abs(y)
    return np.minimum(well_sdf(x, ya), leg_slot_sdf(x, ya))


def main_bay_sdf(x, y):
    """Main-gear bay liner region in plan (negative inside): the opening plus the liner-only pockets above the intact
    skin (brace pocket inboard, trunnion pocket at the leg top)."""
    ya = np.abs(y)
    p = sdf2d.rrect(x, ya, BRACE_POCKET["cx"], BRACE_POCKET["cy"], BRACE_POCKET["hx"], BRACE_POCKET["hy"],
                    BRACE_POCKET["r"])
    q = sdf2d.rrect(x, ya, TRUNNION_POCKET["cx"], TRUNNION_POCKET["cy"], TRUNNION_POCKET["hx"], TRUNNION_POCKET["hy"],
                    TRUNNION_POCKET["r"])
    return _smin(_smin(main_opening_sdf(x, ya), p, 0.04), q, 0.04)


def nose_bay_sdf(x, y):
    return sdf2d.rrect(x, y, NOSE_BAY["cx"], NOSE_BAY["cy"], NOSE_BAY["hx"], NOSE_BAY["hy"], NOSE_BAY["r"])
