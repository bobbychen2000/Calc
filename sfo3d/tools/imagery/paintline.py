"""Painted-line measurement on the NAIP 2024 world raster (USDA NAIP, public domain; 0.5 m world raster made by
tools/imagery/naip_world.py from the 0.6 m UTM source, flown 2024-05-20; docs/research/imagery.md).

Yellow airfield paint (taxiway centrelines, holding-position markings, lead-in lines) is found with a colour index
  yel = min(R, G) - B          (index='min', default: 0 on grey concrete / asphalt, > 0 on yellow paint; low on the red
                                hold-sign panels and the green no-taxi paint, which the 'mean' index also lights up)
  yel = (R + G) / 2 - B        (index='mean': more sensitive on pale, worn lead-in lines; used for the stand lead-ins)
sampled bilinearly. A 6 in (0.15 m) centreline covers ~1/4 of a 0.6 m source pixel, so the index is averaged along the
line direction before the peak across it is located (sub-pixel by a parabola through the three highest samples).

API (world frame x east, z south, metres, tools/geo_frame.py):
  Y = Yellow();  Y.sample(X, Z) -> yellowness
  Y.cross_peak(p, t, half=8, avg=4, step=0.1) -> (offset along the normal n = (-t_z, t_x), strength, background)
  Y.ladder(p, u, n, ...)  -> hold-marking 4-line ladder position along u (see build_airfield_details.py)
"""
import json, math, os
import numpy as np
from scipy.ndimage import map_coordinates

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
META = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')
NPY = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy')
PNG = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.png')


class Yellow:
    def __init__(self, bounds=None, index='min'):
        m = json.load(open(META)); self.res, self.x0, self.z0 = m['res'], m['x0'], m['z0']
        if not os.path.exists(NPY):
            import cv2
            np.save(NPY, cv2.imread(PNG, cv2.IMREAD_COLOR))
        im = np.load(NPY, mmap_mode='r')
        # full-raster float index (about 390 MB as float32) - computed in row blocks
        H, W = im.shape[:2]
        self.Y = np.empty((H, W), np.float32); self.index = index
        for r0 in range(0, H, 1024):
            b = im[r0:r0 + 1024].astype(np.float32)
            if index == 'min': self.Y[r0:r0 + 1024] = np.minimum(b[..., 2], b[..., 1]) - b[..., 0]
            else: self.Y[r0:r0 + 1024] = (b[..., 2] + b[..., 1]) * 0.5 - b[..., 0]
        self.shape = (H, W)

    def _rc(self, X, Z):
        return (np.asarray(Z) - self.z0) / self.res - 0.5, (np.asarray(X) - self.x0) / self.res - 0.5

    def sample(self, X, Z, band='Y'):
        r, c = self._rc(X, Z)
        A = self.Y
        return map_coordinates(A, [np.ravel(r), np.ravel(c)], order=1, mode='nearest').reshape(np.shape(X))

    def profile(self, p, t, half=8.0, avg=4.0, step=0.1, band='Y'):
        """mean index across the line: offsets o in [-half, half] along n = right of t (x east, z south: n = (-t_z, t_x)),
        averaged over [-avg/2, avg/2] along t"""
        t = np.asarray(t, float) / np.linalg.norm(t); n = np.array([-t[1], t[0]])
        o = np.arange(-half, half + 1e-9, step); a = np.linspace(-avg / 2, avg / 2, max(2, int(avg / 0.25) + 1))
        O, A = np.meshgrid(o, a)
        X = p[0] + O * n[0] + A * t[0]; Z = p[1] + O * n[1] + A * t[1]
        return o, self.sample(X, Z, band).mean(axis=0)

    def cross_peak(self, p, t, half=8.0, avg=4.0, step=0.1, min_contrast=6.0):
        """strongest yellow ridge across the line through p with direction t. Returns (offset (m, + = right of t),
        contrast over the local background, second-best contrast) or None."""
        o, y = self.profile(p, t, half, avg, step)
        bg = np.median(y)
        k = int(np.argmax(y)); c = y[k] - bg
        if c < min_contrast: return None
        if 0 < k < len(y) - 1:
            d = y[k - 1] - 2 * y[k] + y[k + 1]
            off = o[k] + (0.5 * step * (y[k - 1] - y[k + 1]) / d if d < 0 else 0.0)
        else: off = o[k]
        # second peak at least 1.5 m away (ambiguity measure)
        mask = np.abs(o - o[k]) > 1.5
        c2 = float(y[mask].max() - bg) if mask.any() else 0.0
        return float(off), float(c), c2


BAR_DEPTH = 7 * 0.3048   # runway holding-position marking: 4 lines 12 in wide with 12 in gaps = 7 ft deep (FAA AC 150/5340-1M fig. A-5? see build_airfield_details.py)


def _box(y, n):
    if n <= 1: return y
    k = np.ones(n) / n
    return np.convolve(np.pad(y, (n // 2, n - 1 - n // 2), mode='edge'), k, mode='valid')


def along_profile(Y, pts, tans, lat_offsets, step_pts=None):
    """mean yellowness at the given lateral offsets (m, + = right of the local tangent) for each sample point"""
    P = np.asarray(pts, float); T = np.asarray(tans, float); N = np.stack([-T[:, 1], T[:, 0]], 1)
    o = np.asarray(lat_offsets, float)
    X = P[:, 0:1] + N[:, 0:1] * o[None]; Z = P[:, 1:2] + N[:, 1:2] * o[None]
    return Y.sample(X, Z).mean(axis=1)


def find_ladder(Y, P, T, S, s_lo, s_hi, half_w=7.0, step=0.1, skews=range(-60, 61, 5)):
    """Holding-position ladder along a densified centreline approach.
    P, T: points / unit tangents of the approach (arc length S, increasing away from the runway).
    The bar may be skewed against the taxiway normal (painted parallel to the runway at oblique entries): the lateral
    samples are sheared by tan(skew) for skews of -60..60 deg and the best one is kept.
    Returns dict(s, contrast, bg, second, skew_deg) for the strongest 7 ft yellow band between s_lo and s_hi, or None."""
    s = np.arange(s_lo, s_hi, step)
    if len(s) < 30: return None
    px = np.interp(s, S, P[:, 0]); pz = np.interp(s, S, P[:, 1])
    tx = np.interp(s, S, T[:, 0]); tz = np.interp(s, S, T[:, 1]); l = np.hypot(tx, tz); tx /= l; tz /= l
    lat = np.r_[np.arange(-half_w, -0.9, 0.5), np.arange(1.0, half_w + 0.01, 0.5)]
    best = None
    def one(sk):
        k_ = math.tan(math.radians(sk))
        X = px[:, None] + (-tz[:, None]) * lat[None] + tx[:, None] * (k_ * lat[None])
        Z = pz[:, None] + tx[:, None] * lat[None] + tz[:, None] * (k_ * lat[None])
        f = _box(Y.sample(X, Z).mean(axis=1), int(round(BAR_DEPTH / step)))
        bg = float(np.median(f)); k = int(np.argmax(f)); c = float(f[k] - bg)
        far = np.abs(s - s[k]) > 4.0
        return {'s': float(s[k]), 'contrast': c, 'bg': bg, 'second': float(f[far].max() - bg) if far.any() else 0.0, 'skew_deg': float(sk)}
    for sk in skews:
        r = one(sk)
        if best is None or r['contrast'] > best['contrast']: best = r
    for sk in np.arange(best['skew_deg'] - 4, best['skew_deg'] + 4.01, 1.0):   # fine scan
        r = one(float(sk))
        if r['contrast'] > best['contrast']: best = r
    return best


def refine_bar(Y, pc, bar0, span=8.0, dtheta=8.0, step_deg=0.5, sw=2.0, bgw=8.0, step=0.1):
    """Straight-bar refinement (Radon-like): for bar directions within +-dtheta of bar0 the yellowness is averaged
    along the bar over +-span and profiled across it over +-bgw; the band peak is searched within +-sw of pc and its
    contrast is taken against the darkest 10 % of the profile (some ladders sit on a light strip several metres wide).
    Returns (point on the bar centre line, unit bar direction, contrast)."""
    pc = np.asarray(pc, float); b0 = np.asarray(bar0, float) / np.linalg.norm(bar0)
    th0 = math.atan2(b0[1], b0[0]); best = None
    lat = np.arange(-span, span + 0.01, 0.5); o = np.arange(-bgw, bgw + 0.01, step); inner = np.abs(o) <= sw
    for dth in np.arange(-dtheta, dtheta + 1e-9, step_deg):
        th = th0 + math.radians(dth); b = np.array([math.cos(th), math.sin(th)]); nrm = np.array([-b[1], b[0]])
        X = pc[0] + o[:, None] * nrm[0] + lat[None] * b[0]; Z = pc[1] + o[:, None] * nrm[1] + lat[None] * b[1]
        f = _box(Y.sample(X, Z).mean(axis=1), int(round(BAR_DEPTH / step)))
        fi = np.where(inner, f, -1e9); k = int(np.argmax(fi)); c = float(f[k] - np.percentile(f, 10))
        if best is None or c > best[2]: best = (pc + nrm * o[k], b, c)
    return best
