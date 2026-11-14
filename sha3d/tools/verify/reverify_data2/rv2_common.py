"""Shared loader for the fix-round-2 re-verify scripts (docs/phase1/reverify_data2.md).

Loads the raw OSM tiles (local only: refs/cache/osm_pinned_raw/, they still hold the sensitive features), applies the
tag rule (tools/law/osm_sensitive.py) on its own, builds the dropped geometries in world metres, and loads the
committable pinned extract. It also derives the second-order drops independently of pin_extract.py: every raw tagged
element that intersects the extent, is not dropped by the tag rule and is missing from the pinned extract.

Nothing here prints. Scripts that use it print counts only; anything that names a dropped element goes to the local
log folder LOCAL (refs/cache/reverify_data2/, git-ignored).
"""
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.environ.get('SHA3D_DIR') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'law'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
import osm_sensitive as S  # noqa: E402
import frame as F  # noqa: E402
import shapely  # noqa: E402
from shapely.geometry import LineString, Point, Polygon, shape  # noqa: E402
from shapely.ops import linemerge, polygonize, unary_union  # noqa: E402

RAW = os.path.join(ROOT, 'refs', 'cache', 'osm_pinned_raw', '20261114')
PIN = os.path.join(ROOT, 'refs', 'cache', 'osm_pinned')
LOCAL = os.path.join(ROOT, 'refs', 'cache', 'reverify_data2')


def to_xz(g):
    return shapely.transform(g, lambda c: [F.ll_to_world(la, lo) for lo, la in c])


class Raw:
    def __init__(self):
        self.N, self.NT, self.W, self.WT, self.R, self.RT = {}, {}, {}, {}, {}, {}
        for fn in sorted(glob.glob(os.path.join(RAW, '*.osm'))):
            for el in ET.parse(fn).getroot():
                if el.tag not in ('node', 'way', 'relation'):
                    continue
                i = int(el.get('id'))
                t = {x.get('k'): x.get('v') for x in el.findall('tag')}
                if el.tag == 'node':
                    self.N[i] = (float(el.get('lat')), float(el.get('lon')))
                    self.NT[i] = t
                elif el.tag == 'way':
                    self.W[i] = [int(n.get('ref')) for n in el.findall('nd')]
                    self.WT[i] = t
                else:
                    self.R[i] = [(m.get('type'), int(m.get('ref')), m.get('role')) for m in el.findall('member')]
                    self.RT[i] = t
        self.xz = {i: F.ll_to_world(*ll) for i, ll in self.N.items()}
        self.drop = {}
        for typ, T in (('node', self.NT), ('way', self.WT), ('relation', self.RT)):
            for i, t in T.items():
                r = S.sensitive_reason(t)
                if r:
                    self.drop[(typ, i)] = r

    def wpts(self, w):
        return [self.xz[n] for n in self.W[w] if n in self.xz]

    def way_geom(self, w, area=None):
        pts = self.wpts(w)
        if len(pts) < 2:
            return None
        closed = self.W[w][0] == self.W[w][-1] and len(pts) >= 4
        if area is None:
            area = closed
        if closed and area:
            g = Polygon(pts)
            return g if g.is_valid else g.buffer(0)
        return LineString(pts)

    def rel_geom(self, r):
        outer, inner = [], []
        for t, ref, role in self.R[r]:
            if t == 'way' and ref in self.W and len(self.wpts(ref)) >= 2:
                (inner if role == 'inner' else outer).append(LineString(self.wpts(ref)))
        if not outer:
            return None
        po = list(polygonize(linemerge(outer) if len(outer) > 1 else outer))
        if not po:
            return unary_union(outer)
        g = unary_union([p.buffer(0) for p in po])
        if inner:
            pi = list(polygonize(linemerge(inner) if len(inner) > 1 else inner))
            if pi:
                g = g.difference(unary_union([p.buffer(0) for p in pi]))
        return g

    def dropped_geoms(self):
        """list of dicts: kind (area/line/point), cls, typ, id, geom (world metres)"""
        out = []
        for (typ, i), why in self.drop.items():
            if typ == 'node':
                if i in self.xz:
                    out.append(dict(kind='point', cls=why, typ=typ, id=i, geom=Point(self.xz[i])))
            elif typ == 'way':
                g = self.way_geom(i)
                if g is not None:
                    out.append(dict(kind='area' if g.geom_type in ('Polygon', 'MultiPolygon') else 'line', cls=why,
                                    typ=typ, id=i, geom=g))
            else:
                g = self.rel_geom(i)
                if g is not None and not g.is_empty:
                    out.append(dict(kind='area' if g.geom_type in ('Polygon', 'MultiPolygon') else 'line', cls=why,
                                    typ=typ, id=i, geom=g))
        return out


def load_pinned():
    G = json.load(open(os.path.join(PIN, 'zsss_osm_pinned.geojson')))
    feats = []
    for f in G['features']:
        p = f['properties']
        g = to_xz(shape(f['geometry'])) if f.get('geometry') else None
        feats.append(dict(typ=p['@type'], id=p['@id'], tags=p.get('tags', {}), geom=g, props=p))
    els = json.load(open(os.path.join(PIN, 'osm_elements.json')))
    ext = json.load(open(os.path.join(PIN, 'extent_hull1km.geojson')))
    ext_xz = to_xz(shape(ext['features'][0]['geometry']))
    return feats, els, ext_xz


def committed_nodes(raw, ext_xz):
    """way id -> raw node ids of each kept way, without the in-extent nodes that are not vertices of its committed
    geometry. Fix round 3 (rule g of pin_extract.py) removes crossing vertices from the kept geometry, so the raw node
    list alone over-counts what a reader of the committable files sees. Nodes outside the extent are kept in the list
    (they are clipped, not removed), so the vertex tests near the extent edge are unchanged. Before fix round 3 this
    list equals raw.W for every kept way."""
    G = json.load(open(os.path.join(PIN, 'zsss_osm_pinned.geojson')))
    inner = ext_xz.buffer(-0.05)
    out = {}
    for f in G['features']:
        p = f['properties']
        if p['@type'] != 'way' or not f.get('geometry') or p['@id'] not in raw.W:
            continue
        cs = set()
        stack = [f['geometry']['coordinates']]
        while stack:
            c = stack.pop()
            if c and isinstance(c[0], (int, float)):
                cs.add((c[0], c[1]))
            else:
                stack.extend(c)
        out[p['@id']] = [n for n in raw.W[p['@id']] if n in raw.N and (
            (round(raw.N[n][1], 7), round(raw.N[n][0], 7)) in cs or not Point(raw.xz[n]).within(inner))]
    return out


def cls(t):
    for k in ('aeroway', 'railway', 'highway', 'waterway', 'building', 'landuse', 'barrier', 'boundary', 'leisure',
              'amenity', 'man_made', 'natural', 'power', 'place', 'office', 'shop', 'public_transport', 'area:highway',
              'type'):
        if k in t:
            return '%s=%s' % (k, t[k])
    return 'other'


def save_local(name, obj):
    os.makedirs(LOCAL, exist_ok=True)
    with open(os.path.join(LOCAL, name), 'w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
