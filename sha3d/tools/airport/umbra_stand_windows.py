"""Read full-resolution (0.35 m IPR, ~0.22 m pixel) windows of the Umbra GEC over the ZSSS stand areas by HTTP range
requests (Umbra SAR Open Data, CC BY 4.0). Task A2 (stands, jet bridges).

usage: python3 -I umbra_stand_windows.py OUT_DIR [reg]
Writes OUT_DIR/<name>.tif for each box (world frame x0, z0, x1, z1 in metres, z = south, tools/common/frame.py): the
pixel window of the GEC covering the box, rotated geotransform kept, values unmodified (uint8). Then OUT_DIR/windows.json.
With 'reg', the registration bands (REG) are read instead: bands across the two runways and along two E-W crossings,
used to measure the GEC registration against OSM (docs/phase1/stands.md).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402

os.environ.setdefault('CURL_CA_BUNDLE', '/root/.ccr/ca-bundle.crt')
os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
import rasterio  # noqa: E402
from rasterio.windows import Window  # noqa: E402

URL = ('https://umbra-open-data-catalog.s3.amazonaws.com/sar-data/tasks/ad%20hoc/Shanghai_CHN/'
       '96b8bdc7-96bf-415e-b43b-20adc327995f/2024-06-02-01-46-47_UMBRA-05/2024-06-02-01-46-47_UMBRA-05_GEC.tif')
STANDS = {   # world x0, z0, x1, z1 (m; z = south)
    't2': (-1300, -660, -440, 1100),       # Terminal 2 piers, aprons Nr. 2 (2xx stands)
    't1e': (230, -1000, 860, 330),         # Terminal 1 (1xx), east apron (3xx), business apron
    'r4': (-1000, -1600, -560, -640),      # west remote apron (4xx; the area south of 413 too)
    'r5': (380, 330, 620, 1560),           # east remote apron (5xx)
    'r6': (-820, 1100, -480, 1720),        # south-west remote apron (6xx)
}
REG = {   # bands across the two runways and along the E-W crossings H2, H6
    'reg_e1': (-115, -1350, 15, -950), 'reg_e2': (-60, -200, 70, 200), 'reg_e3': (-5, 950, 125, 1350),
    'reg_w1': (-485, -1350, -355, -950), 'reg_w2': (-430, -200, -300, 200), 'reg_w3': (-375, 950, -245, 1350),
    'reg_h2': (-640, -1580, -260, -1460), 'reg_h6': (-560, 1380, -320, 1500),
}


def main(out, boxes):
    os.makedirs(out, exist_ok=True)
    meta = {'url': URL, 'collect': '2024-06-02T01:46:48Z UMBRA-05 spotlight, X-band VV, GEC', 'windows': {}}
    with rasterio.open('/vsicurl/' + URL) as s:
        inv = ~s.transform
        for name, (x0, z0, x1, z1) in boxes.items():
            cs, rs = [], []
            for x in (x0, x1):
                for z in (z0, z1):
                    lat, lon = F.world_to_ll(x, z)
                    c, r = inv * (lon, lat); cs.append(c); rs.append(r)
            c0, c1 = max(0, int(min(cs)) - 2), min(s.width, int(max(cs)) + 3)
            r0, r1 = max(0, int(min(rs)) - 2), min(s.height, int(max(rs)) + 3)
            win = Window(c0, r0, c1 - c0, r1 - r0)
            a = s.read(1, window=win)
            prof = s.profile.copy()
            prof.update(width=a.shape[1], height=a.shape[0], transform=s.window_transform(win), compress='deflate',
                        tiled=True, blockxsize=512, blockysize=512)
            path = os.path.join(out, name + '.tif')
            with rasterio.open(path, 'w', **prof) as d:
                d.write(a, 1)
            meta['windows'][name] = dict(box_world=[x0, z0, x1, z1], window_col_row_w_h=[c0, r0, c1 - c0, r1 - r0],
                                         shape=list(a.shape))
            print(name, a.shape, os.path.getsize(path), flush=True)
    json.dump(meta, open(os.path.join(out, 'windows.json'), 'w'), indent=1)


if __name__ == '__main__':
    reg = len(sys.argv) > 2 and sys.argv[2] == 'reg'
    main(sys.argv[1], REG if reg else STANDS)
