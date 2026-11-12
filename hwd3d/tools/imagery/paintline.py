"""Paint and pavement measurement on the committed HWD NAIP mosaics (USDA NAIP 2024 / 2022, public domain; 0.6 m,
EPSG:26910; refs/cache/naip/naip_<year>_hwd_rgb.jpg + .json, made by tools/imagery/naip_fetch.py).

Forked from sfo3d/tools/imagery/paintline.py @ a967f9b. Kept: the yellow-paint colour index yel = min(R, G) - B
(0 on grey asphalt / concrete, > 0 on yellow paint), averaging along the line direction before the peak across it is
located (sub-pixel by a parabola through the three highest samples), the second-peak ambiguity measure, the CIE Lab b*
white-paint rejection (bstar), the 7 ft holding-position band search along an approach (find_ladder: a box filter of
BAR_DEPTH over the along profile, skews of the bar against the taxiway normal). Changed: the raster is the committed
NAIP JPEG in its native UTM 10N grid (sfo3d resampled NAIP into a 0.5 m world raster PNG + .npy cache, which hwd3d does
not have); world (x, z) -> pixel goes through a cubic polynomial fitted at start-up to the exact transform
hwd_frame.world_to_utm10_np (checked at start-up: max error < 2 mm over the fitted extent, else AssertionError), so no
resampling is baked in; a white index (min(R, G, B) minus a local background) for white paint (runway side stripes,
tie-down tees); no OpenCV (not installed here); the full-raster index is computed once per year and kept in memory
(float32, 138 MB). Dropped: the mean-index variant (stand lead-ins, SFO only) and refine_bar (not needed at HWD yet).
Always reads the committed JPEG, never the local GeoTIFF, so a fresh clone reproduces every number (the JPEG error is
mean 2.1 DN, p99 9 DN; tools/imagery/naip_fetch.py measured features in both and found <= 0.04 m difference).

World frame: hwd_frame.py (x east, z south, metres, origin HWD ARP, NAD83(2011)). NAIP E/N are treated as
NAD83(2011) (as hwd_frame.py and sfo3d) [inferred].

API
  N = Naip('2024')
  N.sample(X, Z, idx='yel'|'gray'|'R'|'G'|'B')   bilinear at world points
  N.cross_peak(p, t, half, avg, step, min_contrast, idx='yel')  -> (offset right of t, contrast, second) or None
  N.bstar(p, t, off, avg)                            CIE Lab b* at a found peak
  find_ladder(N, P, T, S, s_lo, s_hi, ...)           holding-position band along an approach
"""
import json, math, os, sys
import numpy as np
from scipy.ndimage import map_coordinates

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(HWD, 'tools', 'common'))
import hwd_frame as F                                                     # noqa: E402

CACHE = os.path.join(HWD, 'refs', 'cache', 'naip')
FT = 0.3048
BAR_DEPTH = 7 * FT     # runway holding-position marking Pattern A: 2 continuous + 2 dashed yellow lines and 3 spaces, each
                       # 12 in (30 cm) wide (FAA AC 150/5340-1M Chg 1 para 3.3.4.1; 6 in allowed only without an operating
                       # ATCT and not Part 139 - HWD has an FAA ATCT) = 7 x 12 in = 7 ft deep
EXTENT = (-1300.0, 1300.0, -1100.0, 1000.0)    # world x0, x1, z0, z1 of the polynomial fit (covers the aerodrome + margin)


def _poly_terms(u, v, deg=3):
    return np.stack([u ** i * v ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)


class Naip:
    """bilinear sampling of one committed NAIP year at world points"""
    _cache = {}

    def __init__(self, year='2024'):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        g = json.load(open(os.path.join(CACHE, 'naip_%s_hwd_rgb.json' % year)))
        self.year = year; self.e0, self.n1, self.res = g['origin_E'], g['origin_N'], g['pixel_size_m']
        self.jpeg = 'refs/cache/naip/naip_%s_hwd_rgb.jpg' % year
        self.flight = sorted({t['flight_date'] for t in g['tiles']})
        im = np.asarray(Image.open(os.path.join(CACHE, 'naip_%s_hwd_rgb.jpg' % year)).convert('RGB'))
        self.rgb = im
        self.R = im[..., 0].astype(np.float32); self.G = im[..., 1].astype(np.float32); self.B = im[..., 2].astype(np.float32)
        self.yel = np.minimum(self.R, self.G) - self.B
        self.gray = (self.R + self.G + self.B) / 3.0
        self._fit()

    def _fit(self):
        """cubic polynomial world (x, z) -> fractional pixel (col, row) fitted to the exact transform; checked"""
        x0, x1, z0, z1 = EXTENT
        self._c = ((x0 + x1) / 2, (z0 + z1) / 2, (x1 - x0) / 2, (z1 - z0) / 2)
        gx, gz = np.meshgrid(np.linspace(x0, x1, 41), np.linspace(z0, z1, 41))
        c, r = self._exact(gx.ravel(), gz.ravel())
        A = _poly_terms((gx.ravel() - self._c[0]) / self._c[2], (gz.ravel() - self._c[1]) / self._c[3])
        self._pc = np.linalg.lstsq(A, c, rcond=None)[0]; self._pr = np.linalg.lstsq(A, r, rcond=None)[0]
        rng = np.random.default_rng(0)
        tx = rng.uniform(x0, x1, 2000); tz = rng.uniform(z0, z1, 2000)
        ce, re = self._exact(tx, tz); ca, ra = self.world_to_px(tx, tz)
        self.fit_err_m = float(np.max(np.hypot(ce - ca, re - ra)) * self.res)
        assert self.fit_err_m < 0.002, 'polynomial world->pixel fit error %.4f m' % self.fit_err_m

    def _exact(self, X, Z):
        E, N = F.world_to_utm10_np(X, Z)
        return (np.asarray(E) - self.e0) / self.res - 0.5, (self.n1 - np.asarray(N)) / self.res - 0.5

    def world_to_px(self, X, Z):
        X = np.asarray(X, float); Z = np.asarray(Z, float)
        A = _poly_terms((X - self._c[0]) / self._c[2], (Z - self._c[1]) / self._c[3])
        return A @ self._pc, A @ self._pr

    def band(self, idx):
        return {'yel': self.yel, 'gray': self.gray, 'R': self.R, 'G': self.G, 'B': self.B}[idx]

    def sample(self, X, Z, idx='yel'):
        X = np.asarray(X, float); Z = np.asarray(Z, float)
        c, r = self.world_to_px(X.ravel(), Z.ravel())
        return map_coordinates(self.band(idx), [r, c], order=1, mode='nearest').reshape(X.shape)

    def profile(self, p, t, half=8.0, avg=4.0, step=0.1, idx='yel'):
        """mean index across the line: offsets o in [-half, half] along n = right of t (x east, z south:
        n = (-t_z, t_x)), averaged over [-avg/2, avg/2] along t"""
        t = np.asarray(t, float) / np.linalg.norm(t); n = np.array([-t[1], t[0]])
        o = np.arange(-half, half + 1e-9, step); a = np.linspace(-avg / 2, avg / 2, max(2, int(avg / 0.25) + 1))
        O, A = np.meshgrid(o, a)
        X = p[0] + O * n[0] + A * t[0]; Z = p[1] + O * n[1] + A * t[1]
        return o, self.sample(X, Z, idx).mean(axis=0)

    def cross_peak(self, p, t, half=8.0, avg=4.0, step=0.1, min_contrast=6.0, idx='yel'):
        """strongest ridge across the line through p with direction t. Returns (offset (m, + = right of t), contrast
        over the median background, second-best contrast >= 1.5 m away) or None"""
        o, y = self.profile(p, t, half, avg, step, idx)
        bg = np.median(y)
        k = int(np.argmax(y)); c = y[k] - bg
        if c < min_contrast: return None
        if 0 < k < len(y) - 1:
            d = y[k - 1] - 2 * y[k] + y[k + 1]
            off = o[k] + (0.5 * step * (y[k - 1] - y[k + 1]) / d if d < 0 else 0.0)
        else: off = o[k]
        mask = np.abs(o - o[k]) > 1.5
        c2 = float(y[mask].max() - bg) if mask.any() else 0.0
        return float(off), float(c), c2

    def bstar(self, p, t, off, avg=3.0):
        """CIE Lab b* (D65, sRGB) of the NAIP colour at offset `off` (m, right of t) from p, averaged over avg m along t.
        sfo3d (static close-out 2026-11-04): yellow centreline peaks p5 / p10 / median b* 8.4 / 9.4 / 16.3, white runway
        side-stripe peaks median 7.7 (on its NAIP 2024 world raster) - the threshold is re-checked at HWD by the caller"""
        t = np.asarray(t, float) / np.linalg.norm(t); n = np.array([-t[1], t[0]]); q = np.asarray(p, float) + n * off
        a = np.linspace(-avg / 2, avg / 2, 7)
        X = q[0] + a * t[0]; Z = q[1] + a * t[1]
        rgb = np.stack([self.sample(X, Z, k) for k in ('R', 'G', 'B')], -1).mean(0) / 255.0
        v = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
        xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ v / np.array([0.95047, 1.0, 1.08883])
        f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
        return float(200 * (f[1] - f[2]))


def _box(y, n):
    if n <= 1: return y
    k = np.ones(n) / n
    return np.convolve(np.pad(y, (n // 2, n - 1 - n // 2), mode='edge'), k, mode='valid')


def find_ladder(N, P, T, S, s_lo, s_hi, half_w=5.0, step=0.1, skews=range(-60, 61, 5)):
    """Holding-position band along a densified centreline approach (P points, T unit tangents, S arc length).
    The bar may be skewed against the taxiway normal (painted parallel to the runway at oblique entries): lateral
    samples are sheared by tan(skew) for skews of -60..60 deg and the best one is kept (then a 1 deg fine scan).
    Returns dict(s, contrast, bg, second, skew_deg) for the strongest BAR_DEPTH yellow band in [s_lo, s_hi), or None."""
    s = np.arange(s_lo, s_hi, step)
    if len(s) < 30: return None
    px = np.interp(s, S, P[:, 0]); pz = np.interp(s, S, P[:, 1])
    tx = np.interp(s, S, T[:, 0]); tz = np.interp(s, S, T[:, 1]); l = np.hypot(tx, tz); tx = tx / l; tz = tz / l
    lat = np.r_[np.arange(-half_w, -0.9, 0.5), np.arange(1.0, half_w + 0.01, 0.5)]

    def one(sk):
        k_ = math.tan(math.radians(sk))
        X = px[:, None] + (-tz[:, None]) * lat[None] + tx[:, None] * (k_ * lat[None])
        Z = pz[:, None] + tx[:, None] * lat[None] + tz[:, None] * (k_ * lat[None])
        f = _box(N.sample(X, Z).mean(axis=1), int(round(BAR_DEPTH / step)))
        bg = float(np.median(f)); k = int(np.argmax(f)); c = float(f[k] - bg)
        far = np.abs(s - s[k]) > 4.0
        return {'s': float(s[k]), 'contrast': c, 'bg': bg, 'second': float(f[far].max() - bg) if far.any() else 0.0,
                'skew_deg': float(sk)}
    best = None
    for sk in skews:
        r = one(sk)
        if best is None or r['contrast'] > best['contrast']: best = r
    for sk in np.arange(best['skew_deg'] - 4, best['skew_deg'] + 4.01, 1.0):
        r = one(float(sk))
        if r['contrast'] > best['contrast']: best = r
    return best
