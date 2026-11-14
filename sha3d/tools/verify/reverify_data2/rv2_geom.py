"""Adversarial geometry tests: can the dropped areas, lines or points be traced from the kept geometry of the pinned
extract? Prints counts, lengths and percentages only, per dropped GROUP (prison area, armed-police area, military
railway lines, police points); never ids, names or positions.
usage: python3 -I rv2_geom.py          (SHA3D_DIR env var optional)
T1 touching: kept features with any part within 1 m of the group;
T2 inside: kept features with any part inside a dropped area (and buildings), by class;
T3 near: kept features within 10 m / 30 m, by class;
T4 trace: share of the group's outline / line (1 m samples, inside the extent) that has kept linework within D m
   running within 30 deg of its direction (D = 5, 10, 20, 30), for all kept linework, for the non-exempt part, and per
   class group; longest traced run; base rate from 40 random placements of the same outline / line in the extent;
T5 parallel: kept features with >= 25 m parallel (30 deg) within 30 m (the fixer's rule uses 10 m), by class;
T6 shared nodes: kept way vertices that are nodes of the group's ways; dropped tagged nodes that are vertices of kept
   ways (their coordinates stay in the kept geometry); kept tagged nodes within 0.5 m of a dropped node;
T7 lines: kept bridges / tunnels / culverts / embankments / cuttings, railway ways, railway nodes and dangling railway
   ends near the lines; kept landuse=railway near the lines;
T8 holes: interior rings of kept polygons and the uncovered gap that kept polygons leave around a dropped area,
   compared with the area (intersection over union, Hausdorff distance);
T9 crossing vertices: kept road vertices that lie on a dropped line, and whether they stand out among the
   'unexplained' road vertices (not shared with another way, no turn, not an end) of the extent.
Per-feature details go to refs/cache/reverify_data2/geom_local.json only.
"""
import json
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv2_common as C  # noqa: E402
sys.path.insert(0, os.path.join(C.ROOT, 'tools', 'osm'))
import pin_extract as PE  # noqa: E402
from shapely.geometry import LineString, Point, MultiPoint  # noqa: E402
from shapely.ops import unary_union, linemerge  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

raw = C.Raw()
feats, els, ext = C.load_pinned()
CN = C.committed_nodes(raw, ext)   # kept ways' vertices as committed (fix round 3: rule g)
dg = [d for d in raw.dropped_geoms() if d['geom'].intersects(ext)]
GROUPS = {
    'prison area': [d for d in dg if d['cls'] == 'prison' and d['kind'] == 'area'],
    'armed-police area': [d for d in dg if d['cls'] == 'armed_police' and d['kind'] == 'area'],
    'military railway lines': [d for d in dg if d['kind'] == 'line'],
    'police points': [d for d in dg if d['kind'] == 'point'],
}
local = defaultdict(dict)


def cgroup(t):
    if t.get('aeroway') == 'aerodrome':
        return 'aerodrome boundary'
    if 'railway' in t:
        return 'railway (passenger)' if PE.passenger_rail(t) else 'railway (other)'
    if 'waterway' in t or t.get('natural') == 'water':
        return 'water'
    if 'highway' in t:
        return 'road (public class or named)' if (t['highway'] in PE.PUBLIC_ROADS or t.get('name')) else 'road (other)'
    if 'building' in t or 'building:part' in t:
        return 'building'
    if 'barrier' in t:
        return 'barrier'
    if 'landuse' in t or 'leisure' in t or 'amenity' in t or 'natural' in t:
        return 'landuse / leisure / amenity / natural'
    if 'boundary' in t or 'admin_level' in t:
        return 'boundary'
    if 'aeroway' in t:
        return 'aeroway'
    return 'other'


def exempt(t, kind):
    return PE.line_exempt(t) if kind == 'line' else PE.public_passing(t)


def linework(g):
    if g is None or g.is_empty:
        return None
    if g.geom_type in ('Polygon', 'MultiPolygon'):
        return g.boundary
    if g.geom_type in ('LineString', 'MultiLineString', 'LinearRing'):
        return g
    return None


# kept segments with class labels
segs, seg_meta = [], []
for k, f in enumerate(feats):
    lw = linework(f['geom'])
    if lw is None:
        continue
    for part in getattr(lw, 'geoms', [lw]):
        cs = list(part.coords)
        for a, b in zip(cs[:-1], cs[1:]):
            if a != b:
                segs.append(LineString([a, b]))
                seg_meta.append(k)
tree = STRtree(segs)
geoms = [f['geom'] for f in feats]
gidx = [k for k, g in enumerate(geoms) if g is not None]
ftree = STRtree([geoms[k] for k in gidx])


def ang(a, b):
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def seg_dir(s):
    (x0, y0), (x1, y1) = s.coords[0], s.coords[-1]
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


def samples(lw, step=1.0):
    """(point, direction) every `step` metres along the linework, inside the extent"""
    out = []
    lw = lw.intersection(ext)
    for part in getattr(lw, 'geoms', [lw]):
        if part.geom_type != 'LineString' or part.length == 0:
            continue
        n = max(1, int(part.length / step))
        for i in range(n):
            s = (i + 0.5) * part.length / n
            p = part.interpolate(s)
            q1, q2 = part.interpolate(max(0, s - 1)), part.interpolate(min(part.length, s + 1))
            out.append((p, math.degrees(math.atan2(q2.y - q1.y, q2.x - q1.x)), part.length / n))
    return out


def trace(lw, kind, D_list=(5, 10, 20, 30), select=None):
    """share of the linework traced by kept segments (within D and 30 deg); select(k) filters features"""
    S = samples(lw)
    tot = sum(w for p, d, w in S)
    res = {}
    runs = {}
    for D in D_list:
        cov = 0.0
        best = cur = 0.0
        for p, d, w in S:
            ok = False
            for j in tree.query(p.buffer(D)):
                k = seg_meta[j]
                if select is not None and not select(k):
                    continue
                s = segs[j]
                if s.distance(p) <= D and ang(seg_dir(s), d) <= 30:
                    ok = True
                    break
            if ok:
                cov += w
                cur += w
                best = max(best, cur)
            else:
                cur = 0.0
        res[D] = 100.0 * cov / tot if tot else 0.0
        runs[D] = best
    return tot, res, runs


def parallel_len(g, lw, band_d, step=1.0):
    """length of kept feature g's linework within band_d of lw and parallel to it (30 deg)"""
    kl = linework(g)
    if kl is None:
        return 0.0
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
            if ang(math.degrees(math.atan2(pb.y - pa.y, pb.x - pa.x)),
                   math.degrees(math.atan2(q2.y - q1.y, q2.x - q1.x))) <= 30:
                tot += b - a
    return tot


kept_way_ids = {f['id'] for f in feats if f['typ'] == 'way'}
listed_nodes = {i for i, v in els['node']}
node_owner = defaultdict(set)
for f in feats:
    if f['typ'] == 'way':
        for n in CN.get(f['id'], []):
            node_owner[n].add(f['id'])

for gname, G in GROUPS.items():
    if not G:
        continue
    print('\n== %s: %d element(s)' % (gname, len(G)))
    kind = G[0]['kind']
    U = unary_union([d['geom'] for d in G])
    lw = U.boundary if kind == 'area' else U
    # T1 / T3
    for D, label in ((1, 'T1 touching (<= 1 m)'), (10, 'T3 within 10 m'), (30, 'T3 within 30 m')):
        c = Counter()
        for j in ftree.query(U.buffer(D)):
            k = gidx[j]
            if geoms[k].distance(U) <= D:
                c[cgroup(feats[k]['tags']) + (' [exempt]' if exempt(feats[k]['tags'], kind if kind != 'point' else 'area') else '')] += 1
        print('  %s: %d %s' % (label, sum(c.values()), dict(sorted(c.items()))))
    # T2
    if kind == 'area':
        c = Counter(); a_in = Counter()
        for j in ftree.query(U):
            k = gidx[j]
            g = geoms[k]
            inter = g.intersection(U)
            if inter.is_empty:
                continue
            m = inter.area if g.geom_type in ('Polygon', 'MultiPolygon') else inter.length
            if m <= 0.01:
                continue
            gr = cgroup(feats[k]['tags'])
            c[gr] += 1
            a_in[gr] += m
            local[gname].setdefault('inside', []).append((feats[k]['typ'], feats[k]['id'], C.cls(feats[k]['tags']), round(m, 1)))
        print('  T2 kept features with a part inside: %d %s' % (sum(c.values()), dict(c)))
        print('     inside measure (m2 for polygons, m for lines): %s' % {k: round(v) for k, v in a_in.items()})
        print('     dropped area size: %.0f m2, outline %.0f m' % (U.area, U.boundary.length))
    if kind == 'point':
        # T6 for points
        pts_ids = [d['id'] for d in G]
        vert = [i for i in pts_ids if node_owner.get(i)]
        listed = [i for i in pts_ids if i in listed_nodes]
        near_tagged = 0
        for d in G:
            for j in ftree.query(d['geom'].buffer(0.5)):
                k = gidx[j]
                if feats[k]['typ'] == 'node' and geoms[k].distance(d['geom']) <= 0.5:
                    near_tagged += 1
        cls_v = Counter(C.cls(next(f['tags'] for f in feats if f['typ'] == 'way' and f['id'] == w))
                        for i in vert for w in node_owner[i])
        print('  T6 dropped points that are vertices of kept ways: %d of %d (kept owner classes %s); listed in '
              'osm_elements.json: %d; kept tagged nodes within 0.5 m: %d' % (len(vert), len(G), dict(cls_v), len(listed), near_tagged))
        # distinctive vertices? a vertex of a kept way that is only there for the dropped node
        lone = 0
        for i in vert:
            owners = node_owner[i]
            if len(owners) == 1:
                w = next(iter(owners)); nds = CN[w]
                if i in nds[1:-1]:
                    j = nds.index(i)
                    a, b, c_ = raw.xz[nds[j - 1]], raw.xz[i], raw.xz[nds[j + 1]]
                    t = ang(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), math.degrees(math.atan2(c_[1] - b[1], c_[0] - b[0])))
                    if t < 2:
                        lone += 1
        print('     of these, mid-vertices of one way with < 2 deg turn (vertex there only for the dropped node): %d' % lone)
        continue
    # T4
    tot, res, runs = trace(lw, kind)
    print('  T4 trace, all kept linework (%.0f m sampled): %s; longest run %s' % (
        tot, {D: '%.1f %%' % v for D, v in res.items()}, {D: '%.0f m' % v for D, v in runs.items()}))
    # base rate: the same outline / line placed at random (rotation + translation) inside the extent, away from it
    import random
    from shapely import affinity
    random.seed(7)
    lwx = lw.intersection(ext)
    cx, cz = lwx.centroid.x, lwx.centroid.y
    minx, minz, maxx, maxz = ext.bounds
    base = {5: [], 10: [], 20: [], 30: []}
    tries = 0
    while len(base[10]) < 40 and tries < 4000:
        tries += 1
        g = affinity.translate(affinity.rotate(lwx, random.uniform(0, 360), origin=(cx, cz)),
                               random.uniform(minx, maxx) - cx, random.uniform(minz, maxz) - cz)
        if not g.within(ext) or g.distance(U) < 100:
            continue
        _, rb, _ = trace(g, kind)
        for D in base:
            base[D].append(rb[D])
    print('     base rate, 40 random placements of the same outline / line in the extent: %s' % {
        D: 'median %.0f %%, p90 %.0f %%, %d of 40 >= true' % (sorted(v)[20], sorted(v)[36], sum(1 for x in v if x >= res[D]))
        for D, v in base.items()})
    tot, res, runs = trace(lw, kind, select=lambda k: not exempt(feats[k]['tags'], kind))
    print('     non-exempt linework only: %s; longest run %s' % ({D: '%.1f %%' % v for D, v in res.items()},
                                                               {D: '%.0f m' % v for D, v in runs.items()}))
    for grp in ('road (public class or named)', 'road (other)', 'railway (passenger)', 'railway (other)', 'water',
                'aerodrome boundary', 'building', 'barrier', 'landuse / leisure / amenity / natural', 'boundary',
                'aeroway', 'other'):
        tot, res, runs = trace(lw, kind, D_list=(10, 30), select=lambda k, grp=grp: cgroup(feats[k]['tags']) == grp)
        if res[30] > 0:
            print('     %-40s %s; longest run %s' % (grp, {D: '%.1f %%' % v for D, v in res.items()},
                                                     {D: '%.0f m' % v for D, v in runs.items()}))
    # T5
    c = Counter(); mx = Counter()
    for j in ftree.query(lw.buffer(30)):
        k = gidx[j]
        L = parallel_len(geoms[k], lw, 30)
        if L >= 25:
            gr = cgroup(feats[k]['tags']) + (' [exempt]' if exempt(feats[k]['tags'], kind) else '')
            c[gr] += 1
            mx[gr] = max(mx[gr], L)
            local[gname].setdefault('parallel30', []).append((feats[k]['typ'], feats[k]['id'], C.cls(feats[k]['tags']), round(L, 1),
                                                              round(parallel_len(geoms[k], lw, 10), 1)))
    print('  T5 kept features >= 25 m parallel within 30 m: %d %s; max length %s' % (
        sum(c.values()), dict(c), {k: round(v) for k, v in mx.items()}))
    # T6
    gnodes = set()
    for d in G:
        if d['typ'] == 'way':
            gnodes.update(raw.W[d['id']])
        elif d['typ'] == 'relation':
            for t, ref, role in raw.R[d['id']]:
                if t == 'way' and ref in raw.W:
                    gnodes.update(raw.W[ref])
    shared = {n: node_owner[n] for n in gnodes if node_owner.get(n)}
    cls_s = Counter(cgroup(next(f['tags'] for f in feats if f['typ'] == 'way' and f['id'] == w))
                    for n, ws in shared.items() for w in ws)
    print('  T6 nodes of the group: %d; kept way vertices among them: %d (by kept owner class %s); listed in '
          'osm_elements.json: %d' % (len(gnodes), len(shared), dict(cls_s), len(gnodes & listed_nodes)))
    # T7 (lines)
    if kind == 'line':
        c = Counter()
        for j in ftree.query(U.buffer(200)):
            k = gidx[j]
            t = feats[k]['tags']; g = geoms[k]; dist = g.distance(U)
            if any(x in t for x in ('bridge', 'tunnel', 'embankment', 'cutting')) or t.get('man_made') == 'bridge' or \
                    t.get('tunnel') == 'culvert':
                if dist <= 30:
                    c['bridge/tunnel/culvert/embankment/cutting <= 30 m (%s)' % cgroup(t)] += 1
            if 'railway' in t:
                lab = 'node' if feats[k]['typ'] == 'node' else 'way'
                for D in (30, 100, 200):
                    if dist <= D:
                        c['railway %s <= %d m (%s)' % (lab, D, 'passenger' if PE.passenger_rail(t) else t.get('railway') + '/' + str(t.get('service')))] += 1
                        break
            if t.get('landuse') == 'railway' and dist <= 30:
                c['landuse=railway <= 30 m'] += 1
        # dangling railway ends
        rail_deg = Counter()
        for f in feats:
            if f['typ'] == 'way' and 'railway' in f['tags'] and f['id'] in CN:
                for n in CN[f['id']]:
                    rail_deg[n] += 1
        dang = Counter()
        for f in feats:
            if f['typ'] == 'way' and 'railway' in f['tags'] and f['id'] in CN and f['geom'] is not None:
                nds = CN[f['id']]
                for n in (nds[0], nds[-1]):
                    if rail_deg[n] == 1 and n in raw.xz:
                        dd = Point(raw.xz[n]).distance(U)
                        for D in (30, 100, 200, 400):
                            if dd <= D:
                                dang['dangling kept railway end <= %d m' % D] += 1
                                break
        print('  T7 %s' % dict(sorted(c.items())))
        print('     %s' % (dict(sorted(dang.items())) or 'no dangling kept railway end within 400 m'))
    # T8 (areas)
    if kind == 'area':
        polys = []
        for j in ftree.query(U.buffer(200)):
            k = gidx[j]
            g = geoms[k]
            if g.geom_type in ('Polygon', 'MultiPolygon'):
                polys.append((k, g))
        best_ring = None
        for k, g in polys:
            for P in getattr(g, 'geoms', [g]):
                for r in P.interiors:
                    from shapely.geometry import Polygon as _P
                    h = _P(r)
                    if h.intersects(U):
                        iou = h.intersection(U).area / h.union(U).area
                        if best_ring is None or iou > best_ring[0]:
                            best_ring = (iou, h.hausdorff_distance(U), C.cls(feats[k]['tags']))
        print('  T8 kept polygons within 200 m: %d; best interior ring vs the area: %s' % (
            len(polys), 'none intersects' if best_ring is None else 'IoU %.2f, Hausdorff %.0f m (%s)' % best_ring))
        # gap left by kept non-building polygons in a 100 m buffer
        for label, sel in (('all kept polygons', lambda t: True),
                           ('landuse / leisure / amenity / natural polygons', lambda t: cgroup(t) == 'landuse / leisure / amenity / natural')):
            cover = unary_union([g for k, g in polys if sel(feats[k]['tags'])] or [Point(0, 0).buffer(0.01)])
            box = U.buffer(100)
            gap = box.difference(cover)
            comps = [p for p in getattr(gap, 'geoms', [gap]) if p.intersects(U)]
            gapU = unary_union(comps) if comps else None
            covered_outside = box.difference(U).intersection(cover).area / box.difference(U).area
            if gapU is not None and not gapU.is_empty:
                iou = gapU.intersection(U).area / gapU.union(U).area
                print('     %s: cover of the 100 m ring outside the area %.0f %%; gap component(s) over the area: IoU %.2f, '
                      'share of the area in the gap %.0f %%' % (label, 100 * covered_outside, iou,
                                                               100 * gapU.intersection(U).area / U.area))
            else:
                print('     %s: no gap over the area' % label)

# T9 crossing vertices
print('\n== T9 crossing vertices')
L = unary_union([d['geom'] for d in GROUPS['military railway lines']])
way_of = defaultdict(list)
for f in feats:
    if f['typ'] == 'way':
        for n in CN.get(f['id'], []):
            way_of[n].append(f['id'])
unexpl, on_line_unexpl, on_line = 0, 0, 0
for f in feats:
    if f['typ'] != 'way' or 'highway' not in f['tags'] or f['id'] not in CN:
        continue
    nds = CN[f['id']]
    for j in range(1, len(nds) - 1):
        n = nds[j]
        if n not in raw.xz or not Point(raw.xz[n]).within(ext):
            continue
        onl = Point(raw.xz[n]).distance(L) <= 0.5
        on_line += onl
        if len(way_of[n]) > 1:
            continue
        a, b, c_ = raw.xz[nds[j - 1]], raw.xz[n], raw.xz[nds[j + 1]]
        t = ang(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), math.degrees(math.atan2(c_[1] - b[1], c_[0] - b[0])))
        if t < 2:
            unexpl += 1
            on_line_unexpl += onl
print('  kept road mid-vertices on a dropped line (<= 0.5 m): %d; unexplained road vertices in the extent '
      '(one way, < 2 deg turn): %d, of which on a dropped line: %d' % (on_line, unexpl, on_line_unexpl))
C.save_local('geom_local.json', local)
