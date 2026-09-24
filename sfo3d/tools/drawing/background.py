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
                   frame                                       world frame of the transform (js/geo.js FRAME_ID):
                                                               'ltp-nad83-2011' (current) is used as is, 'equirect-v1'
                                                               (legacy) through tools/geo_frame.py world_to_legacy
                                                               (exact); a sidecar without 'frame' is assumed to be in the
                                                               current frame and reported as "frame unstated"
                 A GeoTIFF with its own CRS is mapped world -> NAD83(2011) lat/lon (tools/geo_frame.py world_to_ll_np,
                 the exact inverse of js/geo.js llToWorld) -> image CRS (pyproj, from the image CRS's own geodetic datum:
                 a pure projection, no datum shift - world lat/lon ARE NAD83, like NAIP's EPSG:26910) -> pixel.
Frames: every source maps the CURRENT world frame (tools/geo_frame.FRAME_ID, which common.scene() checks against the
extracted scene and js/geo.js). Google registrations (reg.json, no 'frame' key = legacy) go through
tools/sat/common.py sim_from_reg(), which converts world -> legacy first.
Google vs NAIP: imreg.py measures each screenshot's residual translation against NAIP (ground-level gradients,
buildings masked); GoogleScreens applies it (out/draw/google_vs_naip.json, only when it was made for the current
reg.json and NAIP files; GOOGLE_NAIP=0 disables) so that Google-derived numbers share NAIP's georeference.
"""
import glob, hashlib, json, math, os, sys
import numpy as np
import cv2
from common import ROOT, OUT, scene, GF, LEGACY_FRAME, _sha


def _sat_common():
    """tools/sat/common.py (its own module name: tools/drawing/common.py is `common` here)"""
    import importlib.util
    if 'sat_common' not in sys.modules:
        spec = importlib.util.spec_from_file_location('sat_common', os.path.join(ROOT, 'tools', 'sat', 'common.py'))
        m = importlib.util.module_from_spec(spec); sys.modules['sat_common'] = m; spec.loader.exec_module(m)
    return sys.modules['sat_common']

SAT = os.path.join(ROOT, 'tools', 'sat')
SCREENS = os.environ.get('SFO_SCREENS', os.path.join(SAT, 'screens'))
REGF = os.path.join(os.environ.get('SFO_SATWORK', os.path.join(SAT, 'work')), 'reg.json')
NAIP_DIR = os.environ.get('NAIP_DIR', os.path.join(ROOT, 'refs', 'cache', 'naip'))


class Source:
    name = '?'; kind = '?'; licence = ''; public = False

    def pixel(self, img_id, X, Z):  # world -> pixel coords in image img_id
        raise NotImplementedError

    def raster(self, x0, z0, x1, z1, res, chunk=768):
        """north-up world raster (BGR, valid, gsd of the source per pixel); built in bands of `chunk` rows so a 0.25 m/px
        airport-scale raster does not need gigabytes of coordinate arrays"""
        W, H = int(round((x1 - x0) / res)), int(round((z1 - z0) / res))
        out = np.zeros((H, W, 3), np.uint8); best = np.full((H, W), np.inf, np.float32)
        for r0 in range(0, H, chunk):
            r1 = min(H, r0 + chunk); h = r1 - r0
            jj, ii = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(r0, r1, dtype=np.float64))
            X = (x0 + (jj + 0.5) * res).ravel(); Z = (z0 + (ii + 0.5) * res).ravel(); del jj, ii
            ob = out[r0:r1]; bb = best[r0:r1]
            for k in self.images():
                mx, my = self.pixel(k, X, Z); mx = np.asarray(mx, np.float32).reshape(h, W); my = np.asarray(my, np.float32).reshape(h, W)
                v = self.valid(k, mx, my); r = self.gsd(k)
                take = v & (r < bb)
                if not take.any(): continue
                im = self.image(k)
                interp = cv2.INTER_AREA if res > r * 1.5 else cv2.INTER_LINEAR
                if interp == cv2.INTER_AREA and res / r > 2:  # pre-shrink so remap does not alias (cached per image and factor)
                    f = round(r / res * 1.5, 4)
                    if not hasattr(self, '_small'): self._small = {}
                    if (k, f) not in self._small:
                        if len(self._small) > 6: self._small.clear()
                        self._small[(k, f)] = cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
                    rr = cv2.remap(self._small[(k, f)], mx * f, my * f, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                else:
                    rr = cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                ob[take] = rr[take]; bb[take] = r
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

    def __init__(self, correct=None):
        self.reg = json.load(open(REGF)); self._im = {}
        SC = _sat_common(); self.sim = {k: SC.sim_from_reg(r) for k, r in self.reg.items()}
        self.frames = sorted({v.frame for v in self.sim.values()})
        files = os.listdir(SCREENS) if os.path.isdir(SCREENS) else []
        self.files = {}
        for k in self.reg:
            m = [f for f in files if f.startswith(k)]
            if m: self.files[k] = os.path.join(SCREENS, m[0])
        if not self.files: raise FileNotFoundError('no screenshots in ' + SCREENS)
        # residual translation against NAIP (imreg.py): applied when made for these registrations and NAIP files
        self.corr = {}; self.corr_note = 'not applied (no out/draw/google_vs_naip.json)'
        want = os.environ.get('GOOGLE_NAIP', '1') != '0' if correct is None else correct
        cf = os.path.join(OUT, 'google_vs_naip.json')
        if want and os.path.exists(cf):
            C = json.load(open(cf))
            if C.get('reg_sha') != _sha(REGF) or C.get('frame') != GF.FRAME_ID: self.corr_note = 'not applied (google_vs_naip.json is for other registrations / another frame: re-run imreg.py)'
            else:
                self.corr = {k: tuple(v['shift']) for k, v in C['images'].items() if v.get('use')}
                self.corr_note = f'applied: per-screenshot translation to NAIP for {len(self.corr)} of {len(self.files)} screenshots (imreg.py)'
        elif not want: self.corr_note = 'disabled (GOOGLE_NAIP=0)'
        self.name = 'Google Maps screenshots (owner, reference only' + (', re-registered to NAIP)' if self.corr else ')')

    def images(self): return list(self.files)

    def gsd(self, k): return 1.0 / self.reg[k]['s']

    def image(self, k):
        if k not in self._im: self._im[k] = cv2.imread(self.files[k])
        return self._im[k]

    def _legacy(self, X, Z):
        """exact world -> legacy (geo_frame.world_to_legacy_np), memoised for the last coordinate arrays: profiles() and
        raster() map the same points into all 19 screenshots"""
        key = (X.__array_interface__['data'][0], X.size, Z.__array_interface__['data'][0], float(X.flat[0]) if X.size else 0.0, float(Z.flat[-1]) if Z.size else 0.0)
        if getattr(self, '_lkey', None) != key:
            self._lkey = key; self._lval = GF.world_to_legacy_np(X, Z)
        return self._lval

    def pixel(self, k, X, Z):
        # tools/sat/common.py Sim, frame-aware: legacy registrations (all of reg.json) map world -> equirect-v1 (exact)
        # first; + the NAIP residual shift c (a ground feature at world p shows at p + c in the uncorrected mapping),
        # applied in the legacy plane through the map's Jacobian (d legacy / d world = diag(LEGACY_MLON / MLON,
        # LEGACY_MLAT / MLAT) to 3e-4, i.e. < 2 mm for the <= 5 m shifts)
        X = np.asarray(X, float); Z = np.asarray(Z, float); c = self.corr.get(k, (0.0, 0.0)); sim = self.sim[k]
        if sim.frame == LEGACY_FRAME:
            LX, LZ = self._legacy(X, Z)
            P = np.stack([LX + c[0] * GF.LEGACY_MLON / GF.MLON, LZ + c[1] * GF.LEGACY_MLAT / GF.MLAT], -1)
        else: P = np.stack([X + c[0], Z + c[1]], -1)
        A, t = sim.M(); q = P @ A.T + t
        return q[..., 0], q[..., 1]

    def uncorrected(self):
        g = GoogleScreens.__new__(GoogleScreens); g.__dict__.update(self.__dict__); g.corr = {}; g._im = self._im
        g.name = 'Google Maps screenshots (owner, reference only)'; g.corr_note = 'not applied'; return g

    def provenance(self):
        return dict(kind=self.kind, name=self.name, frame=GF.FRAME_ID, registrations=os.path.relpath(REGF, ROOT), reg_sha=_sha(REGF), reg_frames=self.frames,
                    images=len(self.files), naip_correction=self.corr_note, public=False)

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
        self.path = path; self._im = None; meta = {}; self.frame_note = ''
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
            fr = meta.get('frame')
            if fr is None: self.frame = GF.FRAME_ID; self.frame_note = 'frame unstated (assumed ' + GF.FRAME_ID + ')'; print('  WARNING', os.path.relpath(path, ROOT), 'has no "frame" key: assumed', GF.FRAME_ID)
            elif fr in (GF.FRAME_ID, LEGACY_FRAME): self.frame = fr; self.frame_note = fr + (' (converted exactly: geo_frame.world_to_legacy)' if fr == LEGACY_FRAME else '')
            else: raise ValueError(f'unknown world frame {fr!r} (known: {GF.FRAME_ID}, {LEGACY_FRAME})')
        else:
            import rasterio
            from pyproj import CRS, Transformer
            self.imgf = path; ds = rasterio.open(path); self.crs = ds.crs; self.aff = ds.transform; self.H = None
            # world lat/lon are NAD83(2011) (geo_frame); project with the image CRS's own geodetic datum (NAIP:
            # EPSG:26910 = NAD83 / UTM 10N): a pure projection. Never EPSG:4326 (that would claim WGS 84 input).
            C = CRS.from_user_input(ds.crs.to_wkt()); self.tr = Transformer.from_crs(C.geodetic_crs, C, always_xy=True)
            self.res = abs(ds.transform.a) if ds.crs.is_projected else abs(ds.transform.a) * 111000
            self.frame = 'crs:' + (C.to_string() or '?'); self.frame_note = f'GeoTIFF {C.name}: world -> NAD83(2011) lat/lon (geo_frame.world_to_ll) -> {C.name} (datum {C.geodetic_crs.name}, no datum shift)'
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
        X = np.asarray(X, float); Z = np.asarray(Z, float)
        if self.H is not None:
            if self.frame == LEGACY_FRAME: X, Z = GF.world_to_legacy_np(X, Z)
            d = self.H[2, 0] * X + self.H[2, 1] * Z + self.H[2, 2]
            return (self.H[0, 0] * X + self.H[0, 1] * Z + self.H[0, 2]) / d, (self.H[1, 0] * X + self.H[1, 1] * Z + self.H[1, 2]) / d
        lat, lon = GF.world_to_ll_np(X, Z)
        ex, ny = self.tr.transform(lon, lat)
        col, row = ~self.aff * (ex, ny)
        return np.asarray(col) - 0.5, np.asarray(row) - 0.5

    def provenance(self):
        f = self.imgf
        return dict(kind='naip', name=self.name, file=os.path.relpath(f, ROOT), sha=_sha(f), bytes=os.path.getsize(f) if os.path.exists(f) else None,
                    sidecar=os.path.relpath(self.path, ROOT) if self.path.endswith('.json') else None, frame=self.frame, frame_note=self.frame_note, res=self.res, public=self.public)

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
    def provenance(self): return dict(kind=self.kind, name=self.name, parts=[p.provenance() for p in self.parts], public=self.public)


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
    """available backgrounds, primary first: {'naip': Mosaic (public, independent georeference), 'google': GoogleScreens}"""
    out = {}
    n = find_georef()
    if n: out['naip'] = n
    try: out['google'] = GoogleScreens()
    except Exception as e: print('  Google screenshots unavailable:', e)
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
            json.dump(dict(image=f + '.jpg', frame=GF.FRAME_ID, world_to_pixel=[[1 / res, 0, -box[0] / res - 0.5], [0, 1 / res, -box[1] / res - 0.5]], res_m=res, name=f'{src.name} mosaic ({tag})',
                           license=src.licence, note='north-up; pixel (col, row) centre <-> world x = x0 + (col + .5) res, z = z0 + (row + .5) res; finest registered source per pixel'),
                      open(os.path.join(out_dir, f + '.json'), 'w'), indent=1)
            print(f'  background {f}: {img.shape[1]}x{img.shape[0]} px, {valid.mean() * 100:.0f} % covered')


if __name__ == '__main__':
    export_layers()
