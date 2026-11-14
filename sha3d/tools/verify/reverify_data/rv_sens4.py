import sys, os, json
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_sens.py')).read().split('# 2. ids in osm_elements.json')[0])
import numpy as np
G = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
def to_xz(g): return shapely.transform(g, lambda c: [xz(la, lo) for lo, la in c])
for f in G['features']:
    t = f['properties'].get('tags', {})
    if t.get('railway') != 'rail': continue
    kg = to_xz(shape(f['geometry']))
    for r, g in lines:
        if kg.intersection(g.buffer(10)).length >= 25:
            d = [g.distance(Point(p)) for p in np.array(kg.interpolate(np.linspace(0, kg.length, 60)).tolist() if False else [kg.interpolate(s).coords[0] for s in np.linspace(0, kg.length, 60)])]
            print('kept railway way vs dropped line: distance percentiles (m) p10 %.1f p50 %.1f p90 %.1f; kept length %.0f; dropped line length %.0f'
                  % (np.percentile(d, 10), np.percentile(d, 50), np.percentile(d, 90), kg.length, g.length))
# railway points on the dropped lines: how many are vertices shared with other kept ways
