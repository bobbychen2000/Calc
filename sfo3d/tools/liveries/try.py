#!/usr/bin/env python3
"""Development helper: bake brands on one model/type and render quick previews into a contact sheet.
Usage: python3 tools/liveries/try.py <model.sfom> <type> <out.png> BRAND [BRAND ...] [--views side,34] [--size 1024]"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
import paint, preview, liveries
args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=') for a in sys.argv[1:] if a.startswith('--'))
model, typ, out = args[:3]; brands = args[3:]
views = opts.get('views', 'side,34').split(','); S = int(opts.get('size', 1024)); W = int(opts.get('w', 760)); H = int(opts.get('h', 330))
c = paint.Canvas(model, typ, S)
m, P = preview.load_for(model, typ)
rows = []
for b in brands:
    c.reset(); liveries.LIVERIES[b]['paint'](c); img = c.finish()
    ims = [preview.render(m, P, m['textures'], v, W, H, img) for v in views]
    row = Image.new('RGB', (W * len(ims), H + 18), (255, 255, 255))
    for i, im in enumerate(ims): row.paste(im, (i * W, 18))
    ImageDraw.Draw(row).text((4, 3), f'{b} on {typ}', fill=(0, 0, 0))
    rows.append(row)
    if opts.get('save'): img.save(os.path.join(opts['save'], f'{b}_{typ}.webp'), 'WEBP', quality=88)
sheet = Image.new('RGB', (rows[0].size[0], sum(r.size[1] for r in rows)), (255, 255, 255))
y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.size[1]
sheet.save(out); print(out)
