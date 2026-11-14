"""Cut the committed Sentinel-2 crops (refs/cache/s2/<scene>/*.tif) to the SHA Live 3D detailed extent (QA C1 M8,
docs/phase1/qa_data.md; PLAN s.6b Q3 default: convex hull of the aerodrome + 1 km, 23.5 km2).

usage: python3 -I sha3d/tools/geo/s2_cut_extent.py SHA3D_DIR

For every GeoTIFF of each scene directory listed in refs/cache/s2/SOURCES.json:
  1. the extent polygon (refs/cache/osm_pinned/extent_hull1km.geojson, WGS 84) is mapped vertex by vertex into the
     raster CRS (UTM 51N); its bounding box is snapped outwards to the raster's own pixel grid (no resampling: the cut
     raster is a sub-window of the original, pixel for pixel);
  2. pixels whose centre lies outside the polygon are set to the raster's nodata value (0 = Sentinel-2 L2A no-data,
     SCL class 0 = NO_DATA);
  3. written as a DEFLATE GeoTIFF with nodata = 0 in place of the original; the original (larger) crop is moved to
     refs/cache/s2_precut/<scene>/ (local only, never committed: refs/cache/* is ignored and only the cut files in
     refs/cache/s2/ are force-added).
Idempotent: a raster that is already cut (same window) is rewritten identically from the pre-cut copy.
Pixel values inside the polygon are unchanged (checked: max |difference| = 0 over the kept pixels).
"""
import hashlib
import json
import os
import shutil
import sys

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window
from pyproj import Transformer
from shapely.geometry import Polygon, mapping


def cut(src_path, dst_path, poly_ll):
    with rasterio.open(src_path) as ds:
        tr = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True)
        ring = [tr.transform(lo, la) for lo, la in poly_ll.exterior.coords]
        poly = Polygon(ring)
        x0, y0, x1, y1 = poly.bounds
        T = ds.transform
        c0 = int(np.floor((x0 - T.c) / T.a)); c1 = int(np.ceil((x1 - T.c) / T.a))
        r0 = int(np.floor((y1 - T.f) / T.e)); r1 = int(np.ceil((y0 - T.f) / T.e))
        c0, r0 = max(c0, 0), max(r0, 0); c1, r1 = min(c1, ds.width), min(r1, ds.height)
        win = Window(c0, r0, c1 - c0, r1 - r0)
        data = ds.read(window=win)
        wt = ds.window_transform(win)
        outside = geometry_mask([mapping(poly)], out_shape=(win.height, win.width), transform=wt, invert=False,
                                all_touched=False)
        nod = ds.nodata if ds.nodata is not None else 0
        kept_before = data[:, ~outside].copy()
        data[:, outside] = nod
        prof = ds.profile.copy()
        prof.update(width=win.width, height=win.height, transform=wt, nodata=nod, compress='deflate', tiled=False,
                    predictor=2 if data.dtype.kind in 'ui' else 1)
        prof.pop('blockxsize', None); prof.pop('blockysize', None)
        src_px = ds.width * ds.height; src_bounds = ds.bounds; res = T.a
    tmp = dst_path + '.tmp'
    with rasterio.open(tmp, 'w', **prof) as out:
        out.write(data)
    os.replace(tmp, dst_path)
    assert np.array_equal(kept_before, data[:, ~outside])
    with rasterio.open(dst_path) as chk:
        b = chk.bounds
    return dict(res_m=res, px_before=src_px, px_after=int(win.width * win.height), px_inside=int((~outside).sum()),
                km2_before=round((src_bounds.right - src_bounds.left) * (src_bounds.top - src_bounds.bottom) / 1e6, 2),
                km2_bbox_after=round((b.right - b.left) * (b.top - b.bottom) / 1e6, 2),
                km2_valid_after=round(int((~outside).sum()) * res * res / 1e6, 2),
                bounds_after=[round(v, 1) for v in (b.left, b.bottom, b.right, b.top)])


def main(root):
    s2 = os.path.join(root, 'refs/cache/s2')
    pre = os.path.join(root, 'refs/cache/s2_precut')
    ext = json.load(open(os.path.join(root, 'refs/cache/osm_pinned/extent_hull1km.geojson')))['features'][0]
    poly_ll = Polygon(ext['geometry']['coordinates'][0])
    src = json.load(open(os.path.join(s2, 'SOURCES.json')))
    report = {}
    for sc in src['scenes']:
        d = os.path.join(s2, sc['dir']); dp = os.path.join(pre, sc['dir'])
        os.makedirs(dp, exist_ok=True)
        files_cut = {}
        for f in sorted(os.listdir(d)):
            if not f.endswith('.tif'):
                continue
            orig = os.path.join(dp, f)
            if not os.path.exists(orig):          # first run: keep the original crop locally
                shutil.copy2(os.path.join(d, f), orig)
            files_cut[f] = cut(orig, os.path.join(d, f), poly_ll)
        report[sc['dir']] = files_cut
        sc['files'] = {f: hashlib.sha256(open(os.path.join(d, f), 'rb').read()).hexdigest() for f in sorted(files_cut)}
        sc['files_precut_sha256'] = sc.get('files_precut_sha256') or {
            f: hashlib.sha256(open(os.path.join(dp, f), 'rb').read()).hexdigest() for f in sorted(files_cut)}
        b = files_cut['B04.tif']
        sc['window'] = ('cut 2026-11-14 to the bounding box of the detailed extent (refs/cache/osm_pinned/'
                        'extent_hull1km.geojson: convex hull of OSM relation 21913346 + 1 km, 23.545 km2) on the '
                        'native UTM 51N grid: %d x %d px at 10 m (SCL at 20 m), bounds %s; pixels outside the extent '
                        'polygon set to nodata 0 (%.2f km2 of valid pixels). Originally read as a window lon '
                        '121.300-121.370, lat 31.165-31.235 (679 x 786 px); the pre-cut crops are kept locally in '
                        'refs/cache/s2_precut/ (not committed; they remain in git history up to the cut, owner '
                        'decision Q2)' % (round((b['bounds_after'][2] - b['bounds_after'][0]) / 10),
                                           round((b['bounds_after'][3] - b['bounds_after'][1]) / 10),
                                           b['bounds_after'], b['km2_valid_after']))
    src['cut_to_extent'] = {'date': '2026-11-14', 'tool': 'tools/geo/s2_cut_extent.py',
                            'reason': 'QA C1 M8 (docs/phase1/qa_data.md): the committed crops covered 53.4 km2, '
                                      'beyond the 23.5 km2 detailed extent (PLAN s.6b Q3, s.7 Phase 1)',
                            'nodata': 0, 'per_file': report}
    json.dump(src, open(os.path.join(s2, 'SOURCES.json'), 'w'), indent=1)
    json.dump({'topic': 's2_precut', 'what': 'the Sentinel-2 crops of refs/cache/s2/ before the cut to the detailed '
                                             'extent (2026-11-14); local only, never committed',
               'licence': src['licence'], 'attribution': src['attribution'], 'commit': 'no (beyond the extent)',
               'files': {sc['dir']: sc['files_precut_sha256'] for sc in src['scenes']}},
              open(os.path.join(pre, 'SOURCES.json'), 'w'), indent=1)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
