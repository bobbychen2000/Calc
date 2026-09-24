#!/usr/bin/env python3
"""Reproduce the NAIP 2024 lighting observations in docs/research/airfield_lighting.md (research tool, read-only).

- Resamples the public-domain NAIP 2024 world grid (refs/cache/naip/naip_2024_world_0.5m_bgr.npy, see
  docs/research/imagery.md) in a runway-aligned frame: along = ft/metres from the NASR landing threshold (+ into the
  runway), lateral + = LEFT of the landing direction.
- Fits the 4 PAPI lamp housings per end (orange blobs, 30-ft pitch) -> PAPI_OBS in tools/env/build_lighting_spec.py.
- Writes crops of the approach-light piers (28R, 28L, 19L, 19R) for the visual crossmember reading (ALS_PIERS_OBS).
- Optionally overlays tools/env/lighting_fixtures.json on NAIP for QA (--qa).
Outputs go to refs/cache/lighting/naip/ (gitignored).  Run: python3 tools/env/lighting_naip_measure.py [--qa]
"""
import csv, json, math, os, sys
import numpy as np
import cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

FT = 0.3048
OUT = os.path.join(ROOT, 'refs', 'cache', 'lighting', 'naip')
META = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
IMG = np.load(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r')
ENDS = {r['RWY_END_ID'].lstrip('0'): r for r in csv.DictReader(open(os.path.join(ROOT, 'refs', 'cache', 'xcheck', 'faa', 'APT_RWY_END.csv'), encoding='latin-1'))
        if r['ARPT_ID'] == 'SFO'}
OPP = {'10L': '28R', '28R': '10L', '10R': '28L', '28L': '10R', '1L': '19R', '19R': '1L', '1R': '19L', '19L': '1R'}


def w(lat, lon):
    e, n = GF.ll_to_en(lat, lon); return np.array([e, -n])


def frame(end):
    r = ENDS[end]; o = ENDS[OPP[end]]
    A = w(float(r['LAT_DECIMAL']), float(r['LONG_DECIMAL'])); B = w(float(o['LAT_DECIMAL']), float(o['LONG_DECIMAL']))
    u = (B - A) / np.linalg.norm(B - A); left = np.array([u[1], -u[0]])
    T = w(float(r['LAT_DISPLACED_THR_DECIMAL']), float(r['LONG_DISPLACED_THR_DECIMAL'])) if r['LAT_DISPLACED_THR_DECIMAL'].strip() else A
    return T, u, left


def render(end, a0, a1, c0, c1, res, ticks=True):
    """rows: along a0 (top) .. a1 (bottom) metres from the landing threshold; cols: lateral c1 (left edge) .. c0."""
    T, u, left = frame(end)
    H = int((a1 - a0) / res); W = int((c1 - c0) / res)
    aa = a0 + (np.arange(H) + 0.5) * res; cc = c1 - (np.arange(W) + 0.5) * res
    AA, CC = np.meshgrid(aa, cc, indexing='ij')
    X = T[0] + AA * u[0] + CC * left[0]; Z = T[1] + AA * u[1] + CC * left[1]
    col = ((X - META['x0']) / META['res'] - 0.5).astype(np.float32); row = ((Z - META['z0']) / META['res'] - 0.5).astype(np.float32)
    r0 = int(max(0, row.min() - 2)); r1 = int(min(IMG.shape[0], row.max() + 3)); q0 = int(max(0, col.min() - 2)); q1 = int(min(IMG.shape[1], col.max() + 3))
    o = cv2.remap(np.ascontiguousarray(IMG[r0:r1, q0:q1]), col - q0, row - r0, cv2.INTER_LINEAR, borderValue=(40, 40, 40))
    if ticks:
        for ft in range(int(a0 / FT / 100) * 100, int(a1 / FT) + 1, 100):
            y = int((ft * FT - a0) / res)
            if 0 <= y < H:
                cv2.line(o, (0, y), (18 if ft % 500 == 0 else 8, y), (0, 255, 255), 1)
                if ft % 500 == 0:
                    cv2.putText(o, str(ft), (20, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    return o


def papi_fit(end, guess_ft):
    a0 = guess_ft * FT - 25; a1 = guess_ft * FT + 25; c0, c1, res = 25, 95, 0.125
    im = render(end, a0, a1, c0, c1, res, ticks=False).astype(int)
    B, G, R = im[..., 0], im[..., 1], im[..., 2]
    m = ((R - G) > 15) & ((R - B) > 30) & (R > 110)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    pts = [((a0 + (cy + 0.5) * res) / FT, (c1 - (cx + 0.5) * res) / FT) for i, (cx, cy) in enumerate(cen) if i and 6 <= st[i, 4] <= 400]
    best = (0, None, [])
    for p in pts:
        row = [q for q in pts if abs(q[0] - p[0]) < 4]
        for base in [q[1] for q in row]:
            hits = [min(row, key=lambda q: abs(q[1] - (base + k * 30))) for k in range(4)]
            ok = [(h, abs(h[1] - (base + k * 30)) < 4) for k, h in enumerate(hits)]
            good = [h for h, g in ok if g]
            if len(good) > best[0]:
                best = (len(good), round(float(np.mean([h[0] for h in good]))), [round(h[1]) for h in good])
    return best


def main():
    os.makedirs(OUT, exist_ok=True)
    guess = {'10L': 1550, '10R': 1297, '19L': 1343, '19R': 1023, '28L': 1368, '28R': 1368}   # from a first coarse look
    res = {}
    for e, g in guess.items():
        hits, along, lat = papi_fit(e, g)
        res[e] = dict(hits=hits, along_ft=along, lateral_ft=lat)
        print('PAPI', e, res[e])
    json.dump(res, open(os.path.join(OUT, 'papi_fit.json'), 'w'), indent=1)
    strip = np.hstack([np.pad(render(e, 280, 520, 25, 85, 0.25), ((0, 0), (0, 4), (0, 0)), constant_values=255) for e in guess])
    cv2.imwrite(os.path.join(OUT, 'papi_sites.png'), strip)
    for e in ('28R', '28L'):
        cv2.imwrite(os.path.join(OUT, f'als_{e}.png'), render(e, -800, 150, -90, 90, 0.5))
        cv2.imwrite(os.path.join(OUT, f'zoom_{e}.png'), render(e, -450, -170, -30, 30, 0.25))
        cv2.imwrite(os.path.join(OUT, f'end_{e}.png'), render(e, -930, -680, -30, 30, 0.25))
    cv2.imwrite(os.path.join(OUT, 'als_19L.png'), render('19L', -520, 60, -45, 45, 0.5))
    cv2.imwrite(os.path.join(OUT, 'als_19R.png'), render('19R', -300, 60, -45, 45, 0.5))
    if '--qa' in sys.argv:
        qa()


def qa():
    fx = json.load(open(os.path.join(ROOT, 'tools', 'env', 'lighting_fixtures.json')))
    C = {'W': (255, 255, 255), 'Y': (0, 200, 255), 'G': (0, 255, 0), 'R': (0, 0, 255), 'B': (255, 120, 0), '-': (80, 80, 80)}
    for name, (x0, z0, x1, z1, r) in {'qa_east': (1150, 300, 2245, 1100, 1.0), 'qa_19': (300, -1400, 1000, -600, 0.8)}.items():
        c0 = int((x0 - META['x0']) / 0.5); r0 = int((z0 - META['z0']) / 0.5); c1 = int((x1 - META['x0']) / 0.5); r1 = int((z1 - META['z0']) / 0.5)
        sub = cv2.resize(np.ascontiguousarray(IMG[r0:r1, c0:c1]), None, fx=0.5 / r, fy=0.5 / r, interpolation=cv2.INTER_AREA)
        sub = (sub * 0.6).astype(np.uint8)
        for g in fx['groups']:
            s = g['system']
            for p in g['pts']:
                if not (x0 <= p[0] <= x1 and z0 <= p[1] <= z1):
                    continue
                col = C[p[3]] if s in ('runway_edge', 'runway_centreline') else (255, 0, 255) if s == 'papi' else C['R'] if s in ('als_side_row', 'runway_end', 'rwsl_thl') \
                    else C['G'] if s in ('als_threshold_bar', 'threshold_wingbar', 'threshold_end') else (255, 255, 0) if s == 'als_flasher' else C['W']
                cv2.circle(sub, (int((p[0] - x0) / r), int((p[1] - z0) / r)), 3 if s == 'papi' else 2, col, -1)
        cv2.imwrite(os.path.join(OUT, name + '.png'), sub)
    print('QA overlays written to', OUT)


if __name__ == '__main__':
    main()
