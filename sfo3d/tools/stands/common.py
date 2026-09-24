"""Shared loaders for the stand rebuild (tools/stands/).

Frame: the app's world frame (tools/geo_frame.py = js/geo.js, 'ltp-nad83-2011'): x = east, z = south, metres from
the ARP; true headings with hdgVec(h) = [sin h, -cos h].

Sources (all local caches, gitignored under refs/cache/):
  NAIP 2024 0.5 m world raster  refs/cache/naip/naip_2024_world_0.5m.png (+ .json transform; USDA NAIP, public
                                domain; source 0.6 m UTM 10N, acquired 2024-05-20). A .npy copy is made on first use
                                for fast random access.
  OSM                           refs/cache/osm/ksfo_osm_parsed.json (tools/xcheck/parse_osm.py; (c) OpenStreetMap
                                contributors, ODbL 1.0). WGS 84 lat/lon -> world with geo_frame.wgs84_to_world.
  SFO Museum outlines           data/sfo_airport.json (CDLA-Permissive-1.0), already in the world frame.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

CACHE = os.path.join(ROOT, 'refs', 'cache')
WORK = os.path.join(CACHE, 'stands')          # outputs that embed NAIP pixels / OSM geometry stay here
os.makedirs(WORK, exist_ok=True)
NAIP_PNG = os.path.join(CACHE, 'naip', 'naip_2024_world_0.5m.png')
NAIP_META = os.path.join(CACHE, 'naip', 'naip_2024_world_0.5m.json')
NAIP_NPY = os.path.join(CACHE, 'naip', 'naip_2024_world_0.5m_bgr.npy')
OSM_PARSED = os.path.join(CACHE, 'osm', 'ksfo_osm_parsed.json')


def hdg_vec(h):
    r = math.radians(h); return (math.sin(r), -math.cos(r))


def vec_hdg(dx, dz):
    return math.degrees(math.atan2(dx, -dz)) % 360.0


def hdiff(a, b):
    """signed a - b in (-180, 180]"""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


# ------------------------------------------------------------------------------------------------ NAIP raster
class Naip:
    """NAIP 2024 world raster (BGR uint8), 0.5 m pixels, pixel centres at x0 + (col + 0.5) * res."""
    def __init__(self):
        m = json.load(open(NAIP_META)); self.meta = m
        self.res, self.x0, self.z0 = m['res'], m['x0'], m['z0']
        assert m['frame'] == GF.FRAME_ID, (m['frame'], GF.FRAME_ID)
        if not os.path.exists(NAIP_NPY):
            import cv2
            np.save(NAIP_NPY, cv2.imread(NAIP_PNG, cv2.IMREAD_COLOR))
        self.im = np.load(NAIP_NPY, mmap_mode='r')

    def px(self, x, z):
        return ((np.asarray(x) - self.x0) / self.res - 0.5, (np.asarray(z) - self.z0) / self.res - 0.5)

    def world(self, col, row):
        return (self.x0 + (np.asarray(col) + 0.5) * self.res, self.z0 + (np.asarray(row) + 0.5) * self.res)

    def patch(self, cx, cz, hdg, along, across, res=0.25):
        """resample an oriented patch: rows run along `hdg` (row 0 = +along/2 ahead), columns across (+ = right of the
        heading). Returns (BGR image, (u_along, v_right) grids). Bilinear."""
        import cv2
        f = hdg_vec(hdg); r = (-f[1], f[0])   # right-hand side of the heading in (x, z): rotate f by +90 deg
        # in x-east / z-south, right of heading h is heading h + 90: (sin(h+90), -cos(h+90)) = (cos h, sin h)
        r = (math.cos(math.radians(hdg)), math.sin(math.radians(hdg)))
        nu, nv = int(round(along / res)), int(round(across / res))
        u = along / 2 - (np.arange(nu) + 0.5) * res          # along (+ ahead)
        v = -across / 2 + (np.arange(nv) + 0.5) * res        # right
        U, V = np.meshgrid(u, v, indexing='ij')
        X = cx + U * f[0] + V * r[0]; Z = cz + U * f[1] + V * r[1]
        c, rr = self.px(X, Z)
        img = cv2.remap(np.ascontiguousarray(self._window(c, rr)[0]), (c - self._c0).astype(np.float32),
                        (rr - self._r0).astype(np.float32), cv2.INTER_LINEAR)
        return img, U, V

    def _window(self, c, r):
        c0 = max(0, int(np.floor(c.min())) - 2); r0 = max(0, int(np.floor(r.min())) - 2)
        c1 = min(self.im.shape[1], int(np.ceil(c.max())) + 3); r1 = min(self.im.shape[0], int(np.ceil(r.max())) + 3)
        self._c0, self._r0 = c0, r0
        return (self.im[r0:r1, c0:c1],)

    def crop(self, x0, z0, x1, z1):
        """axis-aligned crop (north up) and the (col0, row0) of its corner"""
        c0, r0 = [int(np.floor(v)) for v in self.px(x0, z0)]
        c1, r1 = [int(np.ceil(v)) for v in self.px(x1, z1)]
        return np.ascontiguousarray(self.im[max(r0, 0):r1, max(c0, 0):c1]), (max(c0, 0), max(r0, 0))


# ------------------------------------------------------------------------------------------------ OSM
def load_osm():
    d = json.load(open(OSM_PARSED))
    for p in d['parking_positions']:
        p['w'] = [GF.wgs84_to_world(la, lo) for la, lo in p['pts']]
    for b in d['jet_bridges']:
        b['w'] = [GF.wgs84_to_world(la, lo) for la, lo in b['pts']]
    for g in d['gates']:
        g['w'] = GF.wgs84_to_world(*g['pt'])
    for k in ('stopways', 'runways', 'aprons', 'terminals', 'taxiways', 'holding_positions'):
        for r in d.get(k, []):
            r['w'] = [GF.wgs84_to_world(la, lo) for la, lo in r['pts']]
    return d


# ------------------------------------------------------------------------------------------------ SFO Museum outlines
def load_airport():
    return json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))


def building_rings(D=None):
    """terminal complex + boarding areas (outer rings and holes), world [x, z]"""
    D = D or load_airport(); out = []
    for poly in D['terminalComplex']: out += [np.array(r, float) for r in poly]
    for b in D['boardingAreas']:
        for poly in b['polys']: out += [np.array(r, float) for r in poly]
    return out


def building_mask(D=None, res=0.5, bounds=(-2000.0, -800.0, 400.0, 1600.0)):
    """raster of the terminal buildings (1 inside) with its transform; bounds = (x0, z0, x1, z1)"""
    import cv2
    D = D or load_airport(); x0, z0, x1, z1 = bounds
    W, H = int((x1 - x0) / res), int((z1 - z0) / res)
    M = np.zeros((H, W), np.uint8)
    polys = list(D['terminalComplex']) + [p for b in D['boardingAreas'] for p in b['polys']]
    for poly in polys:
        for i, ring in enumerate(poly):
            pts = np.array([[(x - x0) / res, (z - z0) / res] for x, z in ring])
            cv2.fillPoly(M, [np.round(pts * 4).astype(np.int32)], 1 if i == 0 else 0, shift=2)
    return M, (x0, z0, res)


class Buildings:
    def __init__(self, D=None):
        self.M, (self.x0, self.z0, self.res) = building_mask(D)
        import cv2
        # distance (m) from each outside pixel to the nearest building pixel
        self.dist = cv2.distanceTransform((1 - self.M).astype(np.uint8), cv2.DIST_L2, 5) * self.res

    def _ij(self, x, z):
        return int((z - self.z0) / self.res), int((x - self.x0) / self.res)

    def inside(self, x, z):
        i, j = self._ij(x, z)
        return 0 <= i < self.M.shape[0] and 0 <= j < self.M.shape[1] and bool(self.M[i, j])

    def d(self, x, z):
        i, j = self._ij(x, z)
        if 0 <= i < self.M.shape[0] and 0 <= j < self.M.shape[1]: return float(self.dist[i, j])
        return 1e9
