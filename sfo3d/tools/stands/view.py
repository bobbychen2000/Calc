"""Debug / verification overlays on NAIP 2024 (north up, native 0.5 m px, optionally scaled): OSM parking-position
lead-ins (yellow = ref, orange = no ref, dot = stop end), OSM jet bridges (cyan), OSM gate nodes (magenta), the
building outline (white) and optionally a stand set (data/sfo_stands.json or refs/cache/stands/stands_built.json:
red nose + heading tick + bridge attach). Outputs embed NAIP pixels and OSM geometry -> refs/cache/stands/view/ only.

Usage: python3 tools/stands/view.py NAME x0 z0 x1 z1 [scale] [--stands FILE] [--nolabels] [--plan] [--noosm]
  --plan: draw each stand's envelope of accepted types (green; alternates magenta), its fixed walkways (yellow),
          docked bridges to the largest observed type's door (orange) and rest poses (magenta); --noosm: hide OSM
"""
import json, os, sys
import cv2
import numpy as np
from common import Naip, load_osm, load_airport, hdg_vec, WORK, ROOT

OUT = os.path.join(WORK, 'view'); os.makedirs(OUT, exist_ok=True)


def render(name, x0, z0, x1, z1, scale=2.0, stands=None, labels=True, osm=None, extra=None, plan=False, noosm=False):
    N = Naip(); img, (c0, r0) = N.crop(x0, z0, x1, z1)
    img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    def P(x, z):
        c, r = N.px(x, z); return (int(round((c - c0 + 0.5) * scale - 0.5)), int(round((r - r0 + 0.5) * scale - 0.5)))
    D = load_airport()
    for poly in list(D['terminalComplex']) + [p for b in D['boardingAreas'] for p in b['polys']]:
        for ring in poly:
            cv2.polylines(img, [np.array([P(*q) for q in ring], np.int32)], True, (255, 255, 255), 1, cv2.LINE_AA)
    osm = osm or load_osm()
    fs = 0.35 * scale / 2
    if noosm: osm = {'jet_bridges': [], 'parking_positions': [], 'gates': []}
    for b in osm['jet_bridges']:
        cv2.polylines(img, [np.array([P(*q) for q in b['w']], np.int32)], False, (255, 255, 0), 1, cv2.LINE_AA)
    for p in osm['parking_positions']:
        col = (0, 255, 255) if p['ref'] else (0, 140, 255)
        pts = np.array([P(*q) for q in p['w']], np.int32)
        cv2.polylines(img, [pts], False, col, 1, cv2.LINE_AA)
        cv2.circle(img, tuple(pts[-1]), 3, col, -1)
        cv2.circle(img, tuple(pts[0]), 2, (0, 0, 0), -1)
        if labels and p['ref']:
            cv2.putText(img, p['ref'], (pts[-1][0] + 4, pts[-1][1] - 4), cv2.FONT_HERSHEY_SIMPLEX, fs, col, 1, cv2.LINE_AA)
    for g in osm['gates']:
        q = P(*g['w']); cv2.drawMarker(img, q, (255, 0, 255), cv2.MARKER_TILTED_CROSS, 6, 1)
        if labels and g.get('ref'):
            cv2.putText(img, g['ref'], (q[0] + 3, q[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, fs * 0.8, (255, 0, 255), 1, cv2.LINE_AA)
    if stands and plan:
        import geom as GM
        for s in stands['stands']:
            poly = GM.stand_env(s)                 # envelope of every type the app accepts on the stand
            geoms = getattr(poly, 'geoms', [poly])
            col = (0, 200, 0) if not s.get('alt_of') else (255, 0, 200)
            for g in geoms:
                cv2.polylines(img, [np.array([P(*q) for q in g.exterior.coords], np.int32)], True, col, 1, cv2.LINE_AA)
            t = s.get('largest_type') or 'A320'
            for b in s.get('bridges', []) + s.get('bridges_upper', []):
                pv = b.get('rotunda') or b['attach']
                cv2.polylines(img, [np.array([P(*q) for q in (b.get('walk') or [b['attach']]) + [pv]], np.int32)], False, (0, 255, 255), 2, cv2.LINE_AA)
                k = GM.dock_door(t, b['door']) if b['door'] <= 2 else None
                dp = GM.door(s['nose'], s['hdg'], t, k) if k else None
                if dp: cv2.line(img, P(*pv), P(*dp), (0, 160, 255), 2, cv2.LINE_AA)        # docked (largest type)
                if b.get('stow'): cv2.line(img, P(*pv), P(*b['stow']), (255, 0, 255), 2, cv2.LINE_AA)   # rest pose
    if stands:
        for s in stands['stands']:
            n = P(*s['nose']); f = hdg_vec(s['hdg'])
            t = P(s['nose'][0] - f[0] * 30, s['nose'][1] - f[1] * 30)
            cv2.line(img, n, t, (0, 0, 255), 1, cv2.LINE_AA); cv2.circle(img, n, 3, (0, 0, 255), -1)
            for b in s.get('bridges', []) + s.get('bridges_upper', []):
                a = P(*b['attach']); cv2.drawMarker(img, a, (0, 0, 255), cv2.MARKER_SQUARE, 6, 1)
                if b.get('rotunda'): cv2.circle(img, P(*b['rotunda']), 4, (0, 255, 0), 1)
            if labels:
                cv2.putText(img, s['name'], (n[0] - 10, n[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 255), 1, cv2.LINE_AA)
    if extra: extra(img, P)
    path = os.path.join(OUT, name + '.png'); cv2.imwrite(path, img); return path


if __name__ == '__main__':
    a = sys.argv[1:]
    st = None
    if '--stands' in a:
        i = a.index('--stands'); st = json.load(open(a[i + 1])); del a[i:i + 2]
    lab = '--nolabels' not in a; pl = '--plan' in a; no = '--noosm' in a
    a = [v for v in a if v not in ('--nolabels', '--plan', '--noosm')]
    name = a[0]; x0, z0, x1, z1 = map(float, a[1:5]); sc = float(a[5]) if len(a) > 5 else 2.0
    print(render(name, x0, z0, x1, z1, sc, st, lab, plan=pl, noosm=no))
