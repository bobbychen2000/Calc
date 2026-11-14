"""Re-verify (data) M3/M4/M5/L4/L6 and the stand checks of QA section 9, with my own geometry.
Counts and stand names only; AIP comparisons are counts. usage: python3 -I rv_stands.py SHA3D_DIR"""
import sys, os, json, math, re
from collections import Counter, defaultdict
import numpy as np
from shapely.geometry import Polygon, LineString, Point, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
import shapely
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'tools/common'))
import frame as F
ST = json.load(open(os.path.join(ROOT, 'data/sha_stands.json')))
A = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
T = json.load(open(os.path.join(ROOT, 'data/sha_taxigraph.json')))
G = json.load(open(os.path.join(ROOT, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
stands = ST['stands']; byn = {s['name']: s for s in stands}
ORDER = ['B', 'C', 'CL', 'D', 'E', 'EL', 'F']
CM = {k: tuple(v) for k, v in ST['class_max'].items()}
# reference shape proportions (my own planform: same proportional sketch as documented in acplan, re-implemented)
REFW = {'B': (3.1, 25), 'C': (3.95, 25), 'CL': (3.76, 25), 'D': (5.03, 31), 'E': (5.64, 30), 'EL': (6.2, 31.6), 'F': (6.5, 37.5)}
def plan(L, span, w, sweep):
    hw = w / 2; t = math.tan(math.radians(sweep)); half = span / 2
    fus = [(0, -hw * .6), (-.06 * L, -hw), (-.8 * L, -hw), (-L, -hw * .3), (-L, hw * .3), (-.8 * L, hw), (-.06 * L, hw), (0, hw * .6)]
    P = [fus]; le = -.36 * L; cr = .17 * L; ct = .045 * L
    for s in (-1, 1):
        tl = le - (half - hw) * t
        P.append([(le, s * hw), (tl, s * half), (tl - ct, s * half), (le - cr, s * hw)])
        hh = .17 * span; hr = -.86 * L; hc = .07 * L
        P.append([(hr, s * hw * .7), (hr - hh * t, s * hh), (hr - hh * t - .4 * hc, s * hh), (hr - hc, s * hw * .7)])
    return P
def place(polys, nose, hdg):
    h = math.radians(hdg); f = (math.sin(h), -math.cos(h)); r = (math.cos(h), math.sin(h))
    return unary_union([Polygon([(nose[0] + u * f[0] + v * r[0], nose[1] + u * f[1] + v * r[1]) for u, v in p]) for p in polys])
def bearing(p, q):
    return math.degrees(math.atan2(q[0] - p[0], -(q[1] - p[1]))) % 360
def hd(a, b): return abs((a - b + 180) % 360 - 180)

# ---- 1. nose / heading against the pinned OSM
xz = lambda lo, la: F.ll_to_world(la, lo)
pp = {}; ways = {}
for f in G['features']:
    t = f['properties'].get('tags', {})
    if t.get('aeroway') == 'parking_position':
        g = f['geometry']
        if g['type'] == 'Point' and t.get('ref'):
            pp.setdefault(t['ref'], []).append(xz(*g['coordinates']))
        if g['type'] == 'LineString':
            ways[f['properties']['@id']] = [xz(*c) for c in g['coordinates']]
dn = []; dh = []; dh_data = []
for s in stands:
    c = pp.get(s['name'])
    if c:
        dn.append(min(math.dist(s['nose'], q) for q in c))
    w = ways.get(s['osm'].get('leadin_way'))
    if w:
        # final segment of the OSM lead-in way that ends at the stop
        if math.dist(w[-1], s['nose']) > math.dist(w[0], s['nose']): w = w[::-1]
        dh.append(hd(bearing(w[-2], w[-1]), s['hdg']))
    li = s['leadin']; dh_data.append(hd(bearing(li[-2], li[-1]), s['hdg']))
print('nose vs OSM ref node: n %d, max %.3f m; hdg vs OSM final segment: n %d, max %.3f deg; hdg vs data leadin final segment: max %.3f deg'
      % (len(dn), max(dn), len(dh), max(dh), max(dh_data)))
# ---- 2. planforms
excl = set()
for s in stands:
    for o in s.get('excl') or []:
        excl.add(frozenset((s['name'], o)))
alt = defaultdict(set)
for s in stands:
    if s.get('alt_group'): alt[tuple(sorted(s['alt_group']))].add(s['name'])
same_alt = lambda a, b: any(a in g and b in g for g in alt.values())
def planforms(mode):
    P = {}
    for s in stands:
        c = s['cls']; w, sw = REFW[c]
        if mode == 'ref':
            r = ST['class_ref'][c]; L, sp = r['length_m'], r['span_m']
        else:
            sp, L = CM[c]
            if mode == 'max_spanmax' and s.get('span_max') is not None:
                sp = min(sp, s['span_max'])
            if s.get('len_max'): L = min(L, s['len_max'])
        P[s['name']] = place(plan(L, sp, w, sw), s['nose'], s['hdg'])
    return P
names = [s['name'] for s in stands]
for mode in ('ref', 'max_spanmax', 'max_raw'):
    P = planforms(mode); tree = STRtree([P[n] for n in names])
    ov = []; close = []
    for i, n in enumerate(names):
        for j in tree.query(P[n].buffer(5)):
            m = names[j]
            if j <= i or frozenset((n, m)) in excl or same_alt(n, m): continue
            a = P[n].intersection(P[m]).area; d = P[n].distance(P[m])
            if a > 0.01: ov.append((n, m, round(a, 2)))
            elif d < 2.5: close.append((n, m, round(d, 2)))
    print('planforms %-12s overlaps (outside excl / alt): %d %s; pairs closer than 2.5 m: %d %s' % (mode, len(ov), ov[:6], len(close), close[:12]))
    if mode == 'max_spanmax':
        PM = P
# buildings clearance (OSM buildings of the airport file + context buildings)
bl = [Polygon(b['ring']) for b in A['buildings']] + [Polygon(b['ring']) for b in A['context']['buildings'] if len(b.get('ring') or []) >= 4]
btree = STRtree(bl)
nb = [(n, round(min(PM[n].distance(bl[j]) for j in btree.query(PM[n].buffer(3))), 2)) for n in names if len(btree.query(PM[n].buffer(3)))]
print('class-max (span_max) planforms within 3 m of a building: %d %s' % (len(nb), nb[:8]))
# span_max vs class bounds
lo = Counter(); bad = []
for s in stands:
    c = s['cls']; i = ORDER.index(c)
    if s.get('span_max') is None: lo['no span_max'] += 1; continue
    if s['span_max'] > CM[c][0] + 0.01: bad.append((s['name'], 'span_max above class max'))
    below = CM[ORDER[i - 1]][0] if i > 0 else 0
    if s['span_max'] < below - 0.01: bad.append((s['name'], c, s['span_max'], 'span_max below the next lower class max %.1f' % below))
    ref = ST['class_ref'][c]['span_m']
    if s['span_max'] < ref - 0.01: lo['span_max below the class reference span'] += 1
print('span_max: %s; inconsistent with the class: %d %s' % (dict(lo), len(bad), bad[:10]))
print('classes', dict(Counter(s['cls'] for s in stands)), 'cls_src', dict(Counter(s['cls_src'] for s in stands)))
# ---- 3. AIP comparison (local, counts only)
AIPF = os.path.join(ROOT, 'refs/cache/aip/derived_aip_zsss/stands.json')
if os.path.exists(AIPF):
    AS = json.load(open(AIPF)); W = AS['wingspan_limit_m']
    def lim(x):
        m = re.findall(r'[\d.]+', str(x)); return (float(m[-1]), '＜' in str(x) or '<' in str(x)) if m else (None, None)
    def aip_cls(x):
        v, strict = lim(x)
        if v is None: return None
        for c in ORDER:
            sp = CM[c][0]
            if (sp < v) if strict else (sp <= v + 0.05): last = c
            else: break
        return last
    cmp = Counter(); area_over = Counter(); over2 = []
    for s in stands:
        if s['name'] not in W: cmp['not in AIP'] += 1; continue
        a = aip_cls(W[s['name']])
        if a is None: cmp['no limit'] += 1; continue
        d = ORDER.index(s['cls']) - ORDER.index(a)
        cmp['exact' if d == 0 else 'above' if d > 0 else 'below'] += 1
        if d > 0: area_over[s['area']] += 1
        if d >= 2: over2.append(s['name'])
        wide_us = ORDER.index(s['cls']) >= ORDER.index('D'); wide_aip = ORDER.index(a) >= ORDER.index('D')
        cmp['wide/narrow agree' if wide_us == wide_aip else ('we wide, AIP narrow' if wide_us else 'we narrow, AIP wide')] += 1
        sm = s.get('span_max')
        if sm is not None:
            v, strict = lim(W[s['name']])
            if sm > v + 0.05 or (strict and sm >= v): cmp['span_max above the AIP limit'] += 1
    print('vs AIP (mirror), local counts:', dict(cmp)); print('  above the AIP class by area:', dict(area_over)); print('  2+ classes above: %d' % len(over2))
    V = set(AS['vdgs_stands'])
    print('  VDGS stands that are contact: %d of %d; contact stands not VDGS: %d' % (sum(1 for s in stands if s['name'] in V and s['contact']),
          len(V & set(names)), sum(1 for s in stands if s['contact'] and s['name'] not in V)))
    print('  bridge_status of VDGS stands:', dict(Counter(s['bridge_status'] for s in stands if s['name'] in V)),
          '| of non-VDGS stands:', dict(Counter(s['bridge_status'] for s in stands if s['name'] not in V)))
# ---- 4. bridges
bs = Counter(s['bridge_status'] for s in stands); print('bridge_status', dict(bs))
reach = []; walk = []; gt50 = []; dup = []; srcs = Counter(); two = 0; t1 = []
for s in stands:
    br = s.get('bridges') or []
    if len(br) > 1: two += 1
    for b in br:
        r = math.dist(b['rotunda'], b['cab']); reach.append(r); srcs[b['src']] += 1
        wl = sum(math.dist(p, q) for p, q in zip(b['walk'][:-1], b['walk'][1:])) if b.get('walk') else 0; walk.append(wl)
        if r > 50: gt50.append((s['name'], round(r, 1)))
        if abs(r - b.get('reach_m', r)) > 0.05: dup.append((s['name'], 'reach_m != |rotunda-cab|'))
        if s['area'].startswith('T1'): t1.append(r)
    for i in range(len(br)):
        for j in range(i + 1, len(br)):
            if math.dist(br[i]['rotunda'], br[j]['rotunda']) < 8: dup.append((s['name'], 'rotundas < 8 m apart'))
print('bridges %d (src %s): reach median %.1f max %.1f; > 50 m: %s; > 45 m: %d; T1 max reach %.1f; stands with 2 bridges: %d; issues %s'
      % (len(reach), dict(srcs), np.median(reach), max(reach), gt50, sum(r > 45 for r in reach), max(t1) if t1 else -1, two, dup[:5]))
# shared rotunda between stands
rot = defaultdict(list)
for s in stands:
    for b in s.get('bridges') or []:
        rot[(round(b['rotunda'][0], 1), round(b['rotunda'][1], 1))].append(s['name'])
print('rotunda points used by more than one stand:', [v for v in rot.values() if len(v) > 1])
s112 = byn.get('112'); print('112:', s112['bridge_status'], s112['contact'], [b['src'] for b in s112['bridges']])
# bridges crossing another stand's planform (cab-rotunda segment)
cross = []
for s in stands:
    for b in s.get('bridges') or []:
        seg = LineString([b['rotunda'], b['cab']])
        for n in names:
            if n != s['name'] and seg.intersection(PM[n]).length > 1.0:
                cross.append((s['name'], n))
print('bridge segments crossing another stand\'s class-max planform by > 1 m: %d %s' % (len(cross), cross[:8]))
# ---- 5. push
pl = []; bad = []; ends = Counter(); over = 0; cross = []
nodes = {(round(n['x'], 2), round(n['z'], 2)): n for n in T['nodes']}
for s in stands:
    p = s['push']; pts = p['pts']; L = sum(math.dist(a, b) for a, b in zip(pts[:-1], pts[1:])); pl.append(L)
    rl = s['leadin'][::-1]
    if not (math.dist(pts[0], s['nose']) < 0.01 and all(any(math.dist(q, r) < 0.01 for r in rl) for q in pts)):
        bad.append(s['name'])
    if abs(L - p['push_dist_m']) > 0.5: bad.append((s['name'], 'len'))
    j = nodes.get((round(pts[-1][0], 2), round(pts[-1][1], 2)))
    ends[j['kind'] if j else 'no graph node'] += 1
    if p.get('over_cap'): over += 1
    line = LineString(pts)
    for n in names:
        if n != s['name'] and line.intersection(PM[n]).length > 1.0:
            cross.append((s['name'], n))
pl = np.array(pl)
print('push: median %.1f, max %.1f, > 150 m: %d %s, > 100 m: %d; not along own lead-in: %s; end node kinds %s; over_cap flags %d'
      % (np.median(pl), pl.max(), (pl > 150).sum(), [s['name'] for s, l in zip(stands, pl) if l > 150], (pl > 100).sum(), bad[:6], dict(ends), over))
print('push paths crossing another stand\'s class-max planform by > 1 m: %d %s' % (len(cross), cross[:10]))
for grp in (['%d' % i for i in range(401, 414)], ['%d' % i for i in range(601, 609)]):
    v = [round(float(pl[names.index(n)]), 0) for n in grp if n in byn]
    print('  push lengths %s..%s: %s; end kinds %s' % (grp[0], grp[-1], v, Counter(byn[n]['push']['end_kind'].split(' osm')[0] for n in grp if n in byn)))
# ---- 6. pavement without lead-in buffers (my own union: aprons + surfaces)
pav = [Polygon(a['ring'], a.get('holes') or []) for a in A['aprons']]
for k, v in A['surfaces'].items():
    for p in v:
        ring = p['ring'] if isinstance(p, dict) else p
        if len(ring) >= 4: pav.append(Polygon(ring).buffer(0))
for r in A['runways']:
    pav.append(Polygon(r['outline']['ring']))
PU = unary_union(pav)
fr = {n: PM[n].difference(PU).area / PM[n].area for n in names}
top = sorted(fr.items(), key=lambda x: -x[1])[:4]
print('class-max planform outside aprons+surfaces+runway (no lead-in buffers): max %s; > 5 %%: %d; data field max %.3f'
      % ([(a, round(b, 3)) for a, b in top], sum(v > 0.05 for v in fr.values()), max(s['pavement_outside_frac_no_leadin'] for s in stands)))
print('nose_note present:', 'nose_note' in ST, '| per-stand src values', dict(Counter(s['src'] for s in stands)),
      '| stands without evidence', sum(1 for s in stands if not s.get('evidence')))
