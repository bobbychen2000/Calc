"""Data files vs dropped geometries: per file / record path, coordinate polylines within 10 m of dropped lines / outlines
(counts and lengths only)."""
import sys, os, json
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_sens.py')).read().split('# 2. ids in osm_elements.json')[0])
from collections import Counter
def walk(o, path):
    if isinstance(o, list) and len(o) >= 2 and all(isinstance(p, list) and len(p) == 2 and all(isinstance(c, (int, float)) for c in p) for p in o):
        yield path, o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + '.' + k)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v, path + '[]')
for fn in ('sha_airport.json', 'sha_stands.json', 'sha_taxigraph.json'):
    D = json.load(open(os.path.join(ROOT, 'data', fn)))
    hits = Counter()
    for path, pts_ in walk(D, ''):
        if any(abs(p[0]) > 1000 and abs(p[1]) < 200 for p in pts_[:1]) and 'lat' in path: continue
        if all(abs(p[0]) < 90 and abs(p[1]) < 200 and isinstance(p[0], float) and 20 < p[0] < 40 for p in pts_):  # lat/lon pairs
            g = LineString([xz(p[0], p[1]) for p in pts_])
        else:
            g = LineString(pts_)
        for kind, items in (('area', areas), ('line', lines)):
            for r, dg in items:
                ref = dg.boundary if kind == 'area' else dg
                l10 = g.intersection(ref.buffer(10)).length
                if l10 >= 10:
                    hits[(path, r, kind)] += round(l10)
        for r, p in pts:
            if g.distance(p) < 1.0 and False:
                hits[(path, 'police point', 'pt')] += 1
    print(fn, dict(hits) if hits else 'no data polyline runs >= 10 m within 10 m of a dropped line / outline')
