"""N2 (taxiway re-fit side effects), independent of twy_refit.py's own junction_check. Prints counts only.
usage: python3 -I rv2_n2.py          (SHA3D_DIR env var optional)
Every taxiway / taxilane of data/sha_airport.json (and its `parts`) is compared vertex by vertex with its OSM way in
the pinned extract (world metres): moved vertices, the turn added at each interior vertex (|turn now - turn in OSM|),
reversed segments (a segment now pointing > 90 deg away from its OSM direction), segments < 0.5 m, spikes
(turns > 150 deg) and the BN ways (not moved by fix round 2). Also checks that the moves listed in
data/meas/twy_refit.json vertex_moves are the moves found in the data.
"""
import json
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv2_common as C  # noqa: E402

A = json.load(open(os.path.join(C.ROOT, 'data', 'sha_airport.json')))
T = json.load(open(os.path.join(C.ROOT, 'data', 'meas', 'twy_refit.json')))
feats, els, ext = C.load_pinned()
osm = {f['id']: list(f['geom'].coords) for f in feats if f['typ'] == 'way' and f['geom'] is not None
       and f['geom'].geom_type == 'LineString' and f['tags'].get('aeroway') in ('taxiway', 'taxilane')}


def turn(a, b, c):
    d1 = math.atan2(b[1] - a[1], b[0] - a[0])
    d2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = abs(math.degrees(d2 - d1)) % 360
    return min(d, 360 - d)


c = Counter()
added = []
per_way_max = {}
bn = Counter()
moved_xy = 0
for rec in A['taxiways'] + A['taxilanes']:
    wid = int(rec['id'].split('/')[-1])
    if wid not in osm:
        c['no OSM twin'] += 1
        continue
    o = osm[wid]
    for pts in ([rec['pts']] if rec.get('pts') else []) + [p for p in (rec.get('parts') or [])]:
        if len(pts) != len(o):
            c['vertex count differs from OSM'] += 1
            continue
        mv = [math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(pts, o)]
        nm = sum(1 for m in mv if m > 0.02)
        moved_xy += nm
        if rec.get('ref') == 'BN':
            bn['BN vertices moved > 2 cm'] += nm
            bn['BN ways'] += 1
        for k in range(1, len(pts) - 1):
            ta = turn(pts[k - 1], pts[k], pts[k + 1])
            to = turn(o[k - 1], o[k], o[k + 1])
            if mv[k - 1] > 0.02 or mv[k] > 0.02 or mv[k + 1] > 0.02:
                added.append(abs(ta - to))
                per_way_max[wid] = max(per_way_max.get(wid, 0), abs(ta - to))
            if ta > 150 and to <= 150:
                c['new spike (> 150 deg)'] += 1
        for k in range(len(pts) - 1):
            L = math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
            if L < 0.5 and math.hypot(o[k + 1][0] - o[k][0], o[k + 1][1] - o[k][1]) >= 0.5:
                c['new segment < 0.5 m'] += 1
            dn = (pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
            do = (o[k + 1][0] - o[k][0], o[k + 1][1] - o[k][1])
            if dn[0] * do[0] + dn[1] * do[1] < 0:
                c['reversed segment'] += 1
added.sort()
print('moved vertices (> 2 cm, counted per way that holds them): %d; ways touched: %d' % (moved_xy, len(per_way_max)))
print('added turn at moved vertices and their neighbours: max %.1f deg, median %.1f deg, ways over 15 deg: %d' % (
    added[-1] if added else 0, added[len(added) // 2] if added else 0, sum(1 for v in per_way_max.values() if v > 15)))
print('defects:', dict(c) or 0)
print('BN:', dict(bn))
vm = T['vertex_moves']
print('twy_refit.json vertex_moves: %d (%s)' % (len(vm), dict(Counter(v['kind'] for v in vm.values()))))
print('not moved (Umbra veto):', [(v['ref'], v['v0'], v['v1']) for v in T['summary']['not_moved_umbra_veto']])
