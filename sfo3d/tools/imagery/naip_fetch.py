"""Download the USDA NAIP orthoimagery covering SFO from Microsoft Planetary Computer and mosaic a GeoTIFF crop.

Source:  STAC API https://planetarycomputer.microsoft.com/api/stac/v1 , collection 'naip'
         (provider/licensor: USDA Farm Service Agency; licence: see docs/research/imagery.md section 1).
Token:   https://planetarycomputer.microsoft.com/api/sas/v1/token/naip  (short-lived SAS token, appended to blob URLs)
Output:  refs/cache/naip/naip_<year>_sfo_utm10n.tif  (RGB+NIR, uint8, EPSG:26910 = NAD83 / UTM 10N, native 0.6 m grid)
         refs/cache/naip/items_<year>/*.json          (the STAC items used, for provenance)
Only the window covering the AOI (+ margin) is read from each Cloud-Optimized GeoTIFF (HTTP range requests).

--source usda : the newest year (NAIP 2024 for CA, flown 2024-05-20) is not on Planetary Computer (its collection ends
         2022-12-31); it is read from USDA FPAC-BC-GEO's own image service
         https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer  (exportImage, one tile at a
         time via a LockRaster mosaic rule, EPSG:26910, nearest neighbour, on the tiles' native 0.6 m grid - verified:
         pixel boundaries fall on multiples of 0.6 m, same grid as 2022; 2022-vs-2024 image correlation 0.2-0.6 m).
Overlap between quarter-quad tiles (NAIP DOQQs carry a ~300 m buffer) is resolved by taking each output pixel from
the tile whose footprint centre is nearest (all tiles share one 0.6 m grid, verified from proj:transform).

usage: python3 tools/imagery/naip_fetch.py [--source pc|usda] [--year 2022] [--margin 150]
"""
import argparse, json, os, sys, time, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE, AOI, ll_to_utm

STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1/search'
TOKEN = 'https://planetarycomputer.microsoft.com/api/sas/v1/token/naip'
USDA = 'https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer'


def http_json(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=60))


def token():
    p = os.path.join(CACHE, 'token.json')
    try:
        t = json.load(open(p))
        exp = time.mktime(time.strptime(t['msft:expiry'], '%Y-%m-%dT%H:%M:%SZ')) - time.timezone
        if exp - time.time() > 600: return t['token']
    except Exception: pass
    t = http_json(TOKEN); json.dump(t, open(p, 'w')); return t['token']


def usda_items(year):
    """catalog query of the USDA image service -> pseudo-STAC items {id, oid, proj:bbox}."""
    import urllib.parse
    q = dict(where=f"year_ts={int(year)} AND ST='CA'", geometry=f"{AOI['lon0']},{AOI['lat0']},{AOI['lon1']},{AOI['lat1']}",
             geometryType='esriGeometryEnvelope', inSR=4326, spatialRel='esriSpatialRelIntersects', outFields='*',
             returnGeometry='true', outSR=26910, f='json')
    d = http_json(USDA + '/query?' + urllib.parse.urlencode(q))
    out = []
    for f in d['features']:
        r = f['geometry']['rings'][0]; xs = [p[0] for p in r]; ys = [p[1] for p in r]
        out.append({'id': f['attributes']['Name'], 'oid': f['attributes']['OBJECTID'], 'attributes': f['attributes'],
                    'properties': {'naip:year': str(year), 'proj:bbox': [min(xs), min(ys), max(xs), max(ys)]}})
    return out


def usda_read(oid, e0, n0, e1, n1, g=0.6, chunk=2000):   # >2000 px per side returns HTTP 500 (tested)
    """exportImage of one locked raster over [e0,e1]x[n0,n1] (EPSG:26910) -> (4, H, W) uint8, in chunks."""
    import urllib.parse, rasterio
    W, H = int(round((e1 - e0) / g)), int(round((n1 - n0) / g))
    arr = np.zeros((4, H, W), np.uint8)
    mr = json.dumps({'mosaicMethod': 'esriMosaicLockRaster', 'lockRasterIds': [oid]})
    for r0 in range(0, H, chunk):
        for c0 in range(0, W, chunk):
            h, w = min(chunk, H - r0), min(chunk, W - c0)
            bb = (e0 + c0 * g, n1 - (r0 + h) * g, e0 + (c0 + w) * g, n1 - r0 * g)
            p = dict(bbox=','.join(f'{v:.3f}' for v in bb), bboxSR=26910, imageSR=26910, size=f'{w},{h}', format='tiff',
                     pixelType='U8', interpolation='RSP_NearestNeighbor', compression='LZ77', mosaicRule=mr, f='image')
            tmp = os.path.join(CACHE, '_chunk.tif')
            for attempt in range(4):
                try:
                    open(tmp, 'wb').write(urllib.request.urlopen(USDA + '/exportImage?' + urllib.parse.urlencode(p), timeout=300).read()); break
                except Exception as ex:
                    print('    retry', attempt, ex); time.sleep(5)
            with rasterio.open(tmp) as ds:
                assert abs(ds.transform.c - bb[0]) < 1e-3 and abs(ds.transform.f - bb[3]) < 1e-3, (ds.transform, bb)
                arr[:, r0:r0 + h, c0:c0 + w] = ds.read()[:4]
    return arr


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--year', default=None); ap.add_argument('--margin', type=float, default=150)
    ap.add_argument('--source', default='pc', choices=['pc', 'usda'])
    a = ap.parse_args()
    bbox = [AOI['lon0'], AOI['lat0'], AOI['lon1'], AOI['lat1']]
    if a.source == 'pc':
        res = http_json(STAC, {'collections': ['naip'], 'bbox': bbox, 'limit': 100})
        json.dump(res, open(os.path.join(CACHE, 'stac_search.json'), 'w'), indent=1)
        feats = res['features']
        years = sorted({f['properties']['naip:year'] for f in feats})
        year = a.year or years[-1]
        items = [f for f in feats if f['properties']['naip:year'] == year]
    else:
        year = a.year or '2024'; years = [year]
        items = usda_items(year)
    print(a.source, 'NAIP years available over AOI:', years, '-> using', year, [f['id'] for f in items])
    idir = os.path.join(CACHE, f'items_{year}'); os.makedirs(idir, exist_ok=True)
    for f in items: json.dump(f, open(os.path.join(idir, f['id'] + '.json'), 'w'), indent=1)

    import rasterio
    from rasterio.windows import from_bounds
    # AOI in UTM (NAD83 lat/lon; the WGS84-vs-NAD83 difference, ~1 m, is far inside the margin)
    E, N = ll_to_utm([AOI['lat0'], AOI['lat0'], AOI['lat1'], AOI['lat1']], [AOI['lon0'], AOI['lon1'], AOI['lon0'], AOI['lon1']])
    g = 0.6
    e0 = np.floor((E.min() - a.margin) / g) * g; e1 = np.ceil((E.max() + a.margin) / g) * g
    n0 = np.floor((N.min() - a.margin) / g) * g; n1 = np.ceil((N.max() + a.margin) / g) * g
    W, H = int(round((e1 - e0) / g)), int(round((n1 - n0) / g))
    print(f'output grid {W} x {H} px, E {e0:.1f}..{e1:.1f}, N {n0:.1f}..{n1:.1f}')
    out = np.zeros((4, H, W), np.uint8)
    best = np.full((H, W), np.inf, np.float32)
    pe, pn = e0 + (np.arange(W) + 0.5) * g, n1 - (np.arange(H) + 0.5) * g   # pixel-centre coordinates (1-D)
    tok = token() if a.source == 'pc' else None
    for f in items:
        pb = f['properties']['proj:bbox']; ce, cn = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
        t0 = time.time()
        if a.source == 'usda':
            ie0, ie1 = max(e0, np.floor(pb[0] / g) * g), min(e1, np.ceil(pb[2] / g) * g)
            in0, in1 = max(n0, np.floor(pb[1] / g) * g), min(n1, np.ceil(pb[3] / g) * g)
            if ie0 >= ie1 or in0 >= in1: continue
            arr = usda_read(f['oid'], ie0, in0, ie1, in1, g)
            c0 = int(round((ie0 - e0) / g)); r0 = int(round((n1 - in1) / g)); h, w = arr.shape[1:]
            d = np.hypot(pe[None, c0:c0 + w] - ce, pn[r0:r0 + h, None] - cn).astype(np.float32)
            valid = arr[:3].max(0) > 0
            take = valid & (d < best[r0:r0 + h, c0:c0 + w])
            for b in range(4): out[b, r0:r0 + h, c0:c0 + w][take] = arr[b][take]
            best[r0:r0 + h, c0:c0 + w][take] = d[take]
            print(f"  {f['id']}: {w}x{h} px exported in {time.time() - t0:.0f} s")
            continue
        url = '/vsicurl/' + f['assets']['image']['href'] + '?' + tok
        with rasterio.Env(CURL_CA_BUNDLE='/root/.ccr/ca-bundle.crt', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                          GDAL_HTTP_MULTIRANGE='YES', GDAL_HTTP_MERGE_CONSECUTIVE_RANGES='YES', VSI_CACHE='TRUE'):
            with rasterio.open(url) as ds:
                assert abs(ds.transform.a - g) < 1e-9 and ds.crs.to_epsg() == 26910
                # intersection of the tile with the output grid
                ie0, ie1 = max(e0, ds.bounds.left), min(e1, ds.bounds.right)
                in0, in1 = max(n0, ds.bounds.bottom), min(n1, ds.bounds.top)
                if ie0 >= ie1 or in0 >= in1: continue
                win = from_bounds(ie0, in0, ie1, in1, ds.transform).round_offsets().round_lengths()
                arr = ds.read(window=win)
                c0 = int(round((ie0 - e0) / g)); r0 = int(round((n1 - in1) / g))
                h, w = arr.shape[1:]
                d = np.hypot(pe[None, c0:c0 + w] - ce, pn[r0:r0 + h, None] - cn).astype(np.float32)
                valid = arr[:3].max(0) > 0
                take = valid & (d < best[r0:r0 + h, c0:c0 + w])
                for b in range(4): out[b, r0:r0 + h, c0:c0 + w][take] = arr[b][take]
                best[r0:r0 + h, c0:c0 + w][take] = d[take]
                print(f"  {f['id']}: window {w}x{h} read in {time.time() - t0:.0f} s")
    from rasterio.transform import from_origin
    path = os.path.join(CACHE, f'naip_{year}_sfo_utm10n.tif')
    prof = dict(driver='GTiff', width=W, height=H, count=4, dtype='uint8', crs='EPSG:26910',
                transform=from_origin(e0, n1, g, g), tiled=True, blockxsize=512, blockysize=512, compress='deflate',
                predictor=2, photometric='RGB', interleave='pixel')
    with rasterio.open(path, 'w', **prof) as dst:
        dst.write(out)
        dst.update_tags(SOURCE='USDA FSA NAIP via Microsoft Planetary Computer (collection naip)' if a.source == 'pc'
                        else 'USDA FPAC-BC-GEO NAIP image service ' + USDA,
                        ITEMS=','.join(f['id'] for f in items), YEAR=year,
                        LICENCE='USDA NAIP - public domain (see docs/research/imagery.md)')
        dst.set_band_description(4, 'NIR')
        dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
    print('wrote', path, f'{os.path.getsize(path) / 1e6:.1f} MB; empty px: {(out[:3].max(0) == 0).sum()}')


if __name__ == '__main__':
    main()
