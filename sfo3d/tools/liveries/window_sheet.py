#!/usr/bin/env python3
"""Verification sheet of the cabin windows: for every type rendered with an imported model, an orthographic port-side view
of the model as the app stretches it for that type, wearing the texture the app gives it (a brand bake, or the neutral
skin `_N` of that type, or the model's own atlas), with the manufacturer's window stations of the type
(tools/liveries/windows.py type_rows) drawn as ticks above and below the body. Every painted or modelled window must sit
between a pair of ticks, and there must be exactly one row per deck.

Usage: python3 tools/liveries/window_sheet.py [--models b738,a320] [--brand UAL] [--out out/liveries/windows] [--w 2400]
Output: <out>/<model>@<type>[_<brand>].png, one per type, plus a text summary (window centres found in the render vs the
reference row: count, mean offset) printed per type.
"""
import argparse, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, preview, windows


def texture_for(man, model, typ, brand=None, res='hi'):
    E = {(e['brand'], e['model']): e for e in man['entries']}
    for b in ([brand] if brand else []) + ['_N']:
        e = E.get((b, model))
        if not e: continue
        for v in [e] + e.get('variants', []):
            if typ in v.get('types', []): return b, os.path.join(common.LIV, v['files'][res])
    return None, None


def sheet(model, typ, man, brand=None, W=2400, out=None):
    A = common.app()
    mm, P = preview.load_for(os.path.join(common.MD, model + '.sfom'), typ)
    b, tex = texture_for(man, model, typ, brand)
    from PIL import Image as I
    liv = I.open(tex) if tex else None
    lo, hi = P.min(0), P.max(0)
    body = mm['zone'] != 3
    L = float(-P[body, 0].min())
    # frame: the fuselage, 0.6 m margin
    ymin, ymax = float(P[body, 1].min()), float(P[body, 1].max())
    c = np.array([-L / 2, 0.5 * (ymin + ymax), 0.0])
    span = (L + 1.2) / W
    H = int(math.ceil((ymax - ymin + 1.2) / span))
    H = min(H, 900)
    im = preview.render(mm, P, mm['textures'], (90, 0), W, H, liv, zoom=(c, span))
    d = ImageDraw.Draw(im)
    T = A['types'][typ]; f = T['fit']; sc = f['s'] if f else 1.0
    rows = windows.type_rows(typ, A)
    env = common.Envelope(P, mm['idx'], mm['zone'], L)
    info = []
    for r in rows:
        for s in r['s']:
            sm = s / sc                                  # model units of the stretched model
            top, bot, _ = env.at(sm)
            info.append((sm, top, bot, r['deck']))
    def px(s_, y_):
        # preview.render view (90, 0): camera on the port side looking to +z, screen right = -x (nose on the left)
        Q0 = -((-s_) - c[0])
        return W / 2 + Q0 / span, H / 2 - (y_ - c[1]) / span
    for sm, top, bot, deck in info:
        x, yt = px(sm, top + 0.25); _, yb = px(sm, bot - 0.25)
        col = (220, 0, 0) if deck == 0 else (0, 120, 255)
        d.line([x, yt - 18, x, yt], fill=col, width=2); d.line([x, yb, x, yb + 18], fill=col, width=2)
    label = f'{model} as {typ}: ' + (f'{b} texture' if b else 'model atlas') + ' | ' + (
        '; '.join(f"deck {r['deck']}: {len(r['s'])} windows, pitch {r['pitch']:.3f} m" for r in rows) if rows else 'no reference row (artist glass kept)')
    d.rectangle([0, 0, 12 + 7 * len(label), 16], fill=(255, 255, 255)); d.text((6, 3), label, fill=(0, 0, 0))
    if out:
        os.makedirs(out, exist_ok=True)
        fn = os.path.join(out, f'{model}@{typ}' + (f'_{brand}' if brand else '') + '.png'); im.save(fn)
        return fn, label
    return im, label


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--models'); ap.add_argument('--types'); ap.add_argument('--brand'); ap.add_argument('--w', type=int, default=2400)
    ap.add_argument('--out', default=os.path.join(common.ROOT, 'out', 'liveries', 'windows'))
    a = ap.parse_args()
    A = common.app(); man = json.load(open(os.path.join(common.LIV, 'manifest.json')))
    models = a.models.split(',') if a.models else sorted(set(v for v in A['typeModel'].values() if v))
    for mdl in models:
        types = sorted(t for t, m in A['typeModel'].items() if m == mdl and t in A['types'])
        if a.types: types = [t for t in types if t in a.types.split(',')]
        for t in types:
            fn, label = sheet(mdl, t, man, a.brand, a.w, a.out)
            print(os.path.relpath(fn, common.ROOT), '|', label, flush=True)
