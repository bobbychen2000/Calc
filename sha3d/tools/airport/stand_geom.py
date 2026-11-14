"""Stand geometry from the pinned OSM extract (ODbL) for task A2: shared by build_stands.py, stand_sar.py, stand_s2.py,
build_taxigraph.py and the plates.

OSM at ZSSS (pinned 2026-11-14, refs/cache/osm_pinned/): 164 aeroway=parking_position NODES with ref, every one the end
vertex of an untagged aeroway=parking_position WAY (461 ways = the painted lead-in lines, drawn from the apron taxilane /
taxiway to the stop end). Reference point used here ("stop"): the OSM ref node = the end of the lead-in line, i.e. where
the mapper ended the painted lead-in line (the stop-bar end of the line). Heading = direction of the final segment of the
lead-in into the stop (median length of that segment 67 m, minimum 13 m: straight).

Coordinates: world frame of tools/common/frame.py (x east, z south, metres); headings true degrees.
"""
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import unary_union
import shapely.ops

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402

R2 = lambda v: round(float(v), 2)  # noqa: E731


def key(c):
    return (round(c[0], 7), round(c[1], 7))


def wxz(c):
    x, z = F.ll_to_world(c[1], c[0])
    return (x, z)


def hdiff(a, b):
    return (a - b + 180) % 360 - 180


def _vec_world(lo, la):
    try:
        xs, zs = zip(*[F.ll_to_world(b, a) for a, b in zip(lo, la)])
        return list(xs), list(zs)
    except TypeError:
        return F.ll_to_world(la, lo)


def stand_sort_key(name):
    import re
    m = re.match(r'^(\d+)([A-Z]*)$', name or '')
    return (int(m.group(1)), m.group(2)) if m else (99999, name or '')


class OsmStands:
    """Parses the pinned extract once: stands (ref nodes), lead-in network, unreferenced dead ends, gates, terminals,
    aprons, taxiways."""

    def __init__(self, root):
        self.root = root
        fc = json.load(open(os.path.join(root, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
        self.features = fc['features']
        T = lambda f: f['properties']['tags']  # noqa: E731
        self.ref_nodes = [f for f in self.features if T(f).get('aeroway') == 'parking_position'
                          and f['geometry']['type'] == 'Point']
        self.leadin_ways = [f for f in self.features if T(f).get('aeroway') == 'parking_position'
                            and f['geometry']['type'] == 'LineString']
        self.gates = [f for f in self.features if T(f).get('aeroway') == 'gate']
        self.taxiway_ways = [f for f in self.features if T(f).get('aeroway') == 'taxiway'
                             and f['geometry']['type'] == 'LineString']
        self.terminals = [f for f in self.features if T(f).get('aeroway') == 'terminal']
        self.aprons = [f for f in self.features if T(f).get('aeroway') == 'apron']
        # vertex degree inside the lead-in network (an end vertex counts 1, an inner vertex 2)
        self.deg = defaultdict(int)
        self.vert_ways = defaultdict(list)
        for i, f in enumerate(self.leadin_ways):
            cs = f['geometry']['coordinates']
            for j, c in enumerate(cs):
                k = key(c)
                self.deg[k] += 1 if j in (0, len(cs) - 1) else 2
                self.vert_ways[k].append((i, j))
        self.twy_vertices = set()
        for f in self.taxiway_ways:
            for c in f['geometry']['coordinates']:
                self.twy_vertices.add(key(c))

    # ------------------------------------------------------------------------------------------- polygons
    def terminal_polys(self):
        out = []
        for f in self.terminals:
            g = shapely.ops.transform(_vec_world, shape(f['geometry']))
            out.append((f, g))
        return out

    def apron_union(self):
        return unary_union([shapely.ops.transform(_vec_world, shape(f['geometry'])) for f in self.aprons])

    # ------------------------------------------------------------------------------------------- stands
    def incoming(self, k):
        """segments of the lead-in network arriving at vertex k: list of (way index, polyline (x, z) ending at k)"""
        out = []
        for i, j in self.vert_ways[k]:
            cs = self.leadin_ways[i]['geometry']['coordinates']
            if j == len(cs) - 1:
                out.append((i, [wxz(c) for c in cs]))
            elif j == 0:
                out.append((i, [wxz(c) for c in cs[::-1]]))
            else:      # inner vertex: two directions
                out.append((i, [wxz(c) for c in cs[:j + 1]]))
                out.append((i, [wxz(c) for c in cs[j:][::-1]]))
        return out

    def _graph(self):
        if getattr(self, '_G', None) is None:
            G = defaultdict(set); P = {}
            for f in self.leadin_ways:
                cs = f['geometry']['coordinates']
                for c0, c1 in zip(cs[:-1], cs[1:]):
                    k0, k1 = key(c0), key(c1)
                    if k0 == k1:
                        continue
                    G[k0].add(k1); G[k1].add(k0); P[k0] = wxz(c0); P[k1] = wxz(c1)
            self._G, self._P = G, P
        return self._G, self._P

    def trace_back(self, k, max_len=800.0):
        """the primary lead-in path of stand vertex k: the shortest path over the lead-in network (Dijkstra) from the
        taxiway system to k, not passing through another stand's stop. Returns the polyline (x, z) ENDING at k
        (taxiway end first), or None."""
        import heapq
        G, P = self._graph()
        refk = {key(f['geometry']['coordinates']) for f in self.ref_nodes}
        if k not in G:
            return None
        dist = {k: 0.0}; prev = {}; hq = [(0.0, k)]
        while hq:
            d, v = heapq.heappop(hq)
            if d > dist.get(v, 1e18) or d > max_len:
                continue
            if v in self.twy_vertices and v != k:
                path = [v]
                while path[-1] != k:
                    path.append(prev[path[-1]])
                return [P[q] for q in path]
            if v in refk and v != k:
                continue
            for n in G[v]:
                nd = d + math.dist(P[v], P[n])
                if nd < dist.get(n, 1e18):
                    dist[n] = nd; prev[n] = v; heapq.heappush(hq, (nd, n))
        return None

    def stand_axis(self, k):
        """(stop (x, z), heading deg, final segment length, way ids) for a stand node k. For an inner vertex (five 33x
        stands), the arriving piece with the longest final straight segment is taken."""
        stop = None
        best = None
        for i, pl in self.incoming(k):
            if len(pl) < 2:
                continue
            a, b = pl[-2], pl[-1]
            L = math.dist(a, b)
            if best is None or L > best[2]:
                best = (i, F.vec_hdg(b[0] - a[0], b[1] - a[1]), L)
            stop = b
        return stop, best[1], best[2], best[0]

    def stands(self):
        """list of dicts: name, osm node id/version/timestamp, stop, hdg, final_seg_m, way id, degree"""
        out = []
        for f in self.ref_nodes:
            p = f['properties']; k = key(f['geometry']['coordinates'])
            stop, hdg, L, wi = self.stand_axis(k)
            out.append(dict(name=p['tags']['ref'], node=p['@id'], version=p['@version'], timestamp=p['@timestamp'],
                            stop=stop, hdg=hdg, final_seg_m=L, way=self.leadin_ways[wi]['properties']['@id'],
                            degree=self.deg[k], key=k))
        out.sort(key=lambda s: stand_sort_key(s['name']))
        return out

    def unref_dead_ends(self):
        """lead-in ends of degree 1 that are neither a ref node nor a taxiway vertex (OSM positions without ref)"""
        refk = {key(f['geometry']['coordinates']) for f in self.ref_nodes}
        out = []
        for i, f in enumerate(self.leadin_ways):
            cs = f['geometry']['coordinates']
            for c in (cs[0], cs[-1]):
                k = key(c)
                if self.deg[k] == 1 and k not in self.twy_vertices and k not in refk:
                    stop, hdg, L, wi = self.stand_axis(k)
                    out.append(dict(name=None, node=None, stop=stop, hdg=hdg, final_seg_m=L,
                                    way=f['properties']['@id'], way_version=f['properties']['@version'],
                                    way_timestamp=f['properties']['@timestamp'], key=k))
        return out

    def gate_points(self):
        return [dict(ref=f['properties']['tags'].get('ref'), node=f['properties']['@id'],
                     version=f['properties']['@version'], xz=wxz(f['geometry']['coordinates']),
                     layer=f['properties']['tags'].get('layer')) for f in self.gates]


# --------------------------------------------------------------------------------------------------- geometry helpers
def to_local(p, origin, hdg):
    """world point -> (u ahead along heading, v to the right) relative to origin"""
    f = F.hdg_vec(hdg); r = (-f[1], f[0])
    dx, dz = p[0] - origin[0], p[1] - origin[1]
    return dx * f[0] + dz * f[1], dx * r[0] + dz * r[1]


def from_local(u, v, origin, hdg):
    f = F.hdg_vec(hdg); r = (-f[1], f[0])
    return (origin[0] + u * f[0] + v * r[0], origin[1] + u * f[1] + v * r[1])
