"""Side-by-side sheet: WebGL (left) vs Blender Cycles (right) for each review shot.
Usage: python3 test/blender/compare.py <dir> <out.png> name [name ...]   (reads <dir>/<name>_webgl.png + <dir>/<name>.png)
"""
import os
import sys

from PIL import Image, ImageDraw

d, out, names = sys.argv[1], sys.argv[2], sys.argv[3:]
rows = []
for n in names:
    a, b = os.path.join(d, n + '_webgl.png'), os.path.join(d, n + '.png')
    if os.path.exists(a) and os.path.exists(b):
        rows.append((n, Image.open(a).convert('RGB'), Image.open(b).convert('RGB')))
W = max(r[1].width + r[2].width for r in rows) + 12
H = sum(max(r[1].height, r[2].height) + 26 for r in rows)
sheet = Image.new('RGB', (W, H), (245, 245, 243))
dr = ImageDraw.Draw(sheet)
y = 0
for n, a, b in rows:
    dr.text((6, y + 7), n + '  |  WebGL engine (left)  vs  Blender Cycles (right)', fill=(30, 30, 30))
    sheet.paste(a, (4, y + 22)); sheet.paste(b, (8 + a.width, y + 22))
    y += max(a.height, b.height) + 26
sheet.save(out)
print('sheet', out, W, H)
