"""B3: resample the Umbra GEC overview (CC BY 4.0) into the world frame around airport buildings and draw the OSM
footprints, to look for SAR layover / shadow that would give building heights.

usage: python3 -I sha3d/tools/standards/umbra_crops.py sha3d OUT.png [res_m]
"""
import json, sys, os, math
import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
root, outp = sys.argv[1], sys.argv[2]
res = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
sys.path.insert(0, os.path.join(root, 'tools', 'common'))
import frame  # noqa: E402
UMBRA_OFF = (6.1, 0.9)  # Umbra - OSM: +6.1 m E, -0.9 m N (= +0.9 m in z), airport.md 3.2 (ground features)
src = rasterio.open(os.path.join(root, 'refs/cache/imagery/umbra_opendata/umbra_gec_ovr4.tif'))
arr = src.read(1).astype(np.float32); inv = ~src.transform
A = json.load(open(os.path.join(root, 'data/sha_airport.json'), encoding='utf-8'))
B = {b.get('role') or b['id']: b for b in A['buildings']}
ct = A['control_tower']
def crop(cx, cz, half):
    n = int(2 * half / res)
    xs = cx - half + (np.arange(n) + 0.5) * res; zs = cz - half + (np.arange(n) + 0.5) * res
    X, Z = np.meshgrid(xs, zs)
    # world -> ll (vectorised by small-angle linearisation around the centre; error < 1 cm over 1 km)
    la0, lo0 = frame.world_to_ll(cx, cz); la1, lo1 = frame.world_to_ll(cx + 100, cz); la2, lo2 = frame.world_to_ll(cx, cz + 100)
    lat = la0 + (X - cx) / 100 * (la1 - la0) + (Z - cz) / 100 * (la2 - la0)
    lon = lo0 + (X - cx) / 100 * (lo1 - lo0) + (Z - cz) / 100 * (lo2 - lo0)
    c, r = inv * (lon, lat)
    c = np.clip(c.astype(int), 0, arr.shape[1] - 1); r = np.clip(r.astype(int), 0, arr.shape[0] - 1)
    return arr[r, c], xs, zs
targets = [('T2 main hall (west half)', -1200, 150, 330, ['T2']), ('T1', 620, 220, 260, ['T1']),
           ('China Eastern hangar', -815, 1480, 160, ['MU_hangar']), ('big hangar (E)', 900, -780, 170, ['hangar']),
           ('FBO', 560, 1060, 140, ['FBO']), ('control tower (E)', ct['x'] if 'x' in ct else 0, ct['z'] if 'z' in ct else 0, 110, []),
           ('SW towers', -970, 1130, 110, ['tower_sw_1', 'tower_sw_2']), ('T2 north pier', -950, 425, 200, ['T2'])]
tiles = []
for name, cx, cz, half, roles in targets:
    a, xs, zs = crop(cx, cz, half)
    v = np.clip(255 * np.sqrt(a / np.percentile(a[a > 0], 99.5) if (a > 0).any() else a), 0, 255).astype(np.uint8)
    im = Image.fromarray(v).convert('RGB'); d = ImageDraw.Draw(im)
    def px(x, z): return ((x + UMBRA_OFF[0] - xs[0]) / res, (z + UMBRA_OFF[1] - zs[0]) / res)
    for b in A['buildings']:
        ring = b['ring']
        if all(abs(p[0] - cx) > half or abs(p[1] - cz) > half for p in ring): continue
        col = (255, 60, 60) if (b.get('role') in roles) else (60, 200, 255)
        d.line([px(*p) for p in ring] + [px(*ring[0])], fill=col, width=2)
    d.rectangle([0, 0, im.width, 18], fill=(0, 0, 0)); d.text((4, 3), f'{name}  ({res} m/px, N up, sensor W)', fill=(255, 255, 255))
    tiles.append(im.resize((600, 600)))
cols = 4; rows = math.ceil(len(tiles) / cols)
sheet = Image.new('RGB', (cols * 600, rows * 600 + 30), (0, 0, 0))
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * 600, (i // cols) * 600))
ImageDraw.Draw(sheet).text((6, rows * 600 + 8), 'Umbra Open Data 2024-06-02 UMBRA-05 GEC (CC BY 4.0), 4x overview; OSM footprints (ODbL) shifted by the Umbra-OSM ground offset (+6.1 E, -0.9 N). Red = target.', fill=(255, 255, 255))
sheet.save(outp, quality=88)
print('ok', outp)
