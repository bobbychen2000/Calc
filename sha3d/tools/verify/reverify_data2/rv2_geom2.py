"""More adversarial geometry tests (second part). Prints counts, lengths and percentages only.
usage: python3 -I rv2_geom2.py          (SHA3D_DIR env var optional)
U1 dangling ends: ends of kept roads, boundaries, barriers and waterways that join nothing (not at the extent edge)
   within 30 m of a dropped group, against the base rate of the extent;
U2 bridges / tunnels / culverts of kept ways that cross a dropped line: is anything kept (water, rail, road on another
   layer) underneath, or would the bridge cross 'nothing'?
U3 corridor: share of the dropped lines (points not covered by a kept polygon) that run in a strip with kept polygons
   on both sides within 30 m and no kept road, rail or water in that strip, against 60 random rigid placements of the
   same lines in the extent;
U4 holes left by second-order drops: for each dropped polygon of the second order, the share of its outline that kept
   polygons (other than roads) trace within 1 m / 5 m, and the IoU of the uncovered gap with it;
U5 voids: raw features inside each dropped area (centroid inside) by class, kept features inside, and the kept
   building density in the 300 m ring around the area;
U6 Hough search over the 'unexplained' kept road vertices (one way, < 2 deg turn, not an end; this is what a level
   crossing leaves on a kept road once the railway is gone): line bins (1 deg x 4 m) voted by vertices of distinct
   ways crossing at >= 30 deg, scored by the most distinct ways inside a 300 / 600 / 1000 m window; how the best bin
   that lies mostly on a dropped line ranks among all bins.
"""
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv2_common as C  # noqa: E402
sys.path.insert(0, os.path.join(C.ROOT, 'tools', 'osm'))
import pin_extract as PE  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402
import json  # noqa: E402

raw = C.Raw()
feats, els, ext = C.load_pinned()
CN = C.committed_nodes(raw, ext)   # kept ways' vertices as committed (fix round 3: rule g)
dg = [d for d in raw.dropped_geoms() if d['geom'].intersects(ext)]
G = {'prison area': unary_union([d['geom'] for d in dg if d['cls'] == 'prison']),
     'armed-police area': unary_union([d['geom'] for d in dg if d['cls'] == 'armed_police']),
     'military railway lines': unary_union([d['geom'] for d in dg if d['kind'] == 'line']),
     'police points': unary_union([d['geom'] for d in dg if d['kind'] == 'point'])}
inv = json.load(open(os.path.join(C.LOCAL, 'inventory_local.json')))
edge = ext.boundary.buffer(5)


def net(t):
    if 'highway' in t:
        return 'road'
    if 'boundary' in t or 'admin_level' in t:
        return 'boundary'
    if 'barrier' in t:
        return 'barrier'
    if 'waterway' in t:
        return 'water'
    return None


# U1
deg = defaultdict(Counter)
ends = []
for f in feats:
    if f['typ'] != 'way' or f['id'] not in CN:
        continue
    n = net(f['tags'])
    nds = CN[f['id']]
    for x in nds:
        deg[x]['any'] += 1
    if n and nds[0] != nds[-1]:
        ends += [(n, nds[0]), (n, nds[-1])]
c_near, c_all = Counter(), Counter()
for n, x in ends:
    if x not in raw.xz or deg[x]['any'] > 1:
        continue
    p = Point(raw.xz[x])
    if not p.within(ext) or p.intersects(edge):
        continue
    c_all[n] += 1
    for gname, g in G.items():
        if p.distance(g) <= 30:
            c_near[(gname, n)] += 1
print('U1 dangling kept ends in the extent (not at the edge): %s' % dict(c_all))
for gname, g in G.items():
    a = g.buffer(30).intersection(ext).area / 1e6
    row = {n: '%d (base %.1f)' % (c_near[(gname, n)], c_all[n] / ext.area * 1e6 * a) for n in c_all}
    print('   within 30 m of the %s (%.3f km2): %s' % (gname, a, row))

# U2
L = G['military railway lines']
under = [f for f in feats if f['geom'] is not None and f['geom'].geom_type in ('LineString', 'MultiLineString')]
c2 = Counter()
for f in feats:
    t = f['tags']
    if f['geom'] is None or not any(k in t for k in ('bridge', 'tunnel')) and t.get('man_made') != 'bridge':
        continue
    if not f['geom'].intersects(L.buffer(2)):
        continue
    seg = f['geom'].intersection(L.buffer(15))
    other = [g for g in under if g is not f and (('waterway' in g['tags']) or ('railway' in g['tags']) or
             ('highway' in g['tags'] and g['tags'].get('layer', '0') != t.get('layer', '0'))) and g['geom'].intersects(seg.buffer(3))]
    c2['%s=%s over the line: %s' % ('bridge' if 'bridge' in t or t.get('man_made') == 'bridge' else 'tunnel',
                                    t.get('bridge') or t.get('tunnel') or t.get('man_made'),
                                    'something kept underneath' if other else 'NOTHING kept underneath')] += 1
print('U2 kept bridges / tunnels crossing a dropped line: %s' % (dict(c2) or 0))

# U3
polys = [f['geom'] for f in feats if f['geom'] is not None and f['geom'].geom_type in ('Polygon', 'MultiPolygon')
         and 'highway' not in f['tags']]
ptree = STRtree(polys)
lin = [f['geom'] for f in feats if f['geom'] is not None and f['geom'].geom_type in ('LineString', 'MultiLineString')
       and any(k in f['tags'] for k in ('highway', 'railway', 'waterway'))]
ltree = STRtree(lin)


def covered(q):
    return any(polys[j].contains(q) for j in ptree.query(q))


def corridor(lw, step=2.0):
    """share of lw (not itself covered by a kept polygon) with kept polygons on both sides within 30 m and no kept
    road / rail / water in between"""
    tot = corr = 0.0
    for part in getattr(lw, 'geoms', [lw]):
        if part.geom_type != 'LineString' or part.length == 0:
            continue
        n = max(1, int(part.length / step))
        for i in range(n):
            s = (i + 0.5) * part.length / n
            p = part.interpolate(s)
            q1, q2 = part.interpolate(max(0, s - 1)), part.interpolate(min(part.length, s + 1))
            dx, dz = q2.x - q1.x, q2.y - q1.y
            h = math.hypot(dx, dz) or 1
            nx, nz = -dz / h, dx / h
            w = part.length / n
            tot += w
            if covered(p):
                continue
            sides = []
            for sgn in (1, -1):
                hit = None
                for dd in range(1, 31):
                    if covered(Point(p.x + sgn * nx * dd, p.y + sgn * nz * dd)):
                        hit = dd
                        break
                sides.append(hit)
            if None in sides:
                continue
            strip = LineString([(p.x + nx * sides[0], p.y + nz * sides[0]), (p.x - nx * sides[1], p.y - nz * sides[1])])
            if not any(lin[j].intersects(strip) for j in ltree.query(strip)):
                corr += w
    return 100 * corr / tot if tot else 0.0


L = G['military railway lines']
Lx = L.intersection(ext)
true = corridor(Lx)
import random  # noqa: E402
from shapely import affinity  # noqa: E402
random.seed(1)
cx, cz = Lx.centroid.x, Lx.centroid.y
minx, minz, maxx, maxz = ext.bounds
vals, tries = [], 0
while len(vals) < 60 and tries < 2000:
    tries += 1
    g = affinity.rotate(Lx, random.uniform(0, 360), origin=(cx, cz))
    g = affinity.translate(g, random.uniform(minx, maxx) - cx, random.uniform(minz, maxz) - cz)
    if not g.within(ext) or g.distance(Lx) < 200:
        continue
    vals.append(corridor(g))
vals.sort()
print('U3 corridor share of the dropped lines: %.1f %%; 60 random rigid placements of the same lines in the extent: '
      'median %.1f %%, p90 %.1f %%, max %.1f %%; %d of 60 score at least as high' % (
          true, vals[30], vals[54], vals[-1], sum(1 for v in vals if v >= true)))

# U4
allpolys = [(f, f['geom']) for f in feats if f['geom'] is not None and f['geom'].geom_type in ('Polygon', 'MultiPolygon')
            and 'highway' not in f['tags']]
aptree = STRtree([g for f, g in allpolys])
for d in inv['second_order']:
    if d['typ'] != 'way':
        continue
    g = raw.way_geom(d['id'])
    if g is None or g.geom_type not in ('Polygon', 'MultiPolygon'):
        continue
    b = g.boundary.intersection(ext)
    near = [allpolys[j][1] for j in aptree.query(g.buffer(5))]
    kb = unary_union([x.boundary for x in near]) if near else None
    res = {}
    for D in (1, 5):
        res[D] = 100 * b.intersection(kb.buffer(D)).length / b.length if kb is not None and b.length else 0.0
    cover = unary_union(near) if near else None
    box = g.buffer(50)
    gap = box.difference(cover) if cover is not None else box
    comps = [p for p in getattr(gap, 'geoms', [gap]) if p.intersects(g)]
    gu = unary_union(comps) if comps else None
    iou = gu.intersection(g).area / gu.union(g).area if gu is not None and not gu.is_empty else 0.0
    ring_cover = (box.difference(g).intersection(cover).area / box.difference(g).area) if cover is not None else 0.0
    print('U4 second-order %-22s outline traced by kept non-road polygons: %.0f %% (1 m), %.0f %% (5 m); 50 m ring '
          'covered %.0f %%; gap IoU %.2f' % (d['cls'], res[1], res[5], 100 * ring_cover, iou))

# U5
cent = defaultdict(Counter)
for i, t in raw.WT.items():
    if not t:
        continue
    g = raw.way_geom(i)
    if g is None:
        continue
    c = g.representative_point()
    for gname in ('prison area', 'armed-police area'):
        if G[gname].contains(c):
            cent[gname][('dropped by the tag rule' if ('way', i) in raw.drop else 'raw') + ' ' + C.cls(t).split('=')[0]] += 1
for i, t in raw.NT.items():
    if t and i in raw.xz:
        for gname in ('prison area', 'armed-police area'):
            if G[gname].contains(Point(raw.xz[i])):
                cent[gname][('dropped by the tag rule' if ('node', i) in raw.drop else 'raw') + ' node'] += 1
for gname in ('prison area', 'armed-police area'):
    g = G[gname]
    kin = sum(1 for f in feats if f['geom'] is not None and g.contains(f['geom'].representative_point()))
    ring = g.buffer(300).difference(g).intersection(ext)
    bl = [f['geom'] for f in feats if 'building' in f['tags'] and f['geom'] is not None]
    bd_ring = sum(1 for b in bl if ring.contains(b.representative_point())) / (ring.area / 1e6)
    bd_ext = len(bl) / (ext.area / 1e6)
    print('U5 %s: raw features with their point inside %s; kept with their point inside: %d; kept buildings per km2 in '
          'the 300 m ring %.0f (extent %.0f)' % (gname, dict(cent[gname]), kin, bd_ring, bd_ext))

# U6
way_of = defaultdict(list)
for f in feats:
    if f['typ'] == 'way':
        for x in CN.get(f['id'], []):
            way_of[x].append(f['id'])
pts, dirs, wid = [], [], []
for f in feats:
    if f['typ'] != 'way' or 'highway' not in f['tags'] or f['id'] not in CN:
        continue
    nds = CN[f['id']]
    for j in range(1, len(nds) - 1):
        x = nds[j]
        if x not in raw.xz or len(way_of[x]) > 1 or not Point(raw.xz[x]).within(ext):
            continue
        a, b, c_ = raw.xz[nds[j - 1]], raw.xz[x], raw.xz[nds[j + 1]]
        d1 = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        d2 = math.degrees(math.atan2(c_[1] - b[1], c_[0] - b[0]))
        t = abs(d1 - d2) % 360
        t = min(t, 360 - t)
        if t < 2:
            pts.append(b); dirs.append(d1 % 180); wid.append(f['id'])
pts = np.array(pts); dirs = np.array(dirs); wid = np.array(wid)
on = np.array([Point(p).distance(L) <= 0.5 for p in pts])
votes = defaultdict(set)
for k in range(len(pts)):
    for th in range(180):
        # line direction th; vertex's way must cross it at >= 30 deg
        a = abs(th - dirs[k]) % 180
        if min(a, 180 - a) < 30:
            continue
        r = math.radians(th)
        rho = -pts[k][0] * math.sin(r) + pts[k][1] * math.cos(r)
        votes[(th, int(math.floor(rho / 4)))].add((wid[k], k))
best_global = max((len({w for w, k in v}) for v in votes.values()), default=0)
for Wn in (300, 600, 1000):
    res = []
    for key, v in votes.items():
        if len(v) < 3:
            continue
        r = math.radians(key[0])
        u = np.array([math.cos(r), math.sin(r)])
        ks = sorted(v, key=lambda wk: pts[wk[1]] @ u)
        pr = [pts[k] @ u for w, k in ks]
        best, j0 = (0, 0), 0
        for j1 in range(len(ks)):
            while pr[j1] - pr[j0] > Wn:
                j0 += 1
            sub = ks[j0:j1 + 1]
            nb = len({w for w, k in sub})
            if nb > best[0]:
                best = (nb, int(sum(on[k] for w, k in sub)))
        res.append(best)
    dist = Counter(r[0] for r in res)
    lb = [r for r in res if r[1] >= 3 and r[1] > r[0] // 2]
    bl = max(lb) if lb else None
    print('U6 window %4d m: bins by distinct-way score %s; best bin mostly on a dropped line: %s, %s' % (
        Wn, dict(sorted(dist.items(), reverse=True)[:5]),
        ('score %d (%d on the line)' % bl) if bl else 'none',
        ('%d bins score higher, %d tie' % (sum(1 for r in res if r[0] > bl[0]), sum(1 for r in res if r[0] == bl[0]) - 1))
        if bl else ''))
print('U6 unexplained road vertices: %d, of which on a dropped line: %d; best global bin (whole extent): %d ways' % (
    len(pts), int(on.sum()), best_global))
