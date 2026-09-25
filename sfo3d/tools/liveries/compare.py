#!/usr/bin/env python3
"""Development helper for the livery QA: reference photographs of a brand (tools/liveries/ref_photos.py, refs/cache/livref,
reference only) stacked over quick software renders (tools/liveries/preview.py) of our bake of the same type, port and
starboard side. Writes out/liveries/compare/<BRAND>.png (not committed).

Usage: python3 tools/liveries/compare.py BRAND [BRAND ...] [--type b789] [--res mid] [--w 1000]
"""
import argparse, json, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, preview, liveries

PREF = dict(UAL='b738', DAL='b739', AAL='a321', ASA='b739', SWA='b737', JBU='a321', FFT='a20n', ACA='b38m', AMX='b38m',
            WJA='b38m', HAL='a21n', AVA='a20n', CMP='b39m', SCX='b738', MXY='bcs3', DLH='b748', VIR='b789', JAL='b789')


def pick(code, man, A, typ=None):
    ent = {e['model']: e for e in man['entries'] if e['brand'] == code}
    cands = [typ] if typ else ([PREF[code]] if code in PREF else []) + [A['icao'].get(i) for i in liveries.LIVERIES[code].get('types', [])]
    for t in cands:
        m = A['typeModel'].get(t) if t else None
        if m in ent:
            for v in [ent[m]] + ent[m].get('variants', []):
                if t in v.get('types', []): return m, t, v
    return None


def sheet(code, typ=None, res='mid', W=1000):
    A = common.app(); man = json.load(open(os.path.join(common.LIV, 'manifest.json')))
    p = pick(code, man, A, typ)
    if not p: print(code, 'no bake'); return None
    m, t, v = p
    mm, P = preview.load_for(os.path.join(common.MD, m + '.sfom'), t)
    liv = Image.open(os.path.join(common.LIV, v['files'][res]))
    rows = []
    for view in ('side', 'stbd', '34'):
        rows.append(preview.render(mm, P, mm['textures'], view, W, int(W * 0.3) if view != '34' else int(W * 0.45), liv))
    ref = os.path.join(common.ROOT, 'refs', 'cache', 'livref')
    for k in (1, 2):
        fn = os.path.join(ref, f'{code}_{k}.jpg')
        if os.path.exists(fn):
            im = Image.open(fn).convert('RGB'); rows.insert(k - 1, im.resize((W, int(im.size[1] * W / im.size[0]))))
    H = sum(r.size[1] for r in rows)
    S = Image.new('RGB', (W, H), 'white'); y = 0
    for r in rows: S.paste(r, (0, y)); y += r.size[1]
    ImageDraw.Draw(S).text((6, 6), f'{code} on {m} as {t}', fill=(255, 0, 0))
    out = os.path.join(common.ROOT, 'out', 'liveries', 'compare'); os.makedirs(out, exist_ok=True)
    fn = os.path.join(out, f'{code}.png'); S.save(fn); return fn


def mini(codes, out, res='mid', W=800):
    """compact review sheet: per brand the first reference photo and a port-side render (side by side)"""
    A = common.app(); man = json.load(open(os.path.join(common.LIV, 'manifest.json')))
    rows = []
    for code in codes:
        p = pick(code, man, A)
        if not p: continue
        m, t, v = p
        mm, P = preview.load_for(os.path.join(common.MD, m + '.sfom'), t)
        r = preview.render(mm, P, mm['textures'], 'side', W, int(W * 0.32), Image.open(os.path.join(common.LIV, v['files'][res])))
        ImageDraw.Draw(r).text((6, 6), f'{code} {m}@{t}', fill=(255, 0, 0))
        fn = os.path.join(common.ROOT, 'refs', 'cache', 'livref', f'{code}_1.jpg')
        ph = Image.open(fn).convert('RGB') if os.path.exists(fn) else Image.new('RGB', (W, int(W * 0.32)), 'white')
        ph = ph.resize((W, int(ph.size[1] * W / ph.size[0])))
        h = max(ph.size[1], r.size[1]); row = Image.new('RGB', (2 * W, h), 'white'); row.paste(ph, (0, 0)); row.paste(r, (W, 0)); rows.append(row)
    S = Image.new('RGB', (2 * W, sum(r.size[1] for r in rows)), 'white'); y = 0
    for r in rows: S.paste(r, (0, y)); y += r.size[1]
    S.save(out); return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('brands', nargs='+'); ap.add_argument('--type'); ap.add_argument('--res', default='mid')
    ap.add_argument('--w', type=int, default=1000); ap.add_argument('--mini')
    a = ap.parse_args()
    if a.mini: print(mini(a.brands, a.mini, a.res, a.w)); raise SystemExit
    for b in a.brands: print(sheet(b, a.type, a.res, a.w))
