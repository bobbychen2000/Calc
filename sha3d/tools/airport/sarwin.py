"""Sampler for the full-resolution Umbra GEC windows (refs/cache/imagery/umbra_fullres_stands/*.tif, CC BY 4.0) in the
world frame (tools/common/frame.py). Values are the GEC uint8 amplitudes. A constant registration shift (Umbra minus
OSM, metres east / north) is removed when sampling, so that the returned images are in the OSM registration."""
import glob
import os
import sys

import numpy as np
import rasterio
from pyproj import Transformer
from scipy.ndimage import map_coordinates

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402

INV = Transformer.from_pipeline(
    f'+proj=pipeline +step +inv +proj=topocentric +ellps=WGS84 +lat_0={F.ORIGIN_LAT} +lon_0={F.ORIGIN_LON} +h_0=0 '
    f'+step +inv +proj=cart +ellps=WGS84')


class SarWindows:
    def __init__(self, root, shift_en=(0.0, 0.0), sub='umbra_fullres_stands'):
        self.win = []
        for p in sorted(glob.glob(os.path.join(root, 'refs/cache/imagery', sub, '*.tif'))):
            ds = rasterio.open(p)
            self.win.append((os.path.basename(p)[:-4], ds.read(1), ~ds.transform))
        self.shift = shift_en

    def sample_xz(self, X, Z, order=1):
        """amplitude at world points (X east, Z south; arrays), NaN outside every window"""
        X = np.asarray(X, float); Z = np.asarray(Z, float)
        # a feature at OSM position p appears in Umbra at p + shift
        E = X + self.shift[0]; N = -Z + self.shift[1]
        lon, lat, _ = INV.transform(E, N, np.zeros_like(E))
        out = np.full(X.shape, np.nan)
        for _, a, inv in self.win:
            c, r = inv * (lon, lat)
            ok = (c >= 0) & (r >= 0) & (c < a.shape[1] - 1) & (r < a.shape[0] - 1) & np.isnan(out)
            if ok.any():
                out[ok] = map_coordinates(a, [r[ok] - 0.5, c[ok] - 0.5], order=order, mode='nearest')
        return out

    def grid(self, x0, z0, x1, z1, res):
        xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
        X, Z = np.meshgrid(xs, zs)
        return self.sample_xz(X, Z)

    def patch(self, cx, cz, hdg, along, across, res=0.25, back=None):
        """stand-aligned patch: rows = along the heading (row 0 = ahead of the point by `along - back`), cols = across
        (left to right as seen in the heading direction). Returns (img, U, V): U = metres ahead of (cx, cz), V = metres
        to the right."""
        f = F.hdg_vec(hdg); r = (-f[1], f[0])   # right-hand vector of heading h in (x, z): (cos h, sin h)
        back = along / 2 if back is None else back
        u = np.arange(along - back, -back, -res); v = np.arange(-across / 2, across / 2, res) + res / 2
        U, V = np.meshgrid(u, v, indexing='ij')
        X = cx + U * f[0] + V * r[0]; Z = cz + U * f[1] + V * r[1]
        return self.sample_xz(X, Z), U, V
