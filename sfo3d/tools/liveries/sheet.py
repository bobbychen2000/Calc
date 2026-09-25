#!/usr/bin/env python3
"""Development helper: contact sheet of baked liveries (data/liveries) on their models, software-rendered.
Usage: python3 tools/liveries/sheet.py out.png BRAND:model[@type] ... [--view 34] [--res mid]"""
import sys, os, json
from PIL import Image, ImageDraw
import common, preview
args = [a for a in sys.argv[1:] if not a.startswith('--')]; opts = dict(a[2:].split('=') for a in sys.argv[1:] if a.startswith('--'))
out = args[0]; view = opts.get('view', '34'); res = opts.get('res', 'mid'); W, H = int(opts.get('w', 520)), int(opts.get('h', 280)); cols = int(opts.get('cols', 3))
man = json.load(open(os.path.join(common.LIV, 'manifest.json')))
ims = []
for a in args[1:]:
    b, mt = a.split(':'); m, t = (mt.split('@') + [None])[:2]
    e = next(e for e in man['entries'] if e['brand'] == b and e['model'] == m)
    f = e
    for v in e.get('variants', []):
        if t and t in v['types']: f = v
    typ = t or f['painted_as']
    mm, P = preview.load_for(os.path.join(common.MD, m + '.sfom'), typ)
    im = preview.render(mm, P, mm['textures'], view, W, H, Image.open(os.path.join(common.LIV, f['files'][res])))
    ImageDraw.Draw(im).text((4, 4), f'{b} {m} as {typ}', fill=(0, 0, 0)); ims.append(im)
rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (cols * W, rows * H), (255, 255, 255))
for i, im in enumerate(ims): S.paste(im, ((i % cols) * W, (i // cols) * H))
S.save(out); print(out)
