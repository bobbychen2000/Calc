"""Plates for task A2: stands over Sentinel-2 / Umbra, the taxi graph, and the Sentinel-2 parked-aircraft evidence.

usage: python3 -I sha3d/tools/airport/stands_plates.py SHA3D_DIR
Writes docs/phase1/stands_overlay.jpg, docs/phase1/taxigraph.png, docs/phase1/stands_s2_evidence.png.
Imagery: Copernicus Sentinel-2 L2A (S2B 2026-10-14 TCI; the 2023-2026 stack), Umbra SAR Open Data 2024-06-02 (CC BY
4.0, full-resolution windows, registration shift removed); data (c) OpenStreetMap contributors (ODbL).
"""
import json
import math
import os
import sys

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from scipy.ndimage import map_coordinates, uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
from acplan import class_planform, TEMPLATES, planform  # noqa: E402
from sarwin import SarWindows  # noqa: E402
from stand_geom import from_local  # noqa: E402

ROOT = sys.argv[1]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
A = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
ST = json.load(open(os.path.join(ROOT, 'data/sha_stands.json')))
G = json.load(open(os.path.join(ROOT, 'data/sha_taxigraph.json')))
CCOL = {'B': (120, 220, 255), 'C': (90, 255, 120), 'CL': (200, 255, 90), 'D': (255, 230, 60), 'E': (255, 150, 40),
        'EL': (255, 70, 70), 'F': (255, 60, 220)}
INV = Transformer.from_pipeline(
    f'+proj=pipeline +step +inv +proj=topocentric +ellps=WGS84 +lat_0={F.ORIGIN_LAT} +lon_0={F.ORIGIN_LON} +h_0=0 '
    f'+step +inv +proj=cart +ellps=WGS84')


def s2_image(x0, z0, x1, z1, res):
    ds = rasterio.open(os.path.join(ROOT, 'refs/cache/s2/S2B_51RUQ_20261014_0_L2A/TCI.tif'))
    a = ds.read().astype(float); T = ds.transform
    tr = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True)
    xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
    X, Z = np.meshgrid(xs, zs)
    lon, lat, _ = INV.transform(X, -Z, np.zeros_like(X))
    E, N = tr.transform(lon, lat)
    E = E + 3.09; N = N + 1.00          # OSM registration -> S2 registration (OSM - S2 = (-3.09, -1.00) m)
    col = (E - T.c) / T.a - 0.5; row = (N - T.f) / T.e - 0.5
    rgb = np.stack([map_coordinates(a[k], [row, col], order=1, mode='nearest') for k in range(3)], -1)
    rgb = np.clip((rgb - 30) * 1.15, 0, 255) * 0.85
    return Image.fromarray(rgb.astype(np.uint8))


SAR = None


def sar_image(x0, z0, x1, z1, res):
    global SAR
    if SAR is None:
        SAR = SarWindows(ROOT, (3.4, 0.0))
    g = SAR.grid(x0, z0, x1, z1, res)
    g = np.sqrt(uniform_filter(np.nan_to_num(g) ** 2, 3))
    v = np.clip((np.log1p(g) - 2.2) / 3.0, 0, 1) ** 1.1 * 210
    return Image.fromarray(v.astype(np.uint8)).convert('RGB')


def label(img, txt, xy=(6, 6), size=16):
    d = ImageDraw.Draw(img, 'RGBA'); f = ImageFont.truetype(FONTB, size)
    bb = d.textbbox(xy, txt, font=f)
    d.rectangle([bb[0] - 4, bb[1] - 3, bb[2] + 4, bb[3] + 3], fill=(0, 0, 0, 180))
    d.text(xy, txt, font=f, fill=(255, 255, 255))


def scalebar(img, res, metres, xy):
    d = ImageDraw.Draw(img, 'RGBA'); f = ImageFont.truetype(FONT, 13)
    L = metres / res; x, y = xy
    d.rectangle([x - 4, y - 18, x + L + 4, y + 8], fill=(0, 0, 0, 160))
    d.line([x, y, x + L, y], fill=(255, 255, 255), width=3)
    d.text((x, y - 17), f'{metres:g} m', font=f, fill=(255, 255, 255))


def draw_stands(img, x0, z0, res, names=True, bridges=True, fsize=12):
    d = ImageDraw.Draw(img, 'RGBA'); f = ImageFont.truetype(FONTB, fsize)
    P = lambda p: ((p[0] - x0) / res, (p[1] - z0) / res)  # noqa: E731
    for s in ST['stands']:
        col = CCOL[s['cls']]
        for poly in class_planform(s['cls']):
            pts = [P(from_local(u, v, s['nose'], s['hdg'])) for u, v in poly]
            d.polygon(pts, outline=col + (255,), fill=col + (40,))
        if s['leadin']:
            d.line([P(p) for p in s['leadin']], fill=(80, 160, 255, 150), width=1)
        nx, nz = P(s['nose']); k = max(2, 2.5 / res)
        d.ellipse([nx - k, nz - k, nx + k, nz + k], fill=(255, 255, 255, 255))
        if bridges:
            for b in s['bridges']:
                bc = (255, 0, 255, 255) if b['src'] == 'obs' else (200, 120, 255, 200)
                if b['walk']:
                    d.line([P(p) for p in b['walk']], fill=(255, 255, 255, 230), width=max(1, int(2 / res)))
                d.line([P(b['rotunda']), P(b['cab'])], fill=bc, width=max(1, int(3 / res)))
                rx, rz = P(b['rotunda']); k2 = max(2, 2.5 / res)
                d.ellipse([rx - k2, rz - k2, rx + k2, rz + k2], outline=bc, width=2)
        if names:
            h = math.radians(s['hdg'])
            tx, tz = P((s['nose'][0] + 7 * math.sin(h), s['nose'][1] - 7 * math.cos(h)))
            txt = '%s %s' % (s['name'], s['cls'])
            bb = d.textbbox((tx, tz), txt, font=f)
            dx, dz = (bb[2] - bb[0]) / 2, (bb[3] - bb[1]) / 2
            d.rectangle([tx - dx - 2, tz - dz - 1, tx + dx + 2, tz + dz + 2], fill=(0, 0, 0, 150))
            d.text((tx - dx, tz - dz), txt, font=f, fill=col + (255,))
    for p in ST['positions']:
        px, pz = P((p['x'], p['z'])); k = max(3, 3 / res)
        d.rectangle([px - k, pz - k, px + k, pz + k], outline=(255, 255, 255, 255), width=2)


def legend(img, xy, items, title=None):
    d = ImageDraw.Draw(img, 'RGBA'); f = ImageFont.truetype(FONT, 14); fb = ImageFont.truetype(FONTB, 14)
    x, y = xy; w = 330; h = 22 * len(items) + (26 if title else 8)
    d.rectangle([x, y, x + w, y + h], fill=(0, 0, 0, 190))
    yy = y + 6
    if title:
        d.text((x + 8, yy), title, font=fb, fill=(255, 255, 255)); yy += 22
    for col, txt in items:
        d.rectangle([x + 8, yy + 3, x + 26, yy + 15], fill=col)
        d.text((x + 34, yy), txt, font=f, fill=(255, 255, 255)); yy += 22


def stands_overlay(out):
    # overview over S2 (all stand areas), zooms over Umbra
    x0, z0, x1, z1 = -1330, -1620, 930, 1720
    res = (z1 - z0) / 1900
    ov = s2_image(x0, z0, x1, z1, res)
    draw_stands(ov, x0, z0, res, names=False, bridges=False)
    d = ImageDraw.Draw(ov, 'RGBA')
    for r in A['runways']:
        d.line([((p[0] - x0) / res, (p[1] - z0) / res) for p in r['centreline']['pts']], fill=(255, 255, 255, 120), width=1)
    label(ov, 'ZSSS stands (164 OSM refs) over Sentinel-2 2026-10-14, north up; planform = class reference aircraft', size=16)
    scalebar(ov, res, 500, (20, ov.height - 22))
    legend(ov, (12, 40), [(CCOL[c] + (255,), '%s  %s' % (c, t)) for c, t in
                          (('B', 'span <= 28.5 m (C909, business)'), ('C', '<= 36.5 (A320 / 737 / C919)'),
                           ('CL', '<= 41.1 (757-300 w/l)'), ('D', '<= 52 (767-300ER)'), ('E', '<= 61 (A330 / 787)'),
                           ('EL', '<= 65.5 (777-300ER / A350)'), ('F', '<= 80 (747-8)'))], 'class (sfo3d)')
    zooms = [('T2 north + middle piers (Umbra SAR 2024-06-02)', (-1050, -330), 620, 640),
             ('T2 west + south piers (Umbra SAR 2024-06-02)', (-1060, 380), 620, 640),
             ('T1 west + north faces (Umbra SAR 2024-06-02)', (520, 90), 620, 640)]
    tiles = []
    for name, (cx, cz), w, h in zooms:
        r = w / 610
        zx0, zz0 = cx - w / 2, cz - h / 2
        im = sar_image(zx0, zz0, zx0 + w, zz0 + h, r)
        draw_stands(im, zx0, zz0, r, names=True, bridges=True, fsize=10)
        dd = ImageDraw.Draw(im, 'RGBA')
        for b in A['buildings']:
            dd.line([((p[0] - zx0) / r, (p[1] - zz0) / r) for p in b['ring'] + [b['ring'][0]]], fill=(0, 255, 255, 160), width=1)
        label(im, name, size=15)
        scalebar(im, r, 100, (20, im.height - 18))
        tiles.append(im)
        d.rectangle([(zx0 - x0) / res, (zz0 - z0) / res, (zx0 + w - x0) / res, (zz0 + h - z0) / res], outline=(255, 255, 255), width=2)
    W = ov.width + max(t.width for t in tiles) + 12
    H = max(ov.height, sum(t.height for t in tiles) + 8 * len(tiles)) + 70
    sheet = Image.new('RGB', (W, H), (20, 20, 20))
    sheet.paste(ov, (0, 0))
    y = 0
    for t in tiles:
        sheet.paste(t, (ov.width + 12, y)); y += t.height + 8
    dr = ImageDraw.Draw(sheet); f = ImageFont.truetype(FONT, 15)
    c = ST['counts']
    dr.text((10, H - 62), 'Bridges (zooms): white = fixed walkway (facade -> OSM gate node), magenta = movable bridge to the '
                          'L1 / L2 door of the class reference aircraft; solid magenta = seen on SAR (obs), pale = OSM gate '
                          'only (inf). White squares = OSM positions without ref.', font=f, fill=(230, 230, 230))
    dr.text((10, H - 40), 'Stands %d (contact %d, remote %d), bridges %d (%d stands with 2).  Contains modified Copernicus '
                          'Sentinel data 2026; Umbra SAR Open Data (CC BY 4.0); (c) OpenStreetMap contributors (ODbL).'
            % (c['stands'], c['contact'], c['remote'], c['bridges'], c['stands_with_2_bridges']), font=f, fill=(230, 230, 230))
    sheet.save(out, quality=88)
    print(out, sheet.size)


def taxigraph_png(out):
    x0, z0, x1, z1 = -1450, -2050, 1050, 2050
    res = (z1 - z0) / 2200
    im = s2_image(x0, z0, x1, z1, res)
    im = Image.blend(im, Image.new('RGB', im.size, (0, 0, 0)), 0.55)
    d = ImageDraw.Draw(im, 'RGBA')
    P = lambda p: ((p[0] - x0) / res, (p[1] - z0) / res)  # noqa: E731
    nodes = G['nodes']
    col = {'taxiway': (255, 220, 0, 230), 'taxilane': (255, 245, 170, 200), 'leadin': (90, 160, 255, 190),
           'runway': (255, 60, 60, 255), 'push': (255, 255, 255, 150)}
    for l in G['links']:
        c = col[l['kind']]
        if l['kind'] == 'push':
            pass
        elif l['use'] == 'arrival':
            c = (0, 255, 120, 255)
        elif l['use'] == 'departure':
            c = (255, 120, 0, 255)
        if l['status'] != 'open':
            c = (150, 150, 150, 200)
        wdt = 3 if l['kind'] == 'runway' else (2 if l['kind'] in ('taxiway',) or l['use'] != 'all' else 1)
        d.line([P(p) for p in l['pts']], fill=c, width=wdt)
        if l['dir'] == 'ab' and l['kind'] != 'push' and len(l['pts']) >= 2:
            # arrow at the middle
            pts = l['pts']; m = len(pts) // 2
            a, b = (pts[m - 1], pts[m]) if m > 0 else (pts[0], pts[1])
            ax, az = P(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)); ang = math.atan2(b[1] - a[1], b[0] - a[0])
            k = 7
            d.polygon([(ax + k * math.cos(ang), az + k * math.sin(ang)),
                       (ax + k * math.cos(ang + 2.5), az + k * math.sin(ang + 2.5)),
                       (ax + k * math.cos(ang - 2.5), az + k * math.sin(ang - 2.5))], fill=c)
    for r in G['runways']:
        for cn in r['connections']:
            if cn.get('rapid_exit_for'):
                l = G['links'][cn['link']]
                d.line([P(p) for p in l['pts']], fill=(0, 255, 255, 255), width=3)
    for n in nodes:
        if n['kind'] == 'hold':
            x, z = P((n['x'], n['z'])); d.ellipse([x - 4, z - 4, x + 4, z + 4], fill=(255, 0, 255, 255))
        elif n['kind'] == 'stand':
            x, z = P((n['x'], n['z'])); d.ellipse([x - 2, z - 2, x + 2, z + 2], fill=(255, 255, 255, 255))
        elif n['kind'] == 'rwy_end':
            x, z = P((n['x'], n['z'])); d.rectangle([x - 4, z - 4, x + 4, z + 4], outline=(255, 60, 60, 255), width=2)
    for h in G['hold_inf']:
        x, z = P((h['x'], h['z'])); d.ellipse([x - 4, z - 4, x + 4, z + 4], outline=(255, 0, 255, 255), width=2)
    fb = ImageFont.truetype(FONTB, 13)
    seen = set()
    for l in G['links']:
        if l['kind'] in ('taxiway',) and l['ref'] and l['ref'] not in seen and len(l['pts']) >= 2:
            p = l['pts'][len(l['pts']) // 2]; x, z = P(p)
            d.text((x + 3, z - 7), l['ref'], font=fb, fill=(255, 255, 255, 230)); seen.add(l['ref'])
    label(im, 'ZSSS taxi graph: %d nodes, %d links; every stand reaches both runways (arrival and departure)' %
          (G['counts']['nodes'], G['counts']['links']), size=16)
    legend(im, (12, 40), [((255, 220, 0, 255), 'taxiway (OSM)'), ((255, 245, 170, 255), 'apron taxilane (OSM)'),
                          ((90, 160, 255, 255), 'stand lead-in (OSM)'), ((255, 255, 255, 200), 'push-back link (inf)'),
                          ((0, 255, 120, 255), 'arrival only (AIP: Y1-Y3, ROUTE N/S)'),
                          ((255, 120, 0, 255), 'departure only (AIP: M1-M6, L11-L17)'),
                          ((0, 255, 255, 255), 'rapid exit (angle < 50 deg)'), ((255, 60, 60, 255), 'runway centreline'),
                          ((255, 0, 255, 255), 'hold: OSM (filled) / inferred 90 m (ring)')], 'links')
    scalebar(im, res, 500, (20, im.height - 22))
    dd = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, 13)
    dd.text((10, im.height - 50), 'Background: Contains modified Copernicus Sentinel data 2026. Data (c) OpenStreetMap '
                                  'contributors (ODbL); rules: AIP (mirror) short facts.', font=f, fill=(220, 220, 220))
    im.save(out)
    print(out, im.size)


def s2_evidence(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    S2 = json.load(open(os.path.join(ROOT, 'data/meas/stand_s2.json')))
    st = {s['name']: s for s in ST['stands']}
    fig = plt.figure(figsize=(16, 10))
    # (a) wide-body calls vs lateral spacing
    ax = fig.add_subplot(2, 3, 1)
    xs, ys, cs = [], [], []
    for n, r in S2['stands'].items():
        if n not in st or 'calls_by_class' not in r:
            continue
        nb = st[n]['cls_evidence']['neighbours']; sp = [abs(v[1]) for v in nb.values() if v]
        if not sp:
            continue
        xs.append(min(sp)); ys.append(r['wide_calls']); cs.append(st[n]['cls'] in ('D', 'E', 'EL', 'F'))
    xs, ys, cs = np.array(xs), np.array(ys), np.array(cs)
    ax.scatter(xs[~cs], ys[~cs], s=14, c='tab:green', label='our class B / C / CL')
    ax.scatter(xs[cs], ys[cs], s=14, c='tab:red', label='our class D / E / EL')
    ax.axvline(50, color='0.5', ls='--', lw=0.8); ax.axhline(1.5, color='0.5', ls=':', lw=0.8)
    ax.set_xlabel('lateral spacing to the nearest neighbour (m)'); ax.set_ylabel('dates with a wide-body fit (of ~48)')
    ax.set_title('(a) Sentinel-2 wide-body fits vs stand spacing'); ax.legend(fontsize=8)
    # (b) occupancy histogram
    ax = fig.add_subplot(2, 3, 2)
    occ = [r['occupancy'] for r in S2['stands'].values() if r.get('occupancy') is not None]
    ax.hist(occ, bins=20, color='tab:blue')
    ax.set_xlabel('fraction of dates with an aircraft fitted (10:30-10:50 local)'); ax.set_ylabel('stands')
    ax.set_title('(b) stand occupancy at the S2 overpass, %d dates' % S2['scenes_used'])
    # (c) template class histogram (all calls)
    ax = fig.add_subplot(2, 3, 3)
    from collections import Counter
    cc = Counter(c['tpl'] for r in S2['stands'].values() for c in r.get('calls', []))
    names = [t[0] for t in TEMPLATES]
    ax.bar(names, [cc.get(n, 0) for n in names], color='tab:purple')
    ax.set_title('(c) best template per aircraft fit (all stands, all dates)'); ax.set_ylabel('fits')
    # (d-f) example excess images with fitted template
    import importlib
    M = importlib.import_module('stand_s2')
    scenes = M.load_stack(ROOT); byid = {s['id'][:24]: s for s in scenes}
    ref = [s for s in scenes if s['id'] == M.REF_ID][0]
    sh = {x['id'][:24]: x['shift_px_row_col'] for x in S2['scenes'] if x['used']}
    tr = Transformer.from_crs('EPSG:4326', ref['crs'], always_xy=True)
    TP = {t[0]: t for t in TEMPLATES}
    for k, (n, want) in enumerate((('229', ('E', 'EL', 'D')), ('502', ('D', 'E')), ('275', ('C38', 'C44')))):
        s = st[n]; r = S2['stands'][n]
        calls = [c for c in r['calls'] if c['tpl'] in want] or r['calls']
        c = max(calls, key=lambda c: c['r2'])
        f_ = F.hdg_vec(s['hdg']); rr = (-f_[1], f_[0])
        UU, VV = np.meshgrid(M.U, M.V, indexing='ij')
        X = s['nose'][0] + UU * f_[0] + VV * rr[0]; Z = s['nose'][1] + UU * f_[1] + VV * rr[1]
        lat, lon = np.vectorize(F.world_to_ll)(X, Z); E0, N0 = tr.transform(lon, lat)
        E0 -= M.REF_OFF[0]; N0 -= M.REF_OFF[1]
        stack, ids = [], []
        for sid, (di, dj) in sh.items():
            sc = byid[sid]; T = sc['T']
            stack.append(map_coordinates(sc['img'], [(N0 - T.f) / T.e - 0.5 - di, (E0 - T.c) / T.a - 0.5 - dj], order=1)); ids.append(sid)
        stack = np.array(stack); bg = np.percentile(stack, 15, axis=0)
        ex = stack[ids.index(c['scene'])] - bg
        ax = fig.add_subplot(2, 3, 4 + k)
        ax.imshow(ex, extent=[M.V[0], M.V[-1], M.U[-1], M.U[0]], cmap='magma', vmin=0, vmax=0.12)
        _, L, sp, w, sw = TP[c['tpl']]
        for poly in planform(L, sp, w, sw):
            p = np.array(poly + [poly[0]]); ax.plot(p[:, 1] + c['dv'], p[:, 0] + c['du'], 'c-', lw=0.8)
        ax.set_title('(%s) stand %s, %s: template %s, R2 %.2f' % ('def'[k], n, c['scene'][11:19], c['tpl'], c['r2']), fontsize=10)
        ax.set_xlabel('m right of axis'); ax.set_ylabel('m ahead of the OSM stop')
    fig.suptitle('Parked aircraft on the stands in the Sentinel-2 L2A stack 2023-01..2026-10 (%d cloud-free dates of %d): '
                 'brightness above the per-pixel 15th percentile, planform templates blurred to 10 m. '
                 'Contains modified Copernicus Sentinel data 2023-2026.' % (S2['scenes_used'], S2['scenes_total']), fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=90)
    print(out)


if __name__ == '__main__':
    d = os.path.join(ROOT, 'docs/phase1')
    stands_overlay(os.path.join(d, 'stands_overlay.jpg'))
    taxigraph_png(os.path.join(d, 'taxigraph.png'))
    s2_evidence(os.path.join(d, 'stands_s2_evidence.png'))
