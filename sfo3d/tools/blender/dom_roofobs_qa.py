"""QA plot of tools/blender/dom_roofobs.json (local, out/buildings3d/dom_roofobs_qa.png): NAIP 2024 (public domain; a
measurement backdrop, never a texture) with the rooftop units (yellow, at their imaged position = lean-free + lean x
(deck + unit height)) and the PV tables (green, imaged)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import dom_geom as G  # noqa: E402
import draw_lib as DL  # noqa: E402

O = json.load(open(os.path.join(HERE, 'dom_roofobs.json')))
x0, z0, x1, z1 = -1200, -300, -460, 960
win = [a for a in sys.argv[1:5]]
if len(win) == 4: x0, z0, x1, z1 = map(float, win)
rgb, (X0, Z0, X1, Z1) = DL.naip_rgb(x0, z0, x1, z1, res=0.5, bounds=True); R = (X1 - X0) / rgb.shape[1]
sc = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
im = Image.fromarray(rgb).convert('RGB')
if sc != 1.0: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
dr = ImageDraw.Draw(im)
P = lambda x, z: ((x - X0) / R * sc, (z - Z0) / R * sc)  # noqa: E731
for reg, r in O['pv_tables'].items():
    for t in r['tables']:
        dr.polygon([P(x + r['shift_m'], z) for x, z in t['ring']], outline=(0, 170, 0))
for k, r in O['units'].items():
    for u in r['units']:
        dr.polygon([P(x + r['lean_east'] * (r['deck_h'] + u['h']), z) for x, z in u['ring']], outline=(255, 0, 0), fill=None if os.environ.get('NOFILL') else (255, 220, 0))
out = sys.argv[6] if len(sys.argv) > 6 else os.path.join(G.ROOT, 'out', 'buildings3d', 'dom_roofobs_qa.png')
im.save(out); print(out, im.size)
