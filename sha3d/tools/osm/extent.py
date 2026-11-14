"""Detailed extent of SHA Live 3D (PLAN s.6b, Q3 default): convex hull of OSM aerodrome relation 21913346 + 1 km.

usage: python3 -I extent.py RELATION_FULL.osm [OUT.json]
Library: extent_from_relation(path) -> dict(polygon_xz (shapely, world metres), ring_ll, area_km2, bbox_ll, ...).
The hull is taken in the world frame (tools/common/frame.py), buffered by 1000 m with round joins (64 segments per
quarter circle), and mapped back to WGS 84 vertex by vertex.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'common'))
import frame as F  # noqa: E402
from shapely.geometry import MultiPoint, Polygon  # noqa: E402

BUFFER_M = 1000.0
QUAD_SEGS = 64


def extent_from_relation(path, rel_id='21913346'):
    root = ET.parse(path).getroot()
    nodes = {n.get('id'): (float(n.get('lat')), float(n.get('lon'))) for n in root.iter('node')}
    ways = {w.get('id'): [nd.get('ref') for nd in w.findall('nd')] for w in root.iter('way')}
    rel = next(r for r in root.iter('relation') if r.get('id') == rel_id)
    tags = {t.get('k'): t.get('v') for t in rel.findall('tag')}
    pts = []
    members = []
    for m in rel.findall('member'):
        if m.get('type') == 'way' and m.get('role') in ('outer', ''):
            members.append(m.get('ref'))
            pts += [F.ll_to_world(*nodes[r]) for r in ways[m.get('ref')]]
    hull = MultiPoint(pts).convex_hull
    poly = hull.buffer(BUFFER_M, quad_segs=QUAD_SEGS)
    ring_xz = list(poly.exterior.coords)[:-1]
    ring_ll = [F.world_to_ll(x, z) for x, z in ring_xz]
    lats = [p[0] for p in ring_ll]; lons = [p[1] for p in ring_ll]
    return dict(relation=rel_id, relation_version=int(rel.get('version')), relation_timestamp=rel.get('timestamp'),
                relation_tags={k: tags[k] for k in ('aeroway', 'iata', 'icao', 'ele') if k in tags},
                outer_ways=members, hull_area_km2=hull.area / 1e6, area_km2=poly.area / 1e6,
                polygon_xz=poly, hull_xz=hull, ring_xz=ring_xz, ring_ll=ring_ll,
                bbox_ll=(min(lons), min(lats), max(lons), max(lats)))


if __name__ == '__main__':
    ex = extent_from_relation(sys.argv[1])
    summ = {k: v for k, v in ex.items() if k not in ('polygon_xz', 'hull_xz', 'ring_xz', 'ring_ll')}
    print(json.dumps(summ, indent=1))
    if len(sys.argv) > 2:
        json.dump(dict(summ, ring_ll=[[round(a, 7), round(b, 7)] for a, b in ex['ring_ll']],
                       ring_xz=[[round(x, 2), round(z, 2)] for x, z in ex['ring_xz']]), open(sys.argv[2], 'w'))
