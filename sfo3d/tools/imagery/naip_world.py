"""Resample the NAIP GeoTIFF crop (EPSG:26910, NAD83 / UTM 10N) onto the app's world grid.

World grid = js/geo.js llToWorld: x = east, z = south (m from the ARP), spherical equirectangular
(M_PER_DEG_LAT 110990, M_PER_DEG_LON 111320*cos(lat0)).  Each output pixel centre (x, z) is mapped exactly:
    (x, z) -> (lat, lon) by the inverse geo.js formula -> UTM 10N (pyproj, NAD83) -> source pixel -> bilinear sample,
so the PNG lines up with everything else the app places through llToWorld (FAA runway ends, SFO Museum outlines,
ADS-B).  Datum: world lat/lon is taken as NAD83 (no datum shift); pass --wgs84 to treat world lat/lon as
WGS 84 (ITRF2020 @ epoch) instead, which moves the imagery 1.58 m (see projection_audit.py).

Outputs (refs/cache/naip/, gitignored - USDA NAIP is public domain, but it stays with the other downloads):
    naip_<year>_world_<res>m.png   RGB, row 0 = north edge (z = z0), col 0 = west edge (x = x0)
    naip_<year>_world_<res>m.json  world->pixel transform + provenance
    naip_<year>_world_preview.jpg  4 m/px preview
Transform (pixel-centre convention):  col = (x - x0)/res - 0.5 ,  row = (z - z0)/res - 0.5
                                      (texture UV: u = (x - x0)/(W*res), v = (z - z0)/(H*res))

usage: python3 tools/imagery/naip_world.py [--year 2024] [--res 0.5] [--wgs84] [--tiles 2048] [--proj geojs|ltp]
"""
import argparse, json, math, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', default='2024'); ap.add_argument('--res', type=float, default=0.5)
    ap.add_argument('--wgs84', action='store_true'); ap.add_argument('--tiles', type=int, default=0)
    ap.add_argument('--proj', default='geojs', choices=['geojs', 'ltp'])   # ltp = the recommended geo.js fix
    a = ap.parse_args()
    import rasterio, cv2, pyproj
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    src = os.path.join(CACHE, f'naip_{a.year}_sfo_utm10n.tif')
    with rasterio.open(src) as ds:
        img = np.transpose(ds.read([1, 2, 3]), (1, 2, 0)).copy(); T = ds.transform; tags = ds.tags()
    # world extent of the AOI (outer pixel edges snapped to the resolution)
    xs, zs = world_geojs([AOI['lat0'], AOI['lat1']], [AOI['lon0'], AOI['lon1']]) if a.proj == 'geojs' else \
        world_ltp([AOI['lat0'], AOI['lat1']], [AOI['lon0'], AOI['lon1']])[:2]
    res = a.res
    x0 = math.floor(min(xs) / res) * res; x1 = math.ceil(max(xs) / res) * res
    z0 = math.floor(min(zs) / res) * res; z1 = math.ceil(max(zs) / res) * res
    W, H = int(round((x1 - x0) / res)), int(round((z1 - z0) / res))
    print(f'world grid {W} x {H} px at {res} m: x {x0}..{x1}, z {z0}..{z1}')
    if a.wgs84:   # world lat/lon is WGS84 ~ ITRF2020 @ 2026.73 -> NAD83(2011) (EPSG time-dependent Helmert) -> UTM
        T83 = pyproj.Transformer.from_crs('EPSG:9989', 'EPSG:6319', always_xy=True)
    Tutm = pyproj.Transformer.from_crs('EPSG:4269', 'EPSG:26910', always_xy=True)
    inv = ~T
    out = np.zeros((H, W, 3), np.uint8)
    xc = x0 + (np.arange(W) + 0.5) * res
    t0 = time.time(); step = 512
    for r0 in range(0, H, step):
        h = min(step, H - r0)
        zc = z0 + (np.arange(r0, r0 + h) + 0.5) * res
        X, Z = np.meshgrid(xc, zc)
        lat, lon = ll_geojs(X, Z) if a.proj == 'geojs' else ll_ltp(X, Z)
        if a.wgs84:
            lon, lat, _, _ = T83.transform(lon, lat, np.zeros_like(lat), np.full_like(lat, 2026.73))
        E, N = Tutm.transform(lon, lat)
        c, r = inv * (E, N)                         # pixel-edge coordinates (0,0 = outer corner)
        mx = (np.asarray(c) - 0.5).astype(np.float32); my = (np.asarray(r) - 0.5).astype(np.float32)
        out[r0:r0 + h] = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    print(f'resampled in {time.time() - t0:.0f} s')
    tag = f'naip_{a.year}_world_{res:g}m' + ('_wgs84' if a.wgs84 else '') + ('_ltp' if a.proj == 'ltp' else '')
    png = os.path.join(CACHE, tag + '.png')
    Image.fromarray(out).save(png, optimize=False, compress_level=6)
    Image.fromarray(out).resize((W // int(round(4 / res)), H // int(round(4 / res))), Image.LANCZOS).save(
        os.path.join(CACHE, f'naip_{a.year}_world_preview.jpg'), quality=88)
    meta = dict(
        image=os.path.basename(png), width=W, height=H, res=res, x0=x0, z0=z0, x1=x1, z1=z1,
        convention='col = (x - x0)/res - 0.5, row = (z - z0)/res - 0.5 (pixel centres); x east, z south, metres from ARP',
        world_projection='js/geo.js llToWorld (ARP 37.6188056,-122.3754167; M_PER_DEG_LAT 110990; M_PER_DEG_LON 111320*cos(lat0))' if a.proj == 'geojs'
        else 'local tangent plane (ENU, GRS80) at ARP 37.6188056,-122.3754167 (recommended geo.js fix)',
        world_datum='WGS84 (ITRF2020 @2026.73)' if a.wgs84 else 'NAD83 (world lat/lon taken as NAD83, i.e. same as the FAA runway-end coordinates)',
        source=src.replace(ROOT + os.sep, ''), source_crs='EPSG:26910', source_res=0.6, source_tags=tags,
        resampling='bilinear (cv2.remap), exact per-pixel mapping via pyproj',
        licence='USDA NAIP: public domain (U.S. Government work); credit requested: "USDA Farm Production and Conservation - Business Center, Geospatial Enterprise Operations" (see docs/research/imagery.md)')
    if a.tiles:
        tdir = os.path.join(CACHE, tag + '_tiles'); os.makedirs(tdir, exist_ok=True)
        meta['tiles'] = dict(size=a.tiles, dir=os.path.basename(tdir), pattern='t_{row}_{col}.jpg')
        for tr_ in range(0, H, a.tiles):
            for tc in range(0, W, a.tiles):
                Image.fromarray(out[tr_:tr_ + a.tiles, tc:tc + a.tiles]).save(os.path.join(tdir, f't_{tr_ // a.tiles}_{tc // a.tiles}.jpg'), quality=90)
    json.dump(meta, open(os.path.join(CACHE, tag + '.json'), 'w'), indent=1)
    print('wrote', png, f'{os.path.getsize(png) / 1e6:.0f} MB')


if __name__ == '__main__':
    main()
