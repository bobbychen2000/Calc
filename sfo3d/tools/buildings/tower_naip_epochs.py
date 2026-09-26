"""SFO Airport Traffic Control Tower (2016) - multi-epoch NAIP crops for measuring the tower from above.

Why: NAIP is orthorectified to a terrain DEM, so tall objects lean away from the flight-line nadir ("relief
displacement", docs/research/imagery.md s.6). The cab roof of the 221-ft tower appears ~40 m east of its base in NAIP
2022/2024. Different NAIP years were flown on different flight lines, so the cab roof is displaced in different
directions. Where the displacement lines of several epochs intersect is the tower axis at ground level; the roof disc
itself (a circle seen from above) gives the cab roof diameter directly, independent of the lean.

What it does: for each NAIP epoch that shows the finished tower (2016, 2018, 2020, 2022, 2024) it reads a small window
around the tower from the source GeoTIFF (2016-2022: Microsoft Planetary Computer COGs, windowed HTTP range reads;
2024: the local USDA mosaic refs/cache/naip/naip_2024_sfo_utm10n.tif) and resamples it onto the project world grid
(tools/geo_frame.py, frame ltp-nad83-2011; NAIP is NAD83 / UTM 10N, EPSG:26910) at 0.1 m, north-up, with a 5 m grid.

Outputs (NAIP is U.S. public domain, but the crops are imagery - kept local):
  out/buildings/tower/naip_<year>_tower.png          raw world-grid crop (x -800..-640, z 250..410, 0.1 m/px)
  out/buildings/tower/naip_<year>_tower_grid.jpg     same with a labelled 5 m grid and the SFO Museum 'atc' outline
  out/buildings/tower/naip_epochs.json               per-epoch provenance (item id, flight date, source URL)

usage: python3 tools/buildings/tower_naip_epochs.py [--years 2016,2018,2020,2022,2024] [--res 0.1]
"""
import argparse, json, os, sys, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'imagery'))
import geo_frame as GF  # noqa: E402

OUT = os.path.join(ROOT, 'out', 'buildings', 'tower')
NAIP_CACHE = os.path.join(ROOT, 'refs', 'cache', 'naip')
STAC_SEARCH = os.path.join(NAIP_CACHE, 'stac_search.json')   # saved by tools/imagery/naip_fetch.py (Planetary Computer)
TOKEN_URL = 'https://planetarycomputer.microsoft.com/api/sas/v1/token/naip'
# world window (x east, z south, metres from the ARP) around the SFO Museum 'atc' footprint (-763..-718, 305..358)
WIN = dict(x0=-800.0, x1=-640.0, z0=250.0, z1=410.0)


def pc_token():
    """short-lived Planetary Computer SAS token (kept in memory only)."""
    return json.load(urllib.request.urlopen(TOKEN_URL, timeout=60))['token']


def items_for(year):
    d = json.load(open(STAC_SEARCH))
    return [f for f in d['features'] if str(f['properties'].get('naip:year')) == str(year)]


def world_grid(res):
    xs = np.arange(WIN['x0'], WIN['x1'], res) + res / 2
    zs = np.arange(WIN['z0'], WIN['z1'], res) + res / 2
    return np.meshgrid(xs, zs)


def sample_dataset(ds, X, Z):
    """bilinear sample of an EPSG:26910 rasterio dataset at world points; reads only the needed window."""
    import pyproj, cv2
    from rasterio.windows import from_bounds
    lat, lon = GF.world_to_ll_np(X, Z)                     # world frame is NAD83(2011) (tools/geo_frame.py)
    T = pyproj.Transformer.from_crs('EPSG:4269', 'EPSG:26910', always_xy=True)
    E, N = T.transform(lon, lat)
    m = 5.0
    win = from_bounds(E.min() - m, N.min() - m, E.max() + m, N.max() + m, ds.transform).round_offsets().round_lengths()
    img = np.transpose(ds.read([1, 2, 3], window=win, boundless=True, fill_value=0), (1, 2, 0))
    inv = ~ds.window_transform(win)
    c, r = inv * (E, N)
    return cv2.remap(np.ascontiguousarray(img), (np.asarray(c) - 0.5).astype(np.float32),
                     (np.asarray(r) - 0.5).astype(np.float32), cv2.INTER_LINEAR)


def covers(ds, X, Z):
    import pyproj
    lat, lon = GF.world_to_ll_np(np.array([X.mean()]), np.array([Z.mean()]))
    E, N = pyproj.Transformer.from_crs('EPSG:4269', 'EPSG:26910', always_xy=True).transform(lon, lat)
    b = ds.bounds
    return b.left + 100 < E[0] < b.right - 100 and b.bottom + 100 < N[0] < b.top - 100


def grid_overlay(rgb, res, ring):
    import cv2
    im = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    P = lambda x, z: (int(round((x - WIN['x0']) / res)), int(round((z - WIN['z0']) / res)))
    for g in np.arange(WIN['x0'], WIN['x1'] + 0.1, 5):
        p = P(g, WIN['z0'])[0]
        cv2.line(im, (p, 0), (p, im.shape[0]), (0, 255, 255) if g % 10 == 0 else (150, 150, 150), 1)
        if g % 20 == 0: cv2.putText(im, f'{g:.0f}', (p + 3, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 170, 255), 2)
    for g in np.arange(WIN['z0'], WIN['z1'] + 0.1, 5):
        p = P(WIN['x0'], g)[1]
        cv2.line(im, (0, p), (im.shape[1], p), (0, 255, 255) if g % 10 == 0 else (150, 150, 150), 1)
        if g % 20 == 0: cv2.putText(im, f'{g:.0f}', (3, p - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 170, 255), 2)
    cv2.polylines(im, [np.array([P(*p) for p in ring], np.int32)], True, (0, 0, 255), 2)
    return im


def main():
    import rasterio, cv2
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', default='2016,2018,2020,2022,2024')
    ap.add_argument('--res', type=float, default=0.1)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    ring = [s for s in D['structures'] if s['kind'] == 'atc'][0]['polys'][0][0]
    X, Z = world_grid(a.res)
    meta = {}
    tok = None
    for year in a.years.split(','):
        rec = dict(year=year)
        if year == '2024':
            path = os.path.join(NAIP_CACHE, 'naip_2024_sfo_utm10n.tif')
            with rasterio.open(path) as ds:
                rgb = sample_dataset(ds, X, Z)
            rec.update(source='local USDA mosaic ' + os.path.relpath(path, ROOT),
                       items='m_3712230_nw_10_060_20240520 et al. (flown 2024-05-20)')
        else:
            tok = tok or pc_token()
            rgb = None
            for f in items_for(year):
                href = f['assets']['image']['href']
                with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
                    with rasterio.open('/vsicurl/' + href + '?' + tok) as ds:
                        if not covers(ds, X, Z): continue
                        rgb = sample_dataset(ds, X, Z)
                rec.update(source=href, item=f['id'], datetime=f['properties'].get('datetime'),
                           gsd=f['properties'].get('gsd'))
                break
            if rgb is None:
                print(year, 'no covering item'); continue
        cv2.imwrite(os.path.join(OUT, f'naip_{year}_tower.png'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        cv2.imwrite(os.path.join(OUT, f'naip_{year}_tower_grid.jpg'), grid_overlay(rgb, a.res, ring),
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
        rec.update(window=WIN, res_m=a.res, frame=GF.FRAME_ID)
        meta[year] = rec
        print(year, rec.get('item', rec.get('items')), rgb.shape)
    json.dump(meta, open(os.path.join(OUT, 'naip_epochs.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
