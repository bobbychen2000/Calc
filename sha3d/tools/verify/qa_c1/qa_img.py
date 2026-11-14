"""QA imagery samplers (independent of tools/airport): Sentinel-2 crops (UTM 51N) and Umbra GEC (rotated affine)."""
import sys, json, numpy as np, rasterio
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import frame as F
from pyproj import Transformer
from scipy.ndimage import map_coordinates
R = '/home/user/Calc/sha3d/refs/cache'
TO_UTM = Transformer.from_crs('EPSG:4326', 'EPSG:32651', always_xy=True)
INV = Transformer.from_pipeline(f'+proj=pipeline +step +inv +proj=topocentric +ellps=WGS84 +lat_0={F.ORIGIN_LAT} +lon_0={F.ORIGIN_LON} +h_0=0 +step +inv +proj=cart +ellps=WGS84')
def xz_to_ll(X, Z):
    X = np.asarray(X, float); Z = np.asarray(Z, float)
    lon, lat, _ = INV.transform(X, -Z, np.zeros_like(X)); return lon, lat
class Raster:
    def __init__(self, path, band=1, shift_en=(0, 0)):
        self.ds = rasterio.open(path); self.a = self.ds.read(band).astype(float); self.inv = ~self.ds.transform
        self.utm = self.ds.crs.to_epsg() == 32651; self.shift = shift_en
    def sample(self, X, Z, order=1):
        X = np.asarray(X, float); Z = np.asarray(Z, float)
        lon, lat = xz_to_ll(X + self.shift[0], Z - self.shift[1])
        if self.utm:
            e, n = TO_UTM.transform(lon, lat); c, r = self.inv * (e, n)
        else:
            c, r = self.inv * (lon, lat)
        c = np.asarray(c); r = np.asarray(r)
        out = map_coordinates(self.a, [r - 0.5, c - 0.5], order=order, mode='constant', cval=np.nan)
        bad = (c < 0) | (r < 0) | (c > self.a.shape[1]) | (r > self.a.shape[0])
        out = np.where(bad, np.nan, out); return out
S2 = {'S2B': 'S2B_51RUQ_20261014_0_L2A', 'S2C': 'S2C_51RUQ_20260221_0_L2A'}
def s2(scene, band, shift_en=(0, 0)):
    return Raster(f'{R}/s2/{S2[scene]}/{band}.tif', shift_en=shift_en)
def umbra(shift_en=(0, 0)):
    return Raster(f'{R}/imagery/umbra_opendata/umbra_gec_ovr4.tif', shift_en=shift_en)
def tci(scene):
    ds = rasterio.open(f'{R}/s2/{S2[scene]}/TCI.tif'); return ds
