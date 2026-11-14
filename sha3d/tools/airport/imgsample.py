"""Shared imagery samplers for sha3d airport tools (Sentinel-2 L2A crops in UTM 51N, Umbra GEC overview in rotated
EPSG:4326). All positions are WGS 84 lon/lat; offsets follow docs/phase0/geo.md (OSM minus S2, metres E/N)."""
import os

import numpy as np
import rasterio
from pyproj import Transformer
from scipy.ndimage import map_coordinates

# OSM minus S2 (geo.md s.4, mirror-symmetry fit over 54 / 43 straight runs)
S2_OFFSETS = {'S2B_51RUQ_20261014_0_L2A': (-3.09, -1.00), 'S2C_51RUQ_20260221_0_L2A': (-1.61, -0.14)}


class S2:
    def __init__(self, scene_dir, bands=('B02', 'B03', 'B04', 'B08')):
        self.name = os.path.basename(scene_dir.rstrip('/'))
        self.ds = {b: rasterio.open(os.path.join(scene_dir, b + '.tif')) for b in bands}
        self.T = self.ds[bands[0]].transform
        self.crs = self.ds[bands[0]].crs
        self.img = {b: d.read(1).astype(float) for b, d in self.ds.items()}
        self.tr = Transformer.from_crs('EPSG:4326', self.crs, always_xy=True)
        self.inv = Transformer.from_crs(self.crs, 'EPSG:4326', always_xy=True)
        self.off = S2_OFFSETS.get(self.name, (0.0, 0.0))

    def en(self, lon, lat, osm_frame=True):
        """UTM E/N of a WGS 84 point; osm_frame: the point is in OSM's registration, so move it into the S2 image
        registration (S2 = OSM - offset)."""
        E, N = self.tr.transform(np.asarray(lon), np.asarray(lat))
        if osm_frame:
            E = E - self.off[0]; N = N - self.off[1]
        return E, N

    def sample_en(self, band, E, N, order=1):
        col = (np.asarray(E) - self.T.c) / self.T.a - 0.5
        row = (np.asarray(N) - self.T.f) / self.T.e - 0.5
        return map_coordinates(self.img[band], [row, col], order=order, mode='nearest')

    def ndvi_en(self, E, N):
        r = self.sample_en('B04', E, N); n = self.sample_en('B08', E, N)
        return (n - r) / np.maximum(n + r, 1.0)


class Umbra:
    def __init__(self, path):
        self.ds = rasterio.open(path)
        self.img = self.ds.read(1).astype(float)
        self.inv = ~self.ds.transform
        self.fwd = self.ds.transform

    def sample(self, lon, lat, order=1):
        lon = np.asarray(lon, float); lat = np.asarray(lat, float)
        col, row = self.inv * (lon, lat)
        return map_coordinates(self.img, [np.asarray(row) - 0.5, np.asarray(col) - 0.5], order=order, mode='constant',
                               cval=np.nan)
