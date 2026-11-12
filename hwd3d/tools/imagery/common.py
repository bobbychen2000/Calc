"""Shared constants and coordinate helpers for the HWD orthoimagery tools (hwd3d/tools/imagery/).

Forked from sfo3d/tools/imagery/common.py @ a967f9b. Kept: the CACHE / AOI / ll_to_utm / utm_to_ll interface used by
naip_fetch.py, and the idea of a NAIP sampler that maps world (x, z) -> lat/lon -> UTM -> pixel exactly (no resampling
baked in). Changed: paths (hwd3d/refs/cache/naip for committed files, hwd3d/refs/cache/local/naip for the full-res
GeoTIFFs, which exceed the 25 MB per-file limit), AOI = HWD, the world frame and the UTM 10N projection come from
hwd3d/tools/common/hwd_frame.py (closed-form Krueger series, tested against pyproj EPSG:26910 to 1 mm), bilinear
sampling by scipy.ndimage.map_coordinates instead of cv2 (not installed here), a reader for the committed JPEG +
georeference JSON (so the tools also run when the local GeoTIFF is missing). Dropped (SFO only): the js/geo.js
legacy 'equirect-v1' frame, the SFO runway table (HWD runways are in hwd_frame.RWY_ENDS), the world-grid PNG
raster (naip_world.py is not forked).

Coordinates
-----------
* NAIP rasters: EPSG:26910 (NAD83 / UTM zone 10N), native 0.6 m grid (tile origins are multiples of 0.6 m: STAC
  proj:transform of ca_m_3712223_se_10_060_2022xxxx / 2024xxxx, e.g. E 571434.0, N 4171704.0). NAIP E/N are treated as
  NAD83(2011), as in sfo3d and hwd_frame.py.
* World frame: hwd_frame.py (x east, z south, metres, origin = HWD ARP, NAD83(2011) local tangent plane).
* Pixel (col, row) of a raster with outer corner (E0, N1) and pixel size g: pixel CENTRE of (c, r) is
  E = E0 + (c + 0.5) g, N = N1 - (r + 0.5) g (GDAL geotransform [E0, g, 0, N1, 0, -g]).

Area of interest
----------------
AOI = lat 37.6440..37.6730 N, lon -122.1420..-122.0990 E: "the aerodrome + 300 m margin", fixed by the hwd3d
orchestrator's task G2 (2026-11-12) [the margin itself was not re-derived here: no OSM aerodrome polygon is committed
yet]. Read as NAD83 (the 1.6 m WGS 84 offset, hwd_frame.py header, is irrelevant for an AOI). It is snapped outward
to the native 0.6 m grid: E 575664.0..579487.2, N 4166663.4..4169916.6 (6372 x 5422 px). The NASR runway ends lie
1.09-1.22 km inside it in E and 1.16-1.19 km inside it in N. By eye on the NAIP overview the airfield's paved/fenced
area ends 0.8-1.05 km inside the AOI edges, so the AOI is wider than "aerodrome + 300 m" [obs, rough]; it is kept as
specified (it costs only download size).
"""
import json, math, os, sys
import numpy as np

HWD = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))   # hwd3d/
sys.path.insert(0, os.path.join(HWD, 'tools', 'common'))
import hwd_frame as F                                              # noqa: E402

CACHE = os.path.join(HWD, 'refs', 'cache', 'naip')                 # committed: provenance, RGB JPEG, georef, checks
LOCAL = os.path.join(HWD, 'refs', 'cache', 'local', 'naip')        # gitignored: full-res RGB+NIR GeoTIFFs, SAS token
OUT = os.path.join(HWD, 'out', 'phase1')                           # gitignored: plots and crops for humans
for _d in (CACHE, LOCAL, OUT):
    os.makedirs(_d, exist_ok=True)

AOI = dict(lat0=37.6440, lat1=37.6730, lon0=-122.1420, lon1=-122.0990)   # task G2 (see header)
GRID = 0.6                                                               # NAIP CA 2016+ native GSD (STAC gsd 0.6)
DECI = 6                                                                 # GRID in decimetres (exact integer grid maths)

CREDIT = ('Imagery: USDA NAIP (USDA Farm Production and Conservation Business Center, Geospatial Enterprise '
          'Operations), public domain')


def ll_to_utm(lat, lon):
    """NAD83 lat/lon -> UTM 10N (E, N) (EPSG:26910), vectorised (hwd_frame closed form)."""
    return F.ll_to_utm10_np(lat, lon)


def utm_to_ll(E, N):
    return F.utm10_to_ll_np(E, N)


def aoi_grid():
    """the output grid: AOI corners -> UTM, snapped outward to multiples of 0.6 m.
    Returns dict(e0, n0, e1, n1 [outer edges, m], W, H [px], g)."""
    E, N = ll_to_utm([AOI['lat0'], AOI['lat0'], AOI['lat1'], AOI['lat1']],
                     [AOI['lon0'], AOI['lon1'], AOI['lon0'], AOI['lon1']])
    k = lambda v: v * 10 / DECI                       # metres -> grid units
    ke0, ke1 = math.floor(k(E.min())), math.ceil(k(E.max()))
    kn0, kn1 = math.floor(k(N.min())), math.ceil(k(N.max()))
    m = lambda i: i * DECI / 10                       # grid units -> metres (exact to the 0.1 mm)
    return dict(e0=m(ke0), e1=m(ke1), n0=m(kn0), n1=m(kn1), W=ke1 - ke0, H=kn1 - kn0, g=GRID)


def geotiff_path(year):
    return os.path.join(LOCAL, f'naip_{year}_hwd_utm10n.tif')


def jpeg_path(year):
    return os.path.join(CACHE, f'naip_{year}_hwd_rgb.jpg')


def georef_path(year):
    return os.path.join(CACHE, f'naip_{year}_hwd_rgb.json')


def load_rgb(year, prefer='tif'):
    """-> (img HxWx3 uint8 [or HxWx4 with NIR if from the GeoTIFF and nir=True], georef dict(e0, n1, g, W, H), source).
    Reads the full-res GeoTIFF from refs/cache/local/naip if present (lossless), else the committed JPEG (q >= 90)."""
    tif = geotiff_path(year)
    if prefer == 'tif' and os.path.exists(tif):
        import rasterio
        with rasterio.open(tif) as ds:
            t = ds.transform
            assert abs(t.a - GRID) < 1e-9 and abs(t.e + GRID) < 1e-9 and ds.crs.to_epsg() == 26910
            img = np.transpose(ds.read([1, 2, 3, 4]), (1, 2, 0)).copy()
            return img, dict(e0=t.c, n1=t.f, g=GRID, W=ds.width, H=ds.height), tif
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    G = json.load(open(georef_path(year)))
    img = np.asarray(Image.open(jpeg_path(year)).convert('RGB'))
    return img, dict(e0=G['origin_E'], n1=G['origin_N'], g=G['pixel_size_m'], W=G['width'], H=G['height']), jpeg_path(year)


class NaipSampler:
    """bilinear sampling of a NAIP mosaic at UTM (E, N) or world (x, z) points; exact per-point mapping
    world -> lat/lon (NAD83) -> UTM 10N -> pixel (no resampling baked in)."""
    def __init__(self, year, prefer='tif'):
        self.img, self.geo, self.src = load_rgb(year, prefer)
        self.gray = self.img[..., :3].astype(np.float32).mean(-1)

    def en_to_px(self, E, N):
        """UTM -> fractional (col, row) of pixel centres (col 0.0 = centre of the first pixel)."""
        g = self.geo['g']
        return (np.asarray(E, float) - self.geo['e0']) / g - 0.5, (self.geo['n1'] - np.asarray(N, float)) / g - 0.5

    def px_to_en(self, c, r):
        g = self.geo['g']
        return self.geo['e0'] + (np.asarray(c, float) + 0.5) * g, self.geo['n1'] - (np.asarray(r, float) + 0.5) * g

    def sample_en(self, E, N, band=None, order=1):
        from scipy.ndimage import map_coordinates
        c, r = self.en_to_px(E, N)
        a = self.gray if band is None else self.img[..., band].astype(np.float32)
        return map_coordinates(a, [np.ravel(r), np.ravel(c)], order=order, mode='constant', cval=0.0).reshape(np.shape(c))

    def sample_world(self, X, Z, band=None):
        lat, lon = F.world_to_ll_np(X, Z)
        E, N = ll_to_utm(lat, lon)
        return self.sample_en(E, N, band)
