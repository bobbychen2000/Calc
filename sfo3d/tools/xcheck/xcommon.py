"""Shared helpers for the stand / runway cross-check (tools/xcheck).

Coordinate frame = the app's, reimplemented exactly from js/geo.js:
  ARP 37.6188056 N, -122.3754167 E; E = (lon - lon0) * 111320 * cos(lat0); N = (lat - lat0) * 110990;
  world x = E, z = -N (metres); headings: hdgVec(h) = [sin h, -cos h]  =>  h = atan2(dx, -dz).
(That equirectangular scale is 0.12 % short in E at 37.6 N versus WGS-84 (88 266 m/deg, pyproj); it is the frame
the stands were surveyed in, so all comparisons here use it; true geodesic distances are computed with pyproj where an
absolute length is compared, e.g. runway lengths.)
"""
import json, math, os, re
from pyproj import Geod

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LAT0, LON0 = 37.6188056, -122.3754167
MLAT = 110990.0
MLON = 111320.0 * math.cos(math.radians(LAT0))
GEOD = Geod(ellps='WGS84')
FT = 0.3048


def ll_to_world(lat, lon):
    return ((lon - LON0) * MLON, -(lat - LAT0) * MLAT)


def world_to_ll(x, z):
    return (LAT0 + (-z) / MLAT, LON0 + x / MLON)


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
