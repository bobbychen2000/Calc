"""
Flight-deck detail, track A (flight deck r1 GEOM A, owner 2026-10-04 "the details are drastically missing"): the panel
area -- yokes, rudder pedals and footwells, glareshield hood, GFC 700 / eyebrow fascia, lower panel, panel zoning,
centre stack and pedestal.  The helpers and builders the owned model/flightdeck.py functions call (_yokes, _pedals,
_glareshield, _lower_panel, _pedestal, _panel_face) and the hook _detail_a(acc) that model/flightdeck.build_flightdeck
calls after _pedals.

Every dimension the sheets L6 / L6B draw comes from the interior tables (PANEL, GLARESHIELD, YOKE, PEDALS, PEDESTAL);
the sizes here are builder-level detail (knobs, keys, bezels, screws, stitching), tagged [M] (measured on the
gitignored reference photos: P1046406 / 08 / 09 / 10 of PRO s/n 3001, the JTF p.18 cockpit key, the brochure pp.10 /
12, the Pilatus throttle photo) or [E].  No markings: legends are abstract strokes and pictograms in light_white /
the annunciator colours (no text, no logos; the legend atlas is the seed's).  Segment counts are explicit (the flight
deck is rebuilt at RES 2 in the light tier too once build.LOW_FINE takes it: the seed's job).
"""
from __future__ import annotations

# the builders live in model/fd_kit.py (helpers), fd_footwell.py, fd_panel.py and fd_pedestal.py (first-principles
# flight deck A1: the code split by area, the build byte-identical); this module re-exports them for its callers
from model import fd_kit as _kit, fd_footwell as _fw, fd_panel as _pn, fd_pedestal as _pd

for _m in (_kit, _fw, _pn, _pd):
    globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__") and k != "annotations"})
del _m


# =====================================================================================================================
# the hook called by model/flightdeck.build_flightdeck after _pedals
# =====================================================================================================================
def _detail_a(acc):
    """Track A's extra flight-deck pieces (none yet: the owned builders call the helpers above)."""
    return acc
