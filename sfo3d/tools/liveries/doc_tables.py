#!/usr/bin/env python3
"""Markdown tables for docs/research/liveries_impl.md from the current data (so the document states what the files hold):
  --brands   §6 per-brand status (bakes from data/liveries/manifest.json, colour provenance and reference hosts from
             tools/liveries/liveries.py)
  --windows  §8.3 per-model window decision (tools/liveries/windows.py) and what the atlas removed (head.atlas.windows)
  --atlas    §2 atlas table (head.atlas of data/models/*.sfom)
Usage: python3 tools/liveries/doc_tables.py --brands | --windows | --atlas
"""
import collections, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def prov(cols):
    c = collections.Counter()
    for k, v in cols.items():
        p = str(v[1]) if isinstance(v, (tuple, list)) and len(v) > 1 else '?'
        if 'third-party' in p or 'Norebbo' in p or 'chart' in p: c['third-party'] += 1
        elif p.startswith('official'): c['official'] += 1
        elif p.startswith('measured on the photo'): c['photo'] += 1
        elif p.startswith('measured'): c['measured'] += 1
        else: c['approx'] += 1
    return ', '.join(f'{k} {n}' for k, n in c.items())


def short(u):
    if u.startswith('photo check'): return 'Wikimedia Commons photos'
    m = re.match(r'https?://([^/ ]+)', u)
    return m.group(1).replace('www.', '') if m else ('FlightGear texture (GPL-2.0)' if 'FlightGear' in u else 'note: ' + ' '.join(u.split()[:6]))


def brands():
    import liveries
    man = json.load(open(os.path.join(common.LIV, 'manifest.json')))
    baked = collections.defaultdict(list)
    for e in man['entries']:
        for v in [e] + e.get('variants', []):
            baked[e['brand']].append(os.path.basename(v['files']['hi']).replace('-hi.webp', ''))
    out = ['| Code | Brand | Livery | Baked textures | Colours | Refs | Status / known simplifications |', '|---|---|---|---|---|---|---|']
    for code, L in liveries.LIVERIES.items():
        b = baked.get(code, [])
        out.append(f"| {code} | {L['name']} | {L['version']} | {', '.join(sorted(b)) or '- (procedural airframe only)'} | {prov(L.get('colors', {}))} | "
                   f"{'; '.join(sorted(set(short(r) for r in L['refs'])))} | {L.get('status', '')} |")
    return '\n'.join(out)


def windows_table():
    import windows, sfom
    A = common.app()
    out = ['| Model | Artist windows | Decision | Reason | Removed by the atlas (per model, both sides) |', '|---|---|---|---|---|']
    for k in sorted(A['base']):
        a = windows.artist(k); d = windows.decision(k, A)
        g = len([x for x in a['glass'] if x['side'] < 0]); h = len([x for x in a['holes'] if x['side'] < 0]); t = len([x for x in a['texture'] if x['side'] < 0])
        desc = (f'{g} glass objects per side' + (f' over {h} openings' if h else '')) if a['kind'] == 'geometry' else \
               (f'{h} openings in the skin' if a['kind'] == 'holes' else (f'{t} painted in the source texture' if a['kind'] == 'texture' else 'none'))
        r = sfom.load(os.path.join(common.MD, k + '.sfom'), textures=False)['head']['atlas']['windows']['removed']
        rem = ', '.join([f'{n} {r[n]}' for n in ('glass', 'holes', 'strip') if r.get(n)] + (['painted texture windows dropped from the kept skin'] if r.get('texture') else []))
        out.append(f"| {k} | {desc} | {d['mode']} | {d['why']} | {rem or '-'} |")
    return '\n'.join(out)


def atlas():
    import sfom
    A = common.app()
    out = ['| Model | px/m at 2048 | Fuselage cm/px (2048 / 1024) | Charts | Engines found | Cabin windows | Plug bands (m, model; longest plug) |', '|---|---|---|---|---|---|---|']
    for k in sorted(A['base']):
        h = sfom.load(os.path.join(common.MD, k + '.sfom'), textures=False)['head']; a = h['atlas']
        pxm = a['kpm'] * 2048 / a['size']
        w = a['windows']; bands = ', '.join(f"{b['s']:.2f} ({b['dmax']:.2f})" for b in a['bands']) or '-'
        win = f"{w['mode']}: {w['painted']} painted" + (f", {w['removed']['glass']} glass / {w['removed']['holes']} openings removed" if (w['removed']['glass'] or w['removed']['holes']) else '')
        out.append(f"| {k} ({h.get('name', k)}) | {pxm:.1f} | {100 / pxm:.1f} / {200 / pxm:.1f} | {len(a['charts'])} | {len(a['eng'])} | {win} | {bands} |")
    return '\n'.join(out)


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else '--brands'
    print({'--brands': brands, '--windows': windows_table, '--atlas': atlas}[arg]())
