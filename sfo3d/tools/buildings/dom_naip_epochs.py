"""Domestic terminals (Harvey Milk T1 + Boarding Areas B/C, T2 + BA D, T3 + BA E/F) - multi-epoch NAIP rasters on the
project world grid, for the building research spec (tools/buildings/spec_domestic.json, docs/research/buildings_domestic.md).

Why several epochs: NAIP is orthorectified to a terrain DEM, so roofs are displaced away from the nadir of the flight
line ("relief displacement", docs/research/imagery.md s.6). Each year was flown on a different line, so a roof point at
height h moves between two epochs by (k_b - k_a) * h, while ground features stay put. The domestic roofs are measured
with that inter-epoch shift (tools/buildings/dom_relief.py), calibrated on FAA DOF poles of known height. 2020 was flown
in the late afternoon (long ESE shadows), 2024 near solar noon, which also gives two independent shadow directions.

What it does: for each epoch it reads the domestic-terminal window from the source GeoTIFF (2018-2022: Microsoft
Planetary Computer COGs, windowed HTTP range reads of the NAIP DOQQ m_3712229_ne, which covers the whole window;
2024: the local USDA mosaic refs/cache/naip/naip_2024_sfo_utm10n.tif made by tools/imagery/naip_fetch.py) and
resamples it bilinearly onto the world grid (tools/geo_frame.py, frame ltp-nad83-2011; NAIP is NAD83 / UTM 10N,
EPSG:26910, so the world lat/lon is used as NAD83 directly), north-up, 0.25 m/px (native GSD 0.6 m).

Outputs (NAIP is U.S. public domain, but these are imagery - kept local, never shipped):
  refs/cache/buildings/domestic/naip/naip_<year>_dom.png     x WIN.x0..x1, z WIN.z0..z1, RES m/px, pixel centres at
                                                             x0 + (col + 0.5) * RES, z0 + (row + 0.5) * RES
  refs/cache/buildings/domestic/naip/naip_epochs.json        per-epoch provenance (item id, flight date, source URL)

usage: python3 tools/buildings/dom_naip_epochs.py [--years 2018,2020,2022,2024]
"""
import argparse, json, os, sys, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

OUT = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'domestic', 'naip')
NAIP_CACHE = os.path.join(ROOT, 'refs', 'cache', 'naip')
STAC_SEARCH = os.path.join(NAIP_CACHE, 'stac_search.json')   # saved by tools/imagery/naip_fetch.py (Planetary Computer)
TOKEN_URL = 'https://planetarycomputer.microsoft.com/api/sas/v1/token/naip'
# world window: bounding box of the SFO Museum footprints of T1/BA-B/BA-C, T2/BA-D, T3/BA-E/BA-F
# (data/sfo_airport.json: x -1332..-476, z -267..940) plus a 25-45 m margin for aprons and shadows
WIN = dict(x0=-1360.0, x1=-440.0, z0=-300.0, z1=970.0)
RES = 0.25
DOQQ = 'm_3712229_ne'          # the DOQQ that contains the whole window in 2016-2022 (STAC bbox lon -122.440..-122.372,
                               # lat 37.560..37.627; window lon -122.391..-122.380, lat 37.610..37.621)


def pc_token():
    """short-lived Planetary Computer SAS token (kept in memory only)."""
    return json.load(urllib.request.urlopen(TOKEN_URL, timeout=60))['token']


def item_for(year):
    d = json.load(open(STAC_SEARCH))
    for f in d['features']:
        if str(f['properties'].get('naip:year')) == str(year) and DOQQ in f['id']:
            return f
    return None


def sample_block(ds, x0, x1, z0, z1):
    """bilinear sample of an EPSG:26910 rasterio dataset on the world grid block [x0,x1) x [z0,z1) at RES."""
    import pyproj, cv2
    from rasterio.windows import from_bounds
    xs = np.arange(x0, x1, RES) + RES / 2
    zs = np.arange(z0, z1, RES) + RES / 2
    X, Z = np.meshgrid(xs, zs)
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


def render(ds):
    W = int(round((WIN['x1'] - WIN['x0']) / RES)); H = int(round((WIN['z1'] - WIN['z0']) / RES))
    out = np.zeros((H, W, 3), np.uint8)
    B = 250.0   # block size (m) keeps memory low
    for z0 in np.arange(WIN['z0'], WIN['z1'], B):
        for x0 in np.arange(WIN['x0'], WIN['x1'], B):
            x1, z1 = min(x0 + B, WIN['x1']), min(z0 + B, WIN['z1'])
            blk = sample_block(ds, x0, x1, z0, z1)
            r0 = int(round((z0 - WIN['z0']) / RES)); c0 = int(round((x0 - WIN['x0']) / RES))
            out[r0:r0 + blk.shape[0], c0:c0 + blk.shape[1]] = blk
    return out


def main():
    import rasterio, cv2
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', default='2018,2020,2022,2024')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    mpath = os.path.join(OUT, 'naip_epochs.json')
    meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
    tok = None
    for year in a.years.split(','):
        rec = dict(year=year)
        if year == '2024':
            path = os.path.join(NAIP_CACHE, 'naip_2024_sfo_utm10n.tif')
            with rasterio.open(path) as ds:
                rgb = render(ds)
            rec.update(source='local USDA mosaic ' + os.path.relpath(path, ROOT),
                       items='m_3712229_ne_10_060_20240520 et al. (USDA image service, flown 2024-05-20)')
        else:
            f = item_for(year)
            if f is None:
                print(year, 'no item'); continue
            tok = tok or pc_token()
            href = f['assets']['image']['href']
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
                with rasterio.open('/vsicurl/' + href + '?' + tok) as ds:
                    rgb = render(ds)
            rec.update(source=href, item=f['id'], datetime=f['properties'].get('datetime'), gsd=f['properties'].get('gsd'))
        cv2.imwrite(os.path.join(OUT, f'naip_{year}_dom.png'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        rec.update(window=WIN, res_m=RES, frame=GF.FRAME_ID,
                   pixel_centre='x = x0 + (col + 0.5) * res, z = z0 + (row + 0.5) * res')
        meta[year] = rec
        json.dump(meta, open(mpath, 'w'), indent=1)
        print(year, rec.get('item', rec.get('items')), rgb.shape, flush=True)


if __name__ == '__main__':
    main()
