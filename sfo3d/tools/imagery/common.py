"""Shared constants and coordinate helpers for the orthoimagery tools (tools/imagery/).

World frame (js/geo.js = tools/geo_frame.py, since 24 Sep 2026): x = east (m), z = south (m), origin = ARP
37.6188056 N, -122.3754167 E, exact GRS80 local tangent plane, datum NAD83(2011): `world_new` / `ll_new`.
`world_ltp` / `ll_ltp` compute the same plane through pyproj (agree to 1e-10 m).
LEGACY frame 'equirect-v1' (js/geo.js before 24 Sep 2026; the frame of the research in docs/research/imagery.md, of
reg.json and of refs/cache/naip/reg_naip.json): spherical equirectangular, M_PER_DEG_LAT = 110990,
M_PER_DEG_LON = 111320 * cos(lat0): `world_geojs` / `ll_geojs`.
NaipSampler and world_to_utm / utm_to_world use the current frame unless frame='legacy' is passed.

Area of interest (task spec): lat 37.595..37.640, lon -122.405..-122.350.
Third-party downloads go to refs/cache/naip/ (gitignored, licensed data stays local).
"""
import math, os, json, sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF
CACHE = os.path.join(ROOT, 'refs', 'cache', 'naip')
os.makedirs(CACHE, exist_ok=True)

# ---- js/geo.js constants (copied verbatim; source: js/geo.js lines 3-5) ----
ARP_LAT, ARP_LON = 37.6188056, -122.3754167
M_PER_DEG_LAT = 110990.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(ARP_LAT))

# AOI (task specification)
AOI = dict(lat0=37.595, lat1=37.640, lon0=-122.405, lon1=-122.350)


def world_new(lat, lon):
    """current world frame (js/geo.js llToWorld, NAD83(2011) lat/lon) -> (x east, z south). Vectorised."""
    return GF.ll_to_world_np(lat, lon)


def ll_new(x, z):
    """inverse of world_new -> (lat, lon). Vectorised, exact to < 1e-9 m."""
    return GF.world_to_ll_np(x, z)


def world_geojs(lat, lon):
    """LEGACY frame (js/geo.js llToWorld before 24 Sep 2026) -> (x east, z south) in metres. Vectorised."""
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    return (lon - ARP_LON) * M_PER_DEG_LON, -(lat - ARP_LAT) * M_PER_DEG_LAT


def ll_geojs(x, z):
    """inverse of world_geojs -> (lat, lon)."""
    x = np.asarray(x, float); z = np.asarray(z, float)
    return ARP_LAT + (-z) / M_PER_DEG_LAT, ARP_LON + x / M_PER_DEG_LON


# ---- FAA runway ends (copied verbatim from js/geo.js RWY_ENDS; AirNav / FAA NASR, NAD83, degrees-minutes) ----
def _dms(d, m): return d + m / 60.0
RWY_ENDS = {
    '10L': (_dms(37, 37.724323), -_dms(122, 23.603512)),
    '28R': (_dms(37, 36.812017), -_dms(122, 21.428467)),
    '10R': (_dms(37, 37.577467), -_dms(122, 23.586327)),
    '28L': (_dms(37, 36.702717), -_dms(122, 21.500950)),
    '1L': (_dms(37, 36.473872), -_dms(122, 22.975710)),
    '19R': (_dms(37, 37.588882), -_dms(122, 22.236565)),
    '1R': (_dms(37, 36.379793), -_dms(122, 22.862445)),
    '19L': (_dms(37, 37.640532), -_dms(122, 22.026650)),
}
RWY_PAIRS = [('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')]
RWY_WIDTH_M = 200 * 0.3048


def _pyproj():
    import pyproj
    return pyproj


def ltp_transformer(datum='EPSG:4326'):
    """geodetic (lon, lat, h) in `datum` -> local ENU at the ARP on the GRS80/WGS84 ellipsoid (pyproj pipeline)."""
    pj = _pyproj()
    pipe = (f'+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad '
            f'+step +proj=cart +ellps=GRS80 '
            f'+step +proj=topocentric +ellps=GRS80 +lat_0={ARP_LAT} +lon_0={ARP_LON} +h_0=0')
    return pj.Transformer.from_pipeline(pipe)


def world_ltp(lat, lon, h=0.0):
    """rigorous local tangent plane (ENU on GRS80) -> (x east, z south, up)."""
    T = ltp_transformer()
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    e, n, u = T.transform(lon, lat, np.zeros_like(lat) + h)
    return np.asarray(e), -np.asarray(n), np.asarray(u)


def utm_to_ll(E, N, epsg=26910):
    pj = _pyproj()
    T = pj.Transformer.from_crs(f'EPSG:{epsg}', 'EPSG:4269', always_xy=True)
    lon, lat = T.transform(E, N)
    return np.asarray(lat), np.asarray(lon)


def ll_to_utm(lat, lon, epsg=26910):
    pj = _pyproj()
    T = pj.Transformer.from_crs('EPSG:4269', f'EPSG:{epsg}', always_xy=True)
    E, N = T.transform(lon, lat)
    return np.asarray(E), np.asarray(N)


def world_to_utm(x, z, epsg=26910, frame='world'):
    """world (x, z) -> UTM E, N (NAD83). frame='legacy' for equirect-v1 coordinates."""
    lat, lon = ll_geojs(x, z) if frame == 'legacy' else ll_new(x, z)
    return ll_to_utm(lat, lon, epsg)


def utm_to_world(E, N, epsg=26910, frame='world'):
    lat, lon = utm_to_ll(E, N, epsg)
    return world_geojs(lat, lon) if frame == 'legacy' else world_new(lat, lon)


def load_world_png_meta(path=None):
    path = path or os.path.join(CACHE, 'naip_2024_world_0.5m.json')   
    return json.load(open(path))


class WorldRaster:
    """world (x, z) <-> pixel (col, row) for the world-grid mosaic written by naip_world.py.
    Pixel centres: col = (x - x0) / res - 0.5, row = (z - z0) / res - 0.5 (x0, z0 = outer corner of pixel 0,0)."""
    def __init__(self, meta):
        self.x0, self.z0, self.res = meta['x0'], meta['z0'], meta['res']
        self.W, self.H = meta['width'], meta['height']

    def fwd(self, x, z):
        return (np.asarray(x) - self.x0) / self.res - 0.5, (np.asarray(z) - self.z0) / self.res - 0.5

    def inv(self, c, r):
        return self.x0 + (np.asarray(c) + 0.5) * self.res, self.z0 + (np.asarray(r) + 0.5) * self.res


class NaipSampler:
    """bilinear sampling of the NAIP GeoTIFF (EPSG:26910) at world (x, z) points (current frame, or frame='legacy').
    Uses the exact per-point mapping world -> lat/lon -> UTM -> pixel, so no resampling error is baked in."""
    def __init__(self, year='2024', bands=(1, 2, 3), frame='world'):
        import rasterio, pyproj
        self.ll = ll_geojs if frame == 'legacy' else ll_new
        with rasterio.open(os.path.join(CACHE, f'naip_{year}_sfo_utm10n.tif')) as ds:
            self.img = np.transpose(ds.read(list(bands)), (1, 2, 0)).copy(); self.inv = ~ds.transform
        self.T = pyproj.Transformer.from_crs('EPSG:4269', 'EPSG:26910', always_xy=True)

    def __call__(self, X, Z, gray=True, shift=(0.0, 0.0)):
        import cv2
        X = np.asarray(X, float) + shift[0]; Z = np.asarray(Z, float) + shift[1]
        lat, lon = self.ll(X, Z)
        E, N = self.T.transform(lon, lat)
        c, r = self.inv * (E, N)
        mx = (np.asarray(c) - 0.5).astype(np.float32); my = (np.asarray(r) - 0.5).astype(np.float32)
        if mx.ndim == 1: mx, my = mx[None], my[None]
        im = self.img if not gray else cv2.cvtColor(self.img, cv2.COLOR_RGB2GRAY)
        out = cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return out.astype(np.float32)


def ll_ltp(x, z):
    """inverse of world_ltp (horizontal only, points on the ellipsoid surface h=0): world (x, z) -> (lat, lon).
    Uses the pyproj topocentric pipeline inverse on (E, N, U) with U = -d^2/(2R) (the ellipsoid drops below the
    tangent plane); two fixed-point iterations make the round trip exact to < 1 mm over the AOI."""
    T = ltp_transformer()
    x = np.asarray(x, float); z = np.asarray(z, float)
    e, n = x, -z
    u = -(e * e + n * n) / (2 * 6371000.0)
    for _ in range(3):
        lon, lat, h = T.transform(e, n, u, direction='INVERSE')
        u = u - np.asarray(h)          # push the point onto h = 0
    lon, lat, h = T.transform(e, n, u, direction='INVERSE')
    return np.asarray(lat), np.asarray(lon)
