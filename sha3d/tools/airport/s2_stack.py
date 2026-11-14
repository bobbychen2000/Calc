"""Fetch a time stack of small Sentinel-2 L2A windows over the ZSSS stand areas (Copernicus Sentinel data, free and open;
Element 84 Earth Search STAC v1 + sentinel-cogs COGs by HTTP range requests). Task A2: parked-aircraft footprints per
stand over many dates (tools/airport/stand_s2.py).

usage: python3 -I s2_stack.py OUT_DIR [MAX_CLOUD_PCT]
Writes OUT_DIR/search.json (the STAC search response, assets kept), OUT_DIR/<item id>/{B02,B03,B04,SCL}.tif (native UTM
51N grid; uint16 DN; SCL uint8 at 20 m) and OUT_DIR/stack.json (per item: datetime, cloud cover, files, sha256).
Window: world x -1350..950, z -1650..1750 (tools/common/frame.py), i.e. the stand areas only (2.3 x 3.4 km).
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402

os.environ.setdefault('CURL_CA_BUNDLE', '/root/.ccr/ca-bundle.crt')
os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
os.environ.setdefault('GDAL_HTTP_MAX_RETRY', '4')
import ssl  # noqa: E402
import rasterio  # noqa: E402
from rasterio.windows import from_bounds  # noqa: E402
from pyproj import Transformer  # noqa: E402

STAC = 'https://earth-search.aws.element84.com/v1/search'
BOX = (-1350, -1650, 950, 1750)
BANDS = {'blue': 'B02', 'green': 'B03', 'red': 'B04', 'scl': 'SCL'}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main(out, max_cloud):
    os.makedirs(out, exist_ok=True)
    lat_c, lon_c = F.world_to_ll(0, 0)
    body = {'collections': ['sentinel-2-l2a'], 'intersects': {'type': 'Point', 'coordinates': [lon_c, lat_c]},
            'datetime': '2023-01-01T00:00:00Z/2026-11-14T00:00:00Z', 'query': {'eo:cloud_cover': {'lt': max_cloud}},
            'limit': 200}
    ctx = ssl.create_default_context(cafile=os.environ['CURL_CA_BUNDLE'])
    req = urllib.request.Request(STAC, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json',
                                                                                 'User-Agent': 'stand-research/0.1'})
    d = json.load(urllib.request.urlopen(req, context=ctx, timeout=60))
    json.dump(d, open(os.path.join(out, 'search.json'), 'w'))
    # one item per acquisition day (prefer the newest processing: '_1' over '_0')
    items = {}
    for f in sorted(d['features'], key=lambda f: f['id']):
        day = f['properties']['datetime'][:10]
        items[day] = f
    lls = [F.world_to_ll(x, z) for x in (BOX[0], BOX[2]) for z in (BOX[1], BOX[3])]
    stack = {'stac': STAC, 'search_body': body, 'box_world': BOX, 'items': []}
    for day, f in sorted(items.items()):
        iid = f['id']; od = os.path.join(out, iid); os.makedirs(od, exist_ok=True)
        epsg = f['properties']['proj:epsg']
        tr = Transformer.from_crs('EPSG:4326', f'EPSG:{epsg}', always_xy=True)
        xs, ys = zip(*[tr.transform(lo, la) for la, lo in lls])
        bounds = (min(xs), min(ys), max(xs), max(ys))
        rec = {'id': iid, 'datetime': f['properties']['datetime'], 'cloud_pct': f['properties'].get('eo:cloud_cover'),
               'epsg': epsg, 'files': {}}
        for k, nm in BANDS.items():
            href = f['assets'][k]['href']
            p = os.path.join(od, nm + '.tif')
            if not os.path.exists(p):
                for attempt in range(3):
                    try:
                        with rasterio.open(href) as src:
                            win = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
                            data = src.read(window=win)
                            prof = src.profile.copy()
                            prof.update(width=data.shape[2], height=data.shape[1], transform=src.window_transform(win),
                                        tiled=False, compress='deflate', driver='GTiff')
                            prof.pop('blockxsize', None); prof.pop('blockysize', None)
                            with rasterio.open(p, 'w', **prof) as dst:
                                dst.write(data)
                        break
                    except Exception as e:  # noqa: BLE001
                        print('retry', iid, nm, e, flush=True); time.sleep(3)
            if os.path.exists(p):
                rec['files'][nm] = {'href': href, 'sha256': sha(p), 'bytes': os.path.getsize(p)}
        stack['items'].append(rec)
        print(iid, rec['cloud_pct'], len(rec['files']), flush=True)
    json.dump(stack, open(os.path.join(out, 'stack.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 20.0)
