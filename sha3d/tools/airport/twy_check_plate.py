"""Close-ups of the taxiway re-fit decisions on Sentinel-2 and Umbra (docs/phase1/airport_twy_checks.jpg).

usage: python3 -I sha3d/tools/airport/twy_check_plate.py SHA3D_DIR OUT_JPG
Rows: taxiway D at the T2 apron edge (phase-0 flag, NOT moved: the symmetric-pavement fit is pulled into the paved
junction), and the two runs that were moved (A2, H4). Grey = OSM line before, bright green = re-fitted line.
"""
import os
import sys

os.environ['SHA3D_ROOT'] = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overlay as OV  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

rows = [('D at the T2 apron edge: phase-0 flag, not moved', (-595, 690), 420),
        ('A2 rapid exit: moved +4.1 m (S2B + Umbra)', (100, -445), 300),
        ('H4 link: one vertex moved +4.2 m (S2C + Umbra)', (-190, -72), 300)]
tiles = []
for name, (cx, cz), w in rows:
    for mk, src in ((OV.s2_image, 'Sentinel-2 S2B 2026-10-14'), (OV.umbra_image, 'Umbra SAR 2024-06-02')):
        res = w / 560
        im = mk(cx - w / 2, cz - w / 2, cx + w / 2, cz + w / 2, res)
        OV.draw_data(im, cx - w / 2, cz - w / 2, res)
        OV.label(im, f'{name} - {src}', size=13)
        OV.scalebar(im, res, 50, (16, im.height - 16))
        tiles.append(im)
W, H = tiles[0].size
c = Image.new('RGB', (2 * W + 10, 3 * H + 20 + 80), (20, 20, 20))
for k, t in enumerate(tiles):
    c.paste(t, ((k % 2) * (W + 10), (k // 2) * (H + 10)))
d = ImageDraw.Draw(c)
f = ImageFont.truetype(OV.FONT, 14)
d.multiline_text((10, 3 * H + 26), 'grey = OSM line before the re-fit, bright green = re-fitted, yellow = other OSM taxiways, '
                 'blue = apron edge,\nmagenta dot = holding position. Images in their own georeferencing.\n'
                 'Contains modified Copernicus Sentinel data 2026.  Umbra SAR Open Data, Umbra Lab Inc (CC BY 4.0).  '
                 'Map data (c) OpenStreetMap contributors (ODbL 1.0).', font=f, fill=(235, 235, 235), spacing=4)
c.save(sys.argv[2], quality=88)
print(sys.argv[2], c.size)
