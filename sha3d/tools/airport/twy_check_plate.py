"""Close-ups of the taxiway re-fit decisions on Sentinel-2 and Umbra (docs/phase1/airport_twy_checks.jpg).

usage: python3 -I sha3d/tools/airport/twy_check_plate.py SHA3D_DIR OUT_JPG
Rows: taxiway D at the T2 apron edge (phase-0 flag, NOT moved: the symmetric-pavement fit is pulled into the paved
junction), the runs moved after QA C1 M1 (A2 both runs, A1, H2, H7, N, an unnamed taxiway; H4 as before), and BN,
which is left at the OSM position since fix round 2 (Umbra veto: both S2 scenes say -3.7 m, the sharper Umbra -0.6 m).
Grey = OSM line before, bright green = re-fitted line (with the 40 m junction tapers of tools/airport/twy_refit.py).
"""
import os
import sys

os.environ['SHA3D_ROOT'] = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overlay as OV  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

rows = [('D at the T2 apron edge: phase-0 flag, not moved', (-595, 690), 420),
        ('A2 rapid exit: both runs moved (+6.7 / +3.8 m)', (98, -460), 360),
        ('A1 rapid exit: moved +7.7 m (Umbra + S2B)', (97, -959), 360),
        ('H2 crossing: moved +3.5 m (S2B + Umbra)', (-458, -1522), 460),
        ('H7 crossing: moved -4.8 m (S2B + Umbra)', (-41, 1589), 560),
        ('BN: not moved, Umbra veto (S2 -3.7 m, Umbra -0.6 m)', (-271, -1827), 400),
        ('N (north edge): last run moved +7.0 m (S2B + S2C)', (-403, -2290), 300),
        ('unnamed taxiway east of 18L/36R: moved -3.8 m (S2B + Umbra)', (176, -1947), 420)]
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
NR = len(rows)
c = Image.new('RGB', (2 * W + 10, NR * H + (NR - 1) * 10 + 80), (20, 20, 20))
for k, t in enumerate(tiles):
    c.paste(t, ((k % 2) * (W + 10), (k // 2) * (H + 10)))
d = ImageDraw.Draw(c)
f = ImageFont.truetype(OV.FONT, 14)
d.multiline_text((10, NR * H + (NR - 1) * 10 + 6), 'grey = OSM line before the re-fit, bright green = re-fitted (moves tapered to zero over 40 m along '
                 'neighbouring ways),\nyellow = other OSM taxiways, blue = apron edge, magenta dot = holding position. '
                 'Images in their own georeferencing.\n'
                 'Contains modified Copernicus Sentinel data 2026.  Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0, modified.\n'
                 'Map data (c) OpenStreetMap contributors (ODbL 1.0).', font=f, fill=(235, 235, 235), spacing=4)
c.save(sys.argv[2], quality=88)
print(sys.argv[2], c.size)
