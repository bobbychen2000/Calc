"""Data files and JSON docs against the dropped geometry. Prints counts and lengths only.
usage: python3 -I rv2_data.py COMMITTABLE_LIST     (SHA3D_DIR env var optional)
Every committable .json / .js / .geojson outside the pinned extract (data/, data/meas/, docs/, refs/cache/*) is walked:
lists of >= 2 coordinate pairs become polylines, single pairs and {x, z} dicts become points. Pairs in lon / lat
(120-123 E, 30-32 N) are mapped to world metres; other pairs are read as world x / z when both lie within 8 km of the
origin; the taxigraph turn table (pairs of link ids) is skipped. For each dropped group: points within 1 / 10 / 30 m, polyline length within 10 / 30 m and parallel (30 deg),
and the share of the group's outline / line traced by data polylines within 10 / 30 m, per JSON path (keys only).
The .js files are also checked to carry the same object as their .json twin.
"""
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv2_common as C  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

REPO = os.path.abspath(os.path.join(C.ROOT, '..'))
LIST = [l.strip() for l in open(sys.argv[1]) if l.strip()]
raw = C.Raw()
feats, els, ext = C.load_pinned()
dg = [d for d in raw.dropped_geoms() if d['geom'].intersects(ext)]
G = {'prison area': unary_union([d['geom'] for d in dg if d['cls'] == 'prison']),
     'armed-police area': unary_union([d['geom'] for d in dg if d['cls'] == 'armed_police']),
     'military railway lines': unary_union([d['geom'] for d in dg if d['kind'] == 'line']),
     'police points': unary_union([d['geom'] for d in dg if d['kind'] == 'point'])}


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def to_xz(a, b):
    if 120 < a < 123 and 30 < b < 32:
        return C.F.ll_to_world(b, a)
    if 30 < a < 32 and 120 < b < 123:
        return C.F.ll_to_world(a, b)
    if abs(a) < 8000 and abs(b) < 8000:
        return (a, b)
    return None


def walk(o, path, out):
    if isinstance(o, dict):
        if num(o.get('x')) and num(o.get('z')):
            out['pts'].append((path + '.{x,z}', (o['x'], o['z'])))
        for k, v in o.items():
            walk(v, path + '.' + str(k), out)
    elif isinstance(o, list):
        if path.endswith('.turns') or '.turns.' in path:
            return      # taxigraph turn table: pairs of link ids, not coordinates
        if len(o) >= 2 and all(isinstance(p, list) and len(p) == 2 and num(p[0]) and num(p[1]) for p in o):
            xs = [to_xz(*p) for p in o]
            if all(x is not None for x in xs):
                out['lines'].append((path, xs))
                return
        if len(o) == 2 and num(o[0]) and num(o[1]):
            x = to_xz(*o)
            if x is not None:
                out['pts'].append((path, x))
            return
        for v in o:
            walk(v, path + '[]', out)


def load_any(p):
    txt = open(p, encoding='utf-8').read()
    if p.endswith('.js'):
        body = re.sub(r'^(\s*//[^\n]*\n)*', '', txt)
        i = body.index('{')
        j = body.rindex('}')
        return json.loads(body[i:j + 1])
    return json.loads(txt)


files = [f for f in LIST if f.endswith(('.json', '.js', '.geojson')) and '/osm_pinned/' not in f]
data = {}
for f in files:
    try:
        data[f] = load_any(os.path.join(REPO, f))
    except (ValueError, OSError):
        print('  (not parsed: %s)' % f)
js_same = Counter()
for f in files:
    if f.endswith('.js') and f[:-3] + '.json' in data and f in data:
        js_same['same' if data[f] == data[f[:-3] + '.json'] else 'DIFFERENT'] += 1
print('.js files vs their .json twin: %s' % dict(js_same))
pts, lines = [], []
for f, o in data.items():
    out = {'pts': [], 'lines': []}
    walk(o, os.path.basename(f), out)
    pts += [(path, Point(x)) for path, x in out['pts']]
    lines += [(path, LineString(xs)) for path, xs in out['lines'] if len(set(map(tuple, xs))) >= 2]
print('walked %d files: %d points, %d polylines' % (len(data), len(pts), len(lines)))
ptree = STRtree([g for p, g in pts])
ltree = STRtree([g for p, g in lines])


def ang(a, b):
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def parallel_len(kl, lw, band_d, step=1.0):
    near = kl.intersection(lw.buffer(band_d))
    tot = 0.0
    for p in getattr(near, 'geoms', [near]):
        if p.geom_type != 'LineString' or p.length == 0:
            continue
        n = max(1, int(math.ceil(p.length / step)))
        for i in range(n):
            a, b = p.length * i / n, p.length * (i + 1) / n
            pa, pb, m = p.interpolate(a), p.interpolate(b), p.interpolate((a + b) / 2)
            t = lw.project(m)
            q1, q2 = lw.interpolate(max(0, t - 1)), lw.interpolate(min(lw.length, t + 1))
            if ang(math.degrees(math.atan2(pb.y - pa.y, pb.x - pa.x)), math.degrees(math.atan2(q2.y - q1.y, q2.x - q1.x))) <= 30:
                tot += b - a
    return tot


for gname, U in G.items():
    lw = U.boundary if U.geom_type in ('Polygon', 'MultiPolygon') else U
    print('\n== %s' % gname)
    for D in (1, 10, 30):
        c = Counter(p for j in ptree.query(U.buffer(D)) for p, g in [pts[j]] if g.distance(U) <= D)
        print('  points within %2d m: %d %s' % (D, sum(c.values()), dict(c) if D < 30 else dict(c.most_common(8))))
    if gname == 'police points':
        c = Counter(p for j in ltree.query(U.buffer(10)) for p, g in [lines[j]] if g.distance(U) <= 10)
        print('  polylines within 10 m: %d %s' % (sum(c.values()), dict(c.most_common(8))))
        continue
    for D in (10, 30):
        c, mx = Counter(), Counter()
        for j in ltree.query(lw.buffer(D)):
            p, g = lines[j]
            L = parallel_len(g, lw, D)
            if L >= 25:
                c[p] += 1
                mx[p] = max(mx[p], L)
        print('  polylines >= 25 m parallel within %d m: %d %s; max %s' % (D, sum(c.values()), dict(c),
                                                                          {k: round(v) for k, v in mx.items()}))
    # trace
    lwx = lw.intersection(ext)
    S = []
    for part in getattr(lwx, 'geoms', [lwx]):
        if part.geom_type != 'LineString' or part.length == 0:
            continue
        n = max(1, int(part.length))
        for i in range(n):
            s = (i + 0.5) * part.length / n
            q1, q2 = part.interpolate(max(0, s - 1)), part.interpolate(min(part.length, s + 1))
            S.append((part.interpolate(s), math.degrees(math.atan2(q2.y - q1.y, q2.x - q1.x)), part.length / n))
    tot = sum(w for p, d, w in S)
    for D in (10, 30):
        cov = Counter()
        anyc = 0.0
        for p, d, w in S:
            hit = set()
            for j in ltree.query(p.buffer(D)):
                path, g = lines[j]
                if g.distance(p) > D:
                    continue
                t = g.project(p)
                q1, q2 = g.interpolate(max(0, t - 1)), g.interpolate(min(g.length, t + 1))
                if ang(math.degrees(math.atan2(q2.y - q1.y, q2.x - q1.x)), d) <= 30:
                    hit.add(path)
            for h in hit:
                cov[h] += w
            if hit:
                anyc += w
        print('  traced by data polylines within %d m: %.1f %% of %.0f m; by path %s' % (
            D, 100 * anyc / tot if tot else 0, tot, {k: '%.1f %%' % (100 * v / tot) for k, v in cov.most_common(6)}))
