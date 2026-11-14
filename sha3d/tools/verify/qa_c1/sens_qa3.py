import sys, json, glob
sys.path.insert(0, '/home/user/Calc/sha3d/tools/law'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import osm_sensitive as S, frame as F
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, LineString, shape, Point
RAW = '/home/user/Calc/sha3d/refs/cache/osm_pinned_raw/20261114'
nodes = {}; ways = {}; wt = {}
for fn in sorted(glob.glob(RAW + '/*.osm')):
    for el in ET.parse(fn).getroot():
        if el.tag == 'node': nodes[el.get('id')] = (float(el.get('lat')), float(el.get('lon')))
        elif el.tag == 'way':
            ways[el.get('id')] = [n.get('ref') for n in el.findall('nd')]; wt[el.get('id')] = {x.get('k'): x.get('v') for x in el.findall('tag')}
gj = json.load(open('/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson'))
kept = []
for f in gj['features']:
    if f.get('geometry'):
        g = shape(f['geometry']); kept.append((f['properties'].get('tags', {}), g))
for w, t in wt.items():
    r = S.sensitive_reason(t)
    if not r: continue
    nds = ways[w]; closed = nds[0] == nds[-1]
    ll = [(nodes[n][1], nodes[n][0]) for n in nds if n in nodes]
    g = Polygon(ll) if closed and len(ll) >= 4 else LineString(ll)
    keys = sorted(k for k in t if not k.startswith('name') and k not in ('source',))
    gb = g if closed else g
    inter = []
    for tg, kg in kept:
        if closed and kg.intersects(g) and not kg.within(g):
            inter.append(next((k for k in ('highway','building','landuse','waterway','railway','aeroway','barrier','leisure','amenity') if k in tg), 'other'))
        elif closed and kg.within(g):
            inter.append('WITHIN:' + next((k for k in ('highway','building','landuse','waterway','railway','aeroway','barrier') if k in tg), 'other'))
    from collections import Counter
    # area in m2 via frame
    xz = [F.ll_to_world(la, lo) for lo, la in ll]
    area = Polygon(xz).area if closed and len(xz) >= 4 else 0
    print(r, 'closed', closed, 'nodes', len(nds), 'area_m2', round(area), 'tag keys', keys, 'kept features intersecting:', dict(Counter(inter)))
print('--- detail of intersecting kept features (local; no ids printed)')
from shapely.ops import transform
def toxz(g):
    return transform(lambda lo, la, z=None: tuple(zip(*[F.ll_to_world(a, b) for a, b in zip(la if hasattr(la,'__iter__') else [la], lo if hasattr(lo,'__iter__') else [lo])])), g)
for w, t in wt.items():
    r = S.sensitive_reason(t)
    if r not in ('armed_police', 'prison'): continue
    nds = ways[w]; ll = [(nodes[n][1], nodes[n][0]) for n in nds]
    g = Polygon(ll)
    gx = toxz(g)
    for tg, kg in kept:
        if kg.intersects(g):
            kx = toxz(kg)
            key = {k: tg[k] for k in ('highway','building','landuse','waterway','railway','aeroway','barrier','leisure','amenity','natural','service') if k in tg}
            if kx.geom_type in ('LineString','MultiLineString'):
                L = kx.length; inside = kx.intersection(gx).length; near_edge = kx.intersection(gx.exterior.buffer(5)).length
                print(r, key, 'len', round(L), 'inside', round(inside), 'within 5 m of the dropped outline', round(near_edge))
            else:
                print(r, key, kx.geom_type, 'area', round(kx.area), 'overlap', round(kx.intersection(gx).area), 'dropped area', round(gx.area),
                      'boundary-near-length', round(kx.exterior.intersection(gx.exterior.buffer(5)).length) if hasattr(kx,'exterior') else '')
