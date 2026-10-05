"""
FID3-07 (yoke rev L): the knee checks of sheet L6B re-run with the yoke's neutral moved forward, for the owner's open
point on the fore-aft station (every posed photo puts the aft face 14-65 mm forward of the drawn neutral).  Prints
(95th contact roll, wings-level clearance) now and with the shift; the numbers are copied into drawing/yoke_sheet.py
STATION_KNEE.

    python3 -m drawing.yoke_station [shift_mm]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import interior as I  # noqa: E402


def knees(shift_mm=0.0):
    keep = I.YOKE["hub_dx"]
    try:
        I.YOKE["hub_dx"] = I.P(float(keep) - shift_mm * 1e-3, keep.src)
        r = I.crew_checks(-1)
        o = r["occ"]["p95m"]
        return float(o["roll_contact"]), 1000.0 * float(o["yoke_pitch"])
    finally:
        I.YOKE["hub_dx"] = keep


if __name__ == "__main__":
    sh = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0
    c0, p0 = knees(0.0)
    c1, p1 = knees(sh)
    print(f"STATION_SHIFT = {sh:g}")
    print(f"STATION_KNEE = ({c0:.1f}, {c1:.1f}, {p0:.1f}, {p1:.1f})")
