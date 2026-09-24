"""Migration helper for the recommended js/geo.js projection fix (docs/research/imagery.md, section 3).

Old world frame  = js/geo.js today: spherical equirectangular (M_PER_DEG_LAT 110990, M_PER_DEG_LON 111320*cos lat0).
New world frame  = local tangent plane (ENU) on GRS80 at the same ARP (exact; what pyproj 'topocentric' computes).
Both take lat/lon as NAD83(2011) (the FAA / NAIP datum); ADS-B (WGS 84 ~ ITRF @ epoch) is converted separately
by a constant shift (see projection_audit.py).

    old_to_new(x, z) = world_ltp(ll_geojs(x, z))      exact, pointwise
    new_to_old(x, z) = world_geojs(ll_ltp(x, z))

Anything that was *derived from lat/lon* (FAA runway ends, SFO Museum geometry, ADS-B) should simply be rebuilt with
the new projection.  Anything *measured in world metres* (tools/sat stands, bridges, red boxes, paint, pavement -
all measured on screenshots registered in the old frame) is converted pointwise with old_to_new.  The field is
smooth (<= 0.62 m within 500 m of the ARP, 1.9 m at 1.5 km, 4.1 m at the AOI corners); the relative change
between points 100 m apart is <= 0.13 m, so stand spacing / clearances are unaffected.

CLI (never writes into data/ unless you pass that path explicitly):
    python3 tools/imagery/migrate_world.py data/sfo_stands.json refs/cache/naip/sfo_stands_ltp.json \
        --keys nose,attach,redBoxes
Every [x, z] pair (2 numbers) found under the listed keys, at any depth, is converted; everything else is copied.
Headings stored in degrees (keys 'hdg') are corrected by the local grid rotation of the mapping (< 0.05 deg).
"""
import argparse, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def old_to_new(x, z):
    la, lo = ll_geojs(x, z); X, Z, _ = world_ltp(la, lo); return X, Z


def new_to_old(x, z):
    la, lo = ll_ltp(x, z); return world_geojs(la, lo)


def rotation_deg(x, z, d=10.0):
    """local rotation (deg, clockwise positive like a heading) that old_to_new applies to a heading at (x, z)."""
    x0, z0 = old_to_new(x, z); xn, zn = old_to_new(x, z - d)          # a 'north' step
    return math.degrees(math.atan2(float(xn - x0), -float(zn - z0)))


def convert(obj, keys, stats, under=False):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            u = under or (k in keys)
            if k == 'hdg' and isinstance(v, (int, float)) and 'nose' in obj:
                x, z = obj['nose']; out[k] = round((v + rotation_deg(x, z)) % 360, 3); continue
            out[k] = convert(v, keys, stats, u)
        return out
    if isinstance(obj, list):
        if under and len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj):
            X, Z = old_to_new(obj[0], obj[1]); d = math.hypot(float(X) - obj[0], float(Z) - obj[1])
            stats.append(d); return [round(float(X), 3), round(float(Z), 3)]
        return [convert(v, keys, stats, under) for v in obj]
    return obj


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--keys', default='nose,attach,redBoxes'); a = ap.parse_args()
    src = json.load(open(a.src)); stats = []
    out = convert(src, set(a.keys.split(',')), stats)
    json.dump(out, open(a.dst, 'w'), indent=1)
    s = np.array(stats) if stats else np.zeros(1)
    print(f'{len(stats)} points converted; displacement median {np.median(s):.2f} m, max {s.max():.2f} m -> {a.dst}')


if __name__ == '__main__':
    main()
