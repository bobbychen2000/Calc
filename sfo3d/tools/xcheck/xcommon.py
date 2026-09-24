"""Shared helpers for the stand / runway cross-check (tools/xcheck).

Coordinate frame = the app's world frame, from the shared module tools/geo_frame.py (= js/geo.js, frame
'ltp-nad83-2011' since 24 Sep 2026): exact GRS80 local tangent plane at the ARP 37.6188056 N, -122.3754167 E,
datum NAD83(2011); world x = east, z = south (metres); headings: hdgVec(h) = [sin h, -cos h] => h = atan2(dx, -dz).
  ll_to_world / world_to_ll   : NAD83(2011) lat/lon (FAA NASR, AirNav, SFO Museum)
  wgs84_to_world / world_to_wgs84 : WGS 84 lat/lon (OSM, X-Plane Gateway, ADS-B) - applies the measured
                                    NAD83(2011) -> WGS 84 (G2296) displacement at SFO (dE -1.568 m, dN +0.159 m)
  wgs84_to_nad83              : WGS 84 lat/lon -> the NAD83(2011) lat/lon of the same ground point (for geodesic
                                comparisons against NASR)
The research of 24 Sep 2026 (docs/research/stands_xcheck.md) was computed in the LEGACY equirectangular frame
(E = (lon - lon0) * 111320 cos(lat0), N = (lat - lat0) * 110990) with every source taken as-is (no datum shift);
re-running these tools now gives numbers in the new frame, with OSM / X-Plane / ADS-B moved 1.58 m (datum).
"""
import json, math, os, re
from pyproj import Geod

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF
LAT0, LON0 = GF.ARP_LAT, GF.ARP_LON
GEOD = Geod(ellps='GRS80')
FT = 0.3048
ll_to_world = GF.ll_to_world          # NAD83(2011) lat/lon -> world (x, z)
world_to_ll = GF.world_to_ll
wgs84_to_world = GF.wgs84_to_world    # WGS 84 lat/lon -> world (x, z)
world_to_wgs84 = GF.world_to_wgs84


def wgs84_to_nad83(lat, lon):
    return GF.world_to_ll(*GF.wgs84_to_world(lat, lon))


def world_hdg(dx, dz):
    return math.degrees(math.atan2(dx, -dz)) % 360.0


def hdg_vec(h):
    r = math.radians(h); return (math.sin(r), -math.cos(r))


def hdg_diff(a, b):
    """signed a - b in (-180, 180]"""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


def geod_dist(lat1, lon1, lat2, lon2):
    return GEOD.inv(lon1, lat1, lon2, lat2)[2]


def load_stands():
    d = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    return d


def rwy_ends_geojs():
    """RWY_ENDS parsed from js/geo.js (the values the app uses): {id: {lat, lon, elev_ft, disp_ft}}"""
    s = open(os.path.join(ROOT, 'js', 'geo.js')).read()
    out = {}
    for m in re.finditer(r"'(\w+)':\s*\{\s*lat:\s*dms\((\d+),\s*([\d.]+)\),\s*lon:\s*-dms\((\d+),\s*([\d.]+)\),\s*"
                         r"elev:\s*([\d.]+),\s*disp:\s*(\d+)", s):
        k, la, lam, lo, lom, el, dp = m.groups()
        out[k] = {'lat': int(la) + float(lam) / 60, 'lon': -(int(lo) + float(lom) / 60), 'elev_ft': float(el),
                  'disp_ft': float(dp), 'lat_dm': f'{la} {lam}', 'lon_dm': f'{lo} {lom}'}
    return out


def pairs_of_runways():
    return [('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')]


def fmt(v, n=1):
    return '—' if v is None else (f'{v:.{n}f}' if isinstance(v, float) else str(v))
