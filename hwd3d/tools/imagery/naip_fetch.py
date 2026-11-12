"""Download USDA NAIP orthoimagery over Hayward Executive (HWD) and mosaic it on the native 0.6 m UTM 10N grid.

Forked from sfo3d/tools/imagery/naip_fetch.py @ a967f9b. Kept: both read paths (--source pc: Microsoft Planetary
Computer STAC + COG window reads with a SAS token; --source usda: USDA FPAC-BC-GEO image service exportImage of one
locked raster at a time, nearest neighbour, <= 2000 px chunks), the grid-alignment asserts and the overlap rule
(each output pixel from the tile whose footprint centre is nearest). Changed: AOI = HWD (common.AOI, already includes
the 300 m margin, so --margin defaults to 0), output paths (full-res GeoTIFF -> refs/cache/local/naip/, gitignored,
because it exceeds the 25 MB per-file limit; committed instead: an RGB JPEG q 92 4:4:4 at full resolution + exact
georeference JSON + world file, a tile-index PNG, the STAC / catalog items, SOURCES.json and MANIFEST.json with the
sha256 of the full-res files and of their raw pixels), the SAS token is cached in the local (gitignored) dir, the
download chunks go to their own new directory (untrusted downloads), and a bug fix: Planetary Computer's
'naip:year' is a string for 2024 items and an int for 2022 items, and `--year 2022` (a string) matched nothing in
sfo3d (sfo3d/refs/cache/naip_fetch_pc.log: "-> using 2022 []"); years are compared as strings here.

Sources (both public domain; USDA FPAC-BC GEO asks to be credited, see SOURCES.json and
sfo3d/docs/research/imagery.md section 1 for the quoted licence statements):
  pc   : STAC https://planetarycomputer.microsoft.com/api/stac/v1/search , collection 'naip';
         SAS token https://planetarycomputer.microsoft.com/api/sas/v1/token/naip
  usda : https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer (query + exportImage)
Task G2 (2026-11-12): NAIP 2024 via --source usda, NAIP 2022 via --source pc.

Outputs (year Y):
  refs/cache/local/naip/naip_Y_hwd_utm10n.tif   RGB+NIR uint8, EPSG:26910, 0.6 m, deflate (NOT committed)
  refs/cache/naip/naip_Y_hwd_rgb.jpg            RGB, same grid, JPEG quality 92, no chroma subsampling (committed)
  refs/cache/naip/naip_Y_hwd_rgb.json / .jgw    exact georeference (UTM origin = outer NW corner, pixel size)
  refs/cache/naip/naip_Y_hwd_tileidx.png        per-pixel source tile (value = 1 + index into georef 'tiles')
  refs/cache/naip/items_Y/*.json                STAC items / USDA catalog records used
  refs/cache/naip/SOURCES.json, MANIFEST.json   provenance; sha256 of every file written

usage: python3 -I hwd3d/tools/imagery/naip_fetch.py --source usda --year 2024
       python3 -I hwd3d/tools/imagery/naip_fetch.py --source pc --year 2022
"""
import argparse, datetime, hashlib, json, os, shutil, sys, time, urllib.parse, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE, LOCAL, AOI, GRID, CREDIT, aoi_grid, geotiff_path, jpeg_path, georef_path  # noqa: E402

STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1/search'
TOKEN = 'https://planetarycomputer.microsoft.com/api/sas/v1/token/naip'
USDA = 'https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer'
JPEG_Q = 92            # task G2: JPEG quality >= 90; 92 keeps the mean error ~2 DN (measured, see georef 'jpeg') at 13-16 MB
MAX_COMMIT_MB = 25.0   # owner's rule: each committed file <= 25 MB


def http_json(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=60))


def token():
    p = os.path.join(LOCAL, 'token.json')                 # short-lived SAS token: local only, never committed
    try:
        t = json.load(open(p))
        exp = datetime.datetime.strptime(t['msft:expiry'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
        if exp.timestamp() - time.time() > 600: return t['token']
    except Exception: pass
    t = http_json(TOKEN); json.dump(t, open(p, 'w')); return t['token']


def usda_items(year):
    """catalog query of the USDA image service -> pseudo-STAC items {id, oid, attributes, properties.proj:bbox}."""
    q = dict(where=f"year_ts={int(year)} AND ST='CA'", geometry=f"{AOI['lon0']},{AOI['lat0']},{AOI['lon1']},{AOI['lat1']}",
             geometryType='esriGeometryEnvelope', inSR=4326, spatialRel='esriSpatialRelIntersects', outFields='*',
             returnGeometry='true', outSR=26910, f='json')
    url = USDA + '/query?' + urllib.parse.urlencode(q)
    d = http_json(url)
    out = []
    for f in d['features']:
        r = f['geometry']['rings'][0]; xs = [p[0] for p in r]; ys = [p[1] for p in r]
        a = f['attributes']
        date = datetime.datetime.fromtimestamp(a['QQDATE'] / 1000, datetime.timezone.utc).strftime('%Y-%m-%d')
        out.append({'id': a['Name'], 'oid': a['OBJECTID'], 'attributes': a, 'footprint_utm10n': r,
                    'query_url': url, 'flight_date': date,
                    'properties': {'naip:year': str(year), 'proj:bbox': [min(xs), min(ys), max(xs), max(ys)]}})
    return out


def usda_read(oid, e0, n0, e1, n1, dl, g=GRID, chunk=2000):   # >2000 px per side returns HTTP 500 (sfo3d, tested)
    """exportImage of one locked raster over [e0,e1]x[n0,n1] (EPSG:26910) -> (4, H, W) uint8, in chunks."""
    import rasterio
    W, H = int(round((e1 - e0) / g)), int(round((n1 - n0) / g))
    arr = np.zeros((4, H, W), np.uint8)
    mr = json.dumps({'mosaicMethod': 'esriMosaicLockRaster', 'lockRasterIds': [oid]})
    for r0 in range(0, H, chunk):
        for c0 in range(0, W, chunk):
            h, w = min(chunk, H - r0), min(chunk, W - c0)
            bb = (e0 + c0 * g, n1 - (r0 + h) * g, e0 + (c0 + w) * g, n1 - r0 * g)
            p = dict(bbox=','.join(f'{v:.3f}' for v in bb), bboxSR=26910, imageSR=26910, size=f'{w},{h}', format='tiff',
                     pixelType='U8', interpolation='RSP_NearestNeighbor', compression='LZ77', mosaicRule=mr, f='image')
            tmp = os.path.join(dl, f'chunk_{oid}_{r0}_{c0}.tif')
            for attempt in range(4):
                try:
                    data = urllib.request.urlopen(USDA + '/exportImage?' + urllib.parse.urlencode(p), timeout=300).read()
                    open(tmp, 'wb').write(data); break
                except Exception as ex:
                    print('    retry', attempt, ex); time.sleep(5)
            with rasterio.open(tmp) as ds:
                assert ds.crs.to_epsg() == 26910, ds.crs
                assert abs(ds.transform.a - g) < 1e-6 and abs(ds.transform.e + g) < 1e-6, ds.transform
                assert abs(ds.transform.c - bb[0]) < 1e-3 and abs(ds.transform.f - bb[3]) < 1e-3, (ds.transform, bb)
                assert ds.count >= 4 and (ds.width, ds.height) == (w, h), (ds.count, ds.width, ds.height)
                arr[:, r0:r0 + h, c0:c0 + w] = ds.read()[:4]
            os.remove(tmp)
    return arr


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def update_json(path, key, value):
    d = json.load(open(path)) if os.path.exists(path) else {}
    d[key] = value
    json.dump(dict(sorted(d.items())), open(path, 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--year', default=None)
    ap.add_argument('--source', default='pc', choices=['pc', 'usda'])
    ap.add_argument('--margin', type=float, default=0.0, help='extra margin (m); the AOI already includes 300 m')
    a = ap.parse_args()
    fetched = datetime.date.today().isoformat()
    bbox = [AOI['lon0'], AOI['lat0'], AOI['lon1'], AOI['lat1']]
    if a.source == 'pc':
        res = http_json(STAC, {'collections': ['naip'], 'bbox': bbox, 'limit': 100})
        feats = res['features']
        years = sorted({str(f['properties']['naip:year']) for f in feats})
        year = str(a.year or years[-1])
        items = [f for f in feats if str(f['properties']['naip:year']) == year]
        json.dump({'request': {'url': STAC, 'collections': ['naip'], 'bbox': bbox, 'limit': 100},
                   'ids': [f['id'] for f in feats]}, open(os.path.join(CACHE, 'stac_search.json'), 'w'), indent=1)
        for f in items: f['flight_date'] = f['properties']['datetime'][:10]
    else:
        year = str(a.year or '2024'); years = [year]
        items = usda_items(year)
    print(a.source, 'NAIP years available over AOI:', years, '-> using', year, [f['id'] for f in items])
    assert items, 'no items'
    idir = os.path.join(CACHE, f'items_{year}'); os.makedirs(idir, exist_ok=True)
    for f in items: json.dump(f, open(os.path.join(idir, f['id'] + '.json'), 'w'), indent=1)

    import rasterio
    from rasterio.windows import from_bounds
    G = aoi_grid(); g = GRID
    e0, e1, n0, n1 = G['e0'] - a.margin, G['e1'] + a.margin, G['n0'] - a.margin, G['n1'] + a.margin
    W, H = int(round((e1 - e0) / g)), int(round((n1 - n0) / g))
    assert abs(e0 / g - round(e0 / g)) < 1e-6 and abs(n1 / g - round(n1 / g)) < 1e-6, 'grid not on 0.6 m multiples'
    print(f'output grid {W} x {H} px, E {e0:.1f}..{e1:.1f}, N {n0:.1f}..{n1:.1f}')
    out = np.zeros((4, H, W), np.uint8)
    best = np.full((H, W), np.inf, np.float32)
    tidx = np.zeros((H, W), np.uint8)
    pe, pn = e0 + (np.arange(W) + 0.5) * g, n1 - (np.arange(H) + 0.5) * g   # pixel-centre coordinates (1-D)
    tok = token() if a.source == 'pc' else None
    dl = os.path.join(LOCAL, f'_dl_{a.source}_{year}_{int(time.time())}'); os.makedirs(dl)   # own new dir per run
    tiles = []
    for ti, f in enumerate(items):
        pb = f['properties']['proj:bbox']; ce, cn = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
        t0 = time.time()
        if a.source == 'usda':
            ie0, ie1 = max(e0, np.floor(pb[0] / g) * g), min(e1, np.ceil(pb[2] / g) * g)
            in0, in1 = max(n0, np.floor(pb[1] / g) * g), min(n1, np.ceil(pb[3] / g) * g)
            if ie0 >= ie1 or in0 >= in1: continue
            arr = usda_read(f['oid'], ie0, in0, ie1, in1, dl, g)
            href = USDA + '/exportImage (mosaicRule LockRaster ' + str(f['oid']) + ')'
        else:
            href = f['assets']['image']['href']
            url = '/vsicurl/' + href + '?' + tok
            with rasterio.Env(CURL_CA_BUNDLE='/root/.ccr/ca-bundle.crt', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                              GDAL_HTTP_MULTIRANGE='YES', GDAL_HTTP_MERGE_CONSECUTIVE_RANGES='YES', VSI_CACHE='TRUE'):
                with rasterio.open(url) as ds:
                    assert abs(ds.transform.a - g) < 1e-9 and ds.crs.to_epsg() == 26910
                    assert abs(ds.transform.c / g - round(ds.transform.c / g)) < 1e-6, ds.transform   # native grid
                    assert abs(ds.transform.f / g - round(ds.transform.f / g)) < 1e-6, ds.transform
                    ie0, ie1 = max(e0, ds.bounds.left), min(e1, ds.bounds.right)
                    in0, in1 = max(n0, ds.bounds.bottom), min(n1, ds.bounds.top)
                    if ie0 >= ie1 or in0 >= in1: continue
                    win = from_bounds(ie0, in0, ie1, in1, ds.transform).round_offsets().round_lengths()
                    arr = ds.read(window=win)
        c0 = int(round((ie0 - e0) / g)); r0 = int(round((n1 - in1) / g)); h, w = arr.shape[1:]
        d = np.hypot(pe[None, c0:c0 + w] - ce, pn[r0:r0 + h, None] - cn).astype(np.float32)
        valid = arr[:3].max(0) > 0
        take = valid & (d < best[r0:r0 + h, c0:c0 + w])
        for b in range(4): out[b, r0:r0 + h, c0:c0 + w][take] = arr[b][take]
        best[r0:r0 + h, c0:c0 + w][take] = d[take]
        tidx[r0:r0 + h, c0:c0 + w][take] = ti + 1
        tiles.append(dict(id=f['id'], flight_date=f['flight_date'], href=href, footprint_bbox_utm=pb,
                          footprint_centre_utm=[ce, cn], read_window_utm=[float(ie0), float(in0), float(ie1), float(in1)]))
        print(f"  {f['id']}: {w}x{h} px read in {time.time() - t0:.0f} s")
    shutil.rmtree(dl, ignore_errors=True)
    for i, t in enumerate(tiles):
        t['pixels_used'] = int((tidx == i + 1).sum())
    empty = int((out[:3].max(0) == 0).sum())

    # ---- full-res GeoTIFF (local) ----
    from rasterio.transform import from_origin
    src_txt = ('USDA FSA NAIP via Microsoft Planetary Computer (collection naip)' if a.source == 'pc'
               else 'USDA FPAC-BC-GEO NAIP image service ' + USDA)
    path = geotiff_path(year)
    prof = dict(driver='GTiff', width=W, height=H, count=4, dtype='uint8', crs='EPSG:26910',
                transform=from_origin(e0, n1, g, g), tiled=True, blockxsize=512, blockysize=512, compress='deflate',
                predictor=2, photometric='RGB', interleave='pixel')
    with rasterio.open(path, 'w', **prof) as dst:
        dst.write(out)
        dst.update_tags(SOURCE=src_txt, ITEMS=','.join(t['id'] for t in tiles), YEAR=year,
                        LICENCE='USDA NAIP - public domain; credit: ' + CREDIT)
        dst.set_band_description(4, 'NIR')
        dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
    pix_sha = hashlib.sha256(np.ascontiguousarray(out).tobytes()).hexdigest()
    tif_mb = os.path.getsize(path) / 1e6
    print('wrote', path, f'{tif_mb:.1f} MB; empty px: {empty}')

    # ---- committed RGB JPEG + georeference ----
    from PIL import Image
    rgb = np.ascontiguousarray(np.transpose(out[:3], (1, 2, 0)))
    jp = jpeg_path(year)
    Image.fromarray(rgb).save(jp, quality=JPEG_Q, subsampling=0, optimize=True)
    jmb = os.path.getsize(jp) / 1e6
    assert jmb <= MAX_COMMIT_MB, f'JPEG {jmb:.1f} MB > {MAX_COMMIT_MB} MB'
    back = np.asarray(Image.open(jp).convert('RGB')).astype(np.int16)
    err = np.abs(back - rgb.astype(np.int16))
    jpeg_err = dict(mean_abs=float(err.mean()), p99_abs=float(np.percentile(err, 99)), max_abs=int(err.max()))
    del back, err
    open(jp[:-4] + '.jgw', 'w').write(f'{g:.1f}\n0.0\n0.0\n{-g:.1f}\n{e0 + g / 2:.3f}\n{n1 - g / 2:.3f}\n')
    Image.fromarray(tidx).save(os.path.join(CACHE, f'naip_{year}_hwd_tileidx.png'), optimize=True)
    geo = dict(crs='EPSG:26910', crs_name='NAD83 / UTM zone 10N (NAIP E/N treated as NAD83(2011), as hwd_frame.py)',
               origin_E=e0, origin_N=n1, origin_is='outer north-west corner of pixel (col 0, row 0)',
               pixel_size_m=g, width=W, height=H, bounds_utm=[e0, n0, e1, n1],
               pixel_centre='E = origin_E + (col + 0.5) * pixel_size_m ; N = origin_N - (row + 0.5) * pixel_size_m',
               gdal_geotransform=[e0, g, 0.0, n1, 0.0, -g],
               world_file=os.path.basename(jp)[:-4] + '.jgw (pixel-centre convention of ESRI world files)',
               aoi_latlon_nad83=AOI, native_grid='0.6 m, origin on multiples of 0.6 m (same grid as the NAIP tiles)',
               bands='R, G, B (NIR only in the local GeoTIFF)', year=year, source=a.source, source_text=src_txt,
               tiles=tiles, overlap_rule='each pixel from the tile whose footprint-bbox centre is nearest',
               tile_index_png=f'naip_{year}_hwd_tileidx.png (0 = no data, k = tiles[k-1])', empty_px=empty,
               jpeg=dict(file=os.path.basename(jp), quality=JPEG_Q, chroma_subsampling='4:4:4',
                         error_vs_fullres_dn=jpeg_err),
               credit=CREDIT, made_by='hwd3d/tools/imagery/naip_fetch.py', fetched=fetched)
    json.dump(geo, open(georef_path(year), 'w'), indent=1)
    print(f'wrote {jp} {jmb:.1f} MB (JPEG error mean {jpeg_err["mean_abs"]:.2f} DN, p99 {jpeg_err["p99_abs"]:.0f})')

    # ---- SOURCES.json / MANIFEST.json ----
    ids = [t['id'] for t in tiles]; dates = sorted({t['flight_date'] for t in tiles})
    url = (USDA if a.source == 'usda' else STAC + ' (collection naip) -> ' + ', '.join(t['href'] for t in tiles))
    lic = ('public domain (USDA NAIP; data.gov licence https://www.usa.gov/publicdomain/label/1.0/). Credit requested by '
           'USDA FPAC-BC GEO ("asks to be credited for derived products"): ' + CREDIT)
    common = dict(url=url, licence=lic, fetched=fetched, items=ids, flight_dates=dates, year=year,
                  made_by='hwd3d/tools/imagery/naip_fetch.py --source ' + a.source + ' --year ' + year)
    S = os.path.join(CACHE, 'SOURCES.json')
    for fn, note in [(os.path.basename(jp), 'RGB, full resolution 0.6 m, JPEG q92 4:4:4 of the local GeoTIFF'),
                     (os.path.basename(jp)[:-4] + '.jgw', 'world file of the JPEG'),
                     (os.path.basename(georef_path(year)), 'exact georeference + provenance of the JPEG'),
                     (f'naip_{year}_hwd_tileidx.png', 'per-pixel source tile index of the mosaic'),
                     (f'items_{year}/*.json', 'STAC items (pc) / USDA catalog records (usda) used')]:
        update_json(S, fn, dict(common, note=note))
    if a.source == 'pc':
        update_json(S, 'stac_search.json', dict(common, note='STAC search request and all item ids over the AOI'))
    M = os.path.join(CACHE, 'MANIFEST.json')
    rel = lambda p: os.path.relpath(p, os.path.join(CACHE, '..', '..', '..'))
    update_json(M, rel(path), dict(committed=False, why=f'{tif_mb:.1f} MB > 25 MB per-file limit; re-fetch with '
                                   f'naip_fetch.py --source {a.source} --year {year}',
                                   bytes=os.path.getsize(path), sha256=sha256_file(path),
                                   pixels_sha256=pix_sha, pixels_layout='uint8 array (4 bands R,G,B,NIR; H; W) C-order',
                                   shape=[4, H, W], items=ids, fetched=fetched,
                                   note='file sha256 depends on the GDAL/rasterio writer; pixels_sha256 does not'))
    for p in (jp, georef_path(year), jp[:-4] + '.jgw', os.path.join(CACHE, f'naip_{year}_hwd_tileidx.png')):
        update_json(M, rel(p), dict(committed=True, bytes=os.path.getsize(p), sha256=sha256_file(p)))
    print('tiles:', [(t['id'], t['flight_date'], t['pixels_used']) for t in tiles])


if __name__ == '__main__':
    main()
