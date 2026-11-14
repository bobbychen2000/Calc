"""Detail for the dropped lines and for kept lines along a dropped area outline (counts / lengths / tag KEYS only;
console only, local use: never copy its output into a committed file)."""
import sys, os, json
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_sens.py')).read().split('# 2. ids in osm_elements.json')[0])
G = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
def to_xz(g): return shapely.transform(g, lambda c: [xz(la, lo) for lo, la in c])
kept = [(f['properties'].get('tags', {}), to_xz(shape(f['geometry']))) for f in G['features'] if f.get('geometry')]
ext = None
for r, g in lines:
    t = None
    print('dropped %s line: length %.0f m' % (r, g.length))
    # tag keys of the dropped way (keys only)
    near_rail = [kg for tt, kg in kept if 'railway' in tt and kg.geom_type in ('LineString', 'MultiLineString')]
    u = unary_union(near_rail).buffer(10) if near_rail else None
    cov = g.intersection(u).length if u else 0
    allk = unary_union([kg.buffer(10) for tt, kg in kept if kg.geom_type in ('LineString', 'MultiLineString') and 'railway' in tt and tt.get('railway') == 'rail'])
    print('   share of its length within 10 m of kept railway=rail lines: %.0f %%' % (100 * g.intersection(allk).length / g.length))
    pts_on = [tt for tt, kg in kept if kg.geom_type == 'Point' and kg.distance(g) < 1.0]
    from collections import Counter
    print('   kept point features within 1 m of it:', dict(Counter(next((k + '=' + tt[k] for k in ('railway', 'highway', 'barrier') if k in tt), 'other') for tt in pts_on)))
    # nodes of the dropped way that are kept, and how far apart along the line
    print('   inside the extent: %.0f m' % g.length)
for w, r in drop['way'].items():
    print('dropped way class %s tag keys: %s' % (r, sorted(k for k in wtags[w] if not k.startswith('name'))))
# kept rail near the dropped lines: tag keys / values of railway, usage, service
for tt, kg in kept:
    if tt.get('railway') == 'rail':
        for r, g in lines:
            if kg.intersection(g.buffer(10)).length >= 25:
                print('kept rail near a dropped line: len %.0f, within 10 m %.0f, tags %s' % (kg.length, kg.intersection(g.buffer(10)).length,
                      {k: tt[k] for k in tt if k in ('railway', 'usage', 'service', 'electrified', 'gauge', 'operator:type')}))
# kept lines along the outline of one dropped area class
for r, g in areas:
    if r != 'prison': continue
    for tt, kg in kept:
        if kg.geom_type in ('LineString', 'MultiLineString') and kg.intersection(g.boundary.buffer(5)).length >= 10:
            print('kept line along a dropped outline (%s): len %.0f, within 5 m %.0f, tag keys %s, named %s, perimeter %.0f m' % (r, kg.length,
                  kg.intersection(g.boundary.buffer(5)).length, sorted(k for k in tt if not k.startswith('name')), any(k.startswith('name') for k in tt), g.length))
