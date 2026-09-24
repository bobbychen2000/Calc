"""Georeferenced background imagery for the drawing sheets and the deviation measurements.

A background answers two questions in world coordinates (x east, z south, metres from the ARP):
  raster(x0, z0, x1, z1, res) -> (BGR image, valid mask), north-up, pixel (i, j) <-> (x0 + (j+.5) res, z0 + (i+.5) res)
  profiles(P)                 -> BGR samples along many short profiles, each profile read from ONE source image
                                 (P: (n, k, 2) world points) + per-profile image id and ground resolution (m/px)

Sources
  GoogleScreens  the owner's Google Maps screenshots (tools/sat/screens, similarity registrations in
                 tools/sat/work/reg.json). REFERENCE ONLY (licensed imagery): anything rendered from it goes to out/,
                 never to docs/. Per profile / pixel the registered screenshot with the finest resolution is used.
  GeoImage       any georeferenced image, e.g. public-domain NAIP under refs/cache/naip/. Discovered by
                 find_georef(): every *.json sidecar there that names an image and a transform, or a GeoTIFF with a CRS.
                 Accepted sidecar keys (first match wins):
                   image | file | path                         image file (relative to the json)
                   world_to_pixel | w2p | affine               2x3 [[a,b,c],[d,e,f]]: px = a x + b z + c, py = d x + e z + f
                                                               or a 3x3 homography on (x, z, 1)
                   pixel_to_world | p2w                        the inverse of the above (inverted here)
                   res_m | gsd | resolution                   ground sample distance (m/px), else from the transform
                   name, date, source, license                 reported in the sheets / report
                 A GeoTIFF with its own CRS is mapped world -> lat/lon (the app's local equirectangular frame, js/geo.js)
                 -> image CRS (pyproj) -> pixel (rasterio affine).
"""
import glob, json, math, os
import numpy as np
import cv2
from common import ROOT, scene

SAT = os.path.join(ROOT, 'tools', 'sat')
SCREENS = os.environ.get('SFO_SCREENS', os.path.join(SAT, 'screens'))
REGF = os.path.join(os.environ.get('SFO_SATWORK', os.path.join(SAT, 'work')), 'reg.json')
NAIP_DIR = os.environ.get('NAIP_DIR', os.path.join(ROOT, 'refs', 'cache', 'naip'))


class Source:
    name = '?'; kind = '?'; licence = ''; public = False

    def pixel(self, img_id, X, Z):  # world -> pixel coords in image img_id
        raise NotImplementedError

    def raster(self, x0, z0, x1, z1, res):
        W, H = int(round((x1 - x0) / res)), int(round((z1 - z0) / res))
        jj, ii = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
        X = x0 + (jj + 0.5) * res; Z = z0 + (ii + 0.5) * res
        out = np.zeros((H, W, 3), np.uint8); best = np.full((H, W), np.inf, np.float32)
        for k in self.images():
            mx, my = self.pixel(k, X.ravel(), Z.ravel()); mx = mx.reshape(H, W).astype(np.float32); my = my.reshape(H, W).astype(np.float32)
            v = self.valid(k, mx, my); r = self.gsd(k)
            take = v & (r < best)
            if not take.any(): continue
            im = self.image(k)
            interp = cv2.INTER_AREA if res > r * 1.5 else cv2.INTER_LINEAR
            if interp == cv2.INTER_AREA and res / r > 2:  # pre-shrink so remap does not alias
                f = r / res * 1.5; small = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
                rr = cv2.remap(small, mx * f, my * f, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            else:
                rr = cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            out[take] = rr[take]; best[take] = r
        return out, np.isfinite(best), best

    def profiles(self, P, only=None, need=0.9, exclude=None):
        """P (n,k,2) world points -> vals (n,k,3) float32 BGR, img (n,) image id or None, gsd (n,).
        exclude: (n,) image ids not to use per profile (to get a second, independent reading)"""
        n, k, _ = P.shape
        vals = np.full((n, k, 3), np.nan, np.float32); ids = np.full(n, None, object); gsd = np.full(n, np.inf)
        X = P[..., 0].ravel(); Z = P[..., 1].ravel()
        for im_id in (self.images() if only is None else [only]):
            mx, my = self.pixel(im_id, X, Z); mx = mx.reshape(n, k); my = my.reshape(n, k)
            v = self.valid(im_id, mx, my)
            frac = v.mean(1); r = self.gsd(im_id)
            take = (frac >= need) & (r < gsd)
            if exclude is not None: take &= np.array([not (e is not None and e == im_id) for e in exclude], bool)
            if not take.any(): continue
            im = self.image(im_id)
            rr = cv2.remap(im, mx[take].astype(np.float32), my[take].astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
            rr[~v[take]] = np.nan
            vals[take] = rr; gsd[take] = r
            for j in np.where(take)[0]: ids[j] = im_id
        return vals, ids, gsd


class GoogleScreens(Source):
    """the owner's Google Maps screenshots (reference only)"""
    kind = 'google'; name = 'Google Maps screenshots (owner, reference only)'; licence = 'Google imagery - reference only, never redistributed'; public = False
    SKIP_OVERVIEW = '8b334c52'  # 3.2 m/px overview shot: used only where nothing better exists

    def __init__(self):
        self.reg = json.load(open(REGF)); self._im = {}
        files = os.listdir(SCREENS) if os.path.isdir(SCREENS) else []
        self.files = {}
        for k in self.reg:
            m = [f for f in files if f.startswith(k)]
            if m: self.files[k] = os.path.join(SCREENS, m[0])
        if not self.files: raise FileNotFoundError('no screenshots in ' + SCREENS)

    def images(self): return list(self.files)

    def gsd(self, k): return 1.0 / self.reg[k]['s']

    def image(self, k):
        if k not in self._im: self._im[k] = cv2.imread(self.files[k])
        return self._im[k]

    def pixel(self, k, X, Z):
        r = self.reg[k]; t = math.radians(r['th']); c, s = math.cos(t), math.sin(t)
        return r['tx'] + r['s'] * (c * X - s * Z), r['ty'] + r['s'] * (s * X + c * Z)

    def valid(self, k, mx, my):
        # map area of the 1290 x 2796 iPhone screenshot without the status bar / search box, the right-hand buttons and
        # the bottom bar (same masks as tools/sat/mosaic2.py)
        bottom = 2150 if k in ('0af09b78', '35809e3e', '4637f855', 'bc91df95') else 2230
        # the chip row ("Ask Maps", "Work", ...) under the search box reaches y ~ 470 on these screenshots
        v = (mx > 8) & (mx < 1282) & (my > 480) & (my < bottom) & ~((my < 905) & (mx > 1075)) & ~((my > 1875) & (mx > 1025))
        # Google POI pins / labels: saturated orange / blue icons (not paint: those are small), dilated
        ui = self.ui_mask(k)
        ix = np.clip(mx.astype(int), 0, ui.shape[1] - 1); iy = np.clip(my.astype(int), 0, ui.shape[0] - 1)
        return v & ~ui[iy, ix]

    def ui_mask(self, k):
        if not hasattr(self, '_ui'): self._ui = {}
        if k not in self._ui:
            im = self.image(k); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
            h, s_, v_ = hsv[..., 0], hsv[..., 1], hsv[..., 2]
            orange = (h >= 5) & (h <= 20) & (s_ > 170) & (v_ > 200)       # restaurant / shop pins
            blue = (h >= 100) & (h <= 125) & (s_ > 150) & (v_ > 180)      # location / transit pins
            m = (orange | blue).astype(np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))   # keep blobs, drop thin paint lines
            self._ui[k] = cv2.dilate(m, np.ones((61, 61), np.uint8)) > 0
        return self._ui[k]

    def describe(self, k): return f'{k} ({self.gsd(k):.2f} m/px)'


class GeoImage(Source):
    """a georeferenced image described by a JSON sidecar or a GeoTIFF with its own CRS (e.g. NAIP)"""
    kind = 'naip'; public = True

    def __init__(self, path):
        self.path = path; self._im = None; meta = {}
        if path.endswith('.json'):
            meta = json.load(open(path)); img = meta.get('image') or meta.get('file') or meta.get('path')
            self.imgf = os.path.join(os.path.dirname(path), img)
            T = meta.get('world_to_pixel') or meta.get('w2p') or meta.get('affine')
            inv = False
            if T is None and all(k in meta for k in ('x0', 'z0', 'res')):
                # {x0, z0, res}: col = (x - x0)/res - 0.5, row = (z - z0)/res - 0.5 (north-up world raster)
                r = float(meta['res']); T = [[1 / r, 0, -meta['x0'] / r - 0.5], [0, 1 / r, -meta['z0'] / r - 0.5]]
            if T is None: T = meta.get('pixel_to_world') or meta.get('p2w'); inv = True
            if T is None: raise ValueError('no transform in ' + path)
            T = np.array(T, float)
            if T.shape == (2, 3): T = np.vstack([T, [0, 0, 1]])
            self.H = np.linalg.inv(T) if inv else T; self.crs = None
            self.res = float(meta.get('res_m') or meta.get('gsd') or meta.get('resolution') or 1.0 / math.sqrt(abs(np.linalg.det(self.H[:2, :2]))))
        else:
            import rasterio
            self.imgf = path; ds = rasterio.open(path); self.crs = ds.crs; self.aff = ds.transform; self.H = None
            from pyproj import Transformer
            self.tr = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True)
            self.res = abs(ds.transform.a) if ds.crs.is_projected else abs(ds.transform.a) * 111000
        self.source_file = meta.get('source')
        self.name = meta.get('name') or ('NAIP ' + os.path.basename(self.imgf) + (f' ({meta["source_tags"]["YEAR"]})' if meta.get('source_tags', {}).get('YEAR') else ''))
        self.date = meta.get('date'); self.source = meta.get('source'); self.licence = meta.get('license') or meta.get('licence') or ('public domain (USDA NAIP)' if 'naip' in path.lower() else 'see source')

    def images(self): return [self.path]

    def gsd(self, k): return self.res

    def image(self, k):
        if self._im is None:
            im = cv2.imread(self.imgf, cv2.IMREAD_UNCHANGED)
            if im is None:
                import rasterio
                with rasterio.open(self.imgf) as ds: a = ds.read(); im = np.transpose(a[:3][::-1] if a.shape[0] >= 3 else np.repeat(a[:1], 3, 0), (1, 2, 0))
            if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
            if im.shape[2] == 4: im = im[:, :, :3]
            if im.dtype != np.uint8: im = cv2.normalize(im, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            self._im = im
        return self._im

    def pixel(self, k, X, Z):
        if self.H is not None:
            d = self.H[2, 0] * X + self.H[2, 1] * Z + self.H[2, 2]
            return (self.H[0, 0] * X + self.H[0, 1] * Z + self.H[0, 2]) / d, (self.H[1, 0] * X + self.H[1, 1] * Z + self.H[1, 2]) / d
        A = scene()['meta']['ARP']; lat0, lon0 = A['lat'], A['lon']
        lat = lat0 + (-Z) / 110990.0; lon = lon0 + X / (111320.0 * math.cos(math.radians(lat0)))
        ex, ny = self.tr.transform(lon, lat)
        col, row = ~self.aff * (ex, ny)
        return np.asarray(col) - 0.5, np.asarray(row) - 0.5

    def valid(self, k, mx, my):
        im = self.image(k); h, w = im.shape[:2]
        v = (mx >= 0) & (my >= 0) & (mx < w - 1) & (my < h - 1)
        return v

    def describe(self, k): return f'{self.name} ({self.res:.2f} m/px)'


class Mosaic(Source):
    """several GeoImages treated as one source (e.g. NAIP tiles)"""
    def __init__(self, parts, kind, name):
        self.parts = parts; self.kind = kind; self.name = name; self.public = all(p.public for p in parts); self.licence = parts[0].licence if parts else ''

    def images(self): return [(i, k) for i, p in enumerate(self.parts) for k in p.images()]
    def gsd(self, k): return self.parts[k[0]].gsd(k[1])
    def image(self, k): return self.parts[k[0]].image(k[1])
    def pixel(self, k, X, Z): return self.parts[k[0]].pixel(k[1], X, Z)
    def valid(self, k, mx, my): return self.parts[k[0]].valid(k[1], mx, my)
    def describe(self, k): return self.parts[k[0]].describe(k[1])


def find_georef(d=NAIP_DIR):
    """georeferenced images directly in d: JSON sidecars naming an image + transform (other JSON files - STAC
    listings, logs, audits - are ignored), then GeoTIFFs not already covered by a sidecar (its image or `source`)"""
    parts = []
    if os.path.isdir(d):
        used = set()
        for j in sorted(glob.glob(os.path.join(d, '*.json'))):
            try: meta = json.load(open(j))
            except Exception: continue
            if not isinstance(meta, dict) or not (meta.get('image') or meta.get('file')): continue
            try:
                g = GeoImage(j); parts.append(g); used.add(os.path.abspath(g.imgf))
                if g.source_file: used.add(os.path.abspath(os.path.join(ROOT, g.source_file))); used.add(os.path.abspath(os.path.join(d, os.path.basename(g.source_file))))
            except Exception as e:
                print('  (skipping', os.path.relpath(j, ROOT), ':', e, ')')
        for t in sorted(glob.glob(os.path.join(d, '*.tif'))):
            if os.path.abspath(t) in used: continue
            try: parts.append(GeoImage(t))
            except Exception as e: print('  (skipping', os.path.relpath(t, ROOT), ':', e, ')')
    return Mosaic(parts, 'naip', 'NAIP (' + str(len(parts)) + ' image(s))') if parts else None


def sources():
    """available backgrounds, finest first: {'google': GoogleScreens, 'naip': Mosaic}"""
    out = {}
    try: out['google'] = GoogleScreens()
    except Exception as e: print('  Google screenshots unavailable:', e)
    n = find_georef()
    if n: out['naip'] = n
    return out


def export_layers(out_dir=None):
    """world-aligned background rasters for other tools (local only - Google pixels): the whole airport at 1 m/px and
    the terminal area at 0.25 m/px, each with a world_to_pixel JSON in the GeoImage sidecar format above"""
    from common import OUT
    out_dir = out_dir or os.path.join(OUT, 'background'); os.makedirs(out_dir, exist_ok=True)
    for name, src in sources().items():
        for tag, box, res in (('airport', (-2700, -2300, 1950, 1800), 1.0), ('terminal', (-1750, -500, -250, 1150), 0.25)):
            img, valid, gsd = src.raster(*box, res)
            f = f'{name}_{tag}_{res:g}m'
            cv2.imwrite(os.path.join(out_dir, f + '.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            json.dump(dict(image=f + '.jpg', world_to_pixel=[[1 / res, 0, -box[0] / res - 0.5], [0, 1 / res, -box[1] / res - 0.5]], res_m=res, name=f'{src.name} mosaic ({tag})',
                           license=src.licence, note='north-up; pixel (col, row) centre <-> world x = x0 + (col + .5) res, z = z0 + (row + .5) res; finest registered source per pixel'),
                      open(os.path.join(out_dir, f + '.json'), 'w'), indent=1)
            print(f'  background {f}: {img.shape[1]}x{img.shape[0]} px, {valid.mean() * 100:.0f} % covered')


if __name__ == '__main__':
    export_layers()
