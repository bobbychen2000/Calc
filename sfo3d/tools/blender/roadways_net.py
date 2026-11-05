"""Elevated landside roadways: the network and its levels (no bpy; numpy + scipy + shapely). Used by
tools/blender/build_roadways.py (the 3-D asset data/buildings3d/roadways.glb) and drawn on its check sheet first.

Why (integration review round 1, finding 1): the 187 OSM roads the app keeps as `elevated` (data/sfo_landside.json, bridge /
layer >= 1) were drawn as ground footprints only, so the ITB departures curb (level 3) and the domestic departures roadway
stood over flat, painted roads, and no asset owned them. This module owns them.

Inputs (all pinned):
  OSM ways (refs/cache/osm/overpass_landside_at_20260926T030301Z.json, ODbL; the extract data/sfo_landside.json is built
  from) with their node topology: the same selection as tools/build_landside.py (ROAD_CLASSES, not tunnel / covered /
  layer < 0; elevated = bridge != no or layer >= 1), only ways the app keeps (their id is an elevated road in
  data/sfo_landside.json: inside APT_RECT, not airside), without the upper-level garage aisles (`elevated_why`) and the
  ways that run inside a landside building (garage ramps and decks: that asset's own) - every exclusion is counted.
  Asset footprints: data/buildings3d/integration.json (b3d_integrate.py, measured on the exported GLBs).
Levels (deck top above local grade; every value tagged):
  * domestic departures roadway (OSM name 'Departures', layer 1, within ANCHOR_DOM_M of the domestic asset): the domestic
    asset's departures curb, manifest.json#domestic.dimensions 'departures curb above the apron (T1 / T2)' = 4.877 m
    [unk: T3 L1 -> L2 by analogy], less the kerb KERB_M [inf] -> 4.73 m;
  * ITB departures roadway (layer 2 ways within ANCHOR_ITB_M of the ITB hall): spec_itb.json level3.floor = 11.5 m [inf,
    +-1.5 m], less the kerb -> 11.35 m;
  * where an elevated way meets an at-grade road (a shared OSM node): grade (0 m) [inf: the bridge abutment; any fill
    beyond it is the at-grade road's];
  * elsewhere: screened interpolation along the network (minimise sum (dh/ds)^2 + (h - H_L)^2 / ELL^2 over arc length),
    with the layer prior H_L = LAYER_H[layer] [inf: Caltrans Highway Design Manual 309.2 minimum vertical clearance
    15 ft (4.6 m, recalled, not re-checked) + ~1.5-1.9 m structure depth per deck level]; ELL = 100 m.
Checks (report): grade per edge, crossings of elevated ways (clearance between the decks), elevated over at-grade roads.
Frame: tools/geo_frame.py world x east / z south (y up in the 3-D asset)."""
import json, math, os, re, sys
import numpy as np
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

OSM = os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_landside_at_20260926T030301Z.json')
ROAD_CLASSES = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link',
                'tertiary', 'tertiary_link', 'unclassified', 'residential', 'service'}
# tools/build_landside.py DEFAULT_W (inferred carriageway widths where OSM has neither width nor lanes)
DEFAULT_W = {'motorway': 7.2, 'trunk': 7.2, 'primary': 7.2, 'secondary': 7.2, 'tertiary': 7.2, 'unclassified': 6.0,
             'residential': 6.0, 'motorway_link': 4.5, 'trunk_link': 4.5, 'primary_link': 4.5, 'secondary_link': 4.5,
             'tertiary_link': 4.5, 'service': 4.0}
LANE_W = 3.6          # m, FHWA 12-ft lane (as tools/build_landside.py) [inf]
KERB_M = 0.15         # roadway surface below the curb sidewalk (6-in curb face) [inf]
LAYER_H = {1: 6.5, 2: 12.5, 3: 18.5, 4: 24.5}   # deck-top prior per OSM layer [inf, see the header]
ELL = 100.0           # m, screening length of the layer prior along the network [inf]
ANCHOR_DOM_M, ANCHOR_ITB_M = 60.0, 45.0
DECK_DEPTH = 1.2      # m, deck slab + girders, top to soffit [inf: cast-in-place box girder spans ~30 m, depth ~0.04 x span]
CLEAR_MIN = 4.6       # m, vertical clearance reported below (Caltrans HDM 309.2, 15 ft) [inf]


def num(v):
    try: return float(str(v).split(';')[0].replace('m', '').strip())
    except (TypeError, ValueError): return None


def ring_poly(r):
    p = Polygon(r[0], r[1:] if len(r) > 1 else None)
    return p if p.is_valid else p.buffer(0)


def asset_levels():
    """the two curb levels from the asset groups' own records (tags kept)"""
    man = json.load(open(os.path.join(ROOT, 'data', 'buildings3d', 'manifest.json')))
    dom = [d for d in man['domestic']['dimensions'] if d.get('key', '').startswith('departures curb above the apron')][0]
    spec = json.load(open(os.path.join(ROOT, 'tools', 'buildings', 'spec_itb.json')))
    l3 = [it for it in spec['items'] if it.get('id') == 'level3.floor'][0]
    return dict(domestic=dict(curb=float(dom['value']), tag=dom['tag'], source='manifest.json#domestic.dimensions: ' + dom['key'] + ' (' + dom['source'] + ')'),
                itb=dict(curb=float(l3['value']), tag=l3['tag'], source='tools/buildings/spec_itb.json level3.floor (' + l3.get('method', '') + '; ' + l3.get('note', '') + ')'))


def footprints():
    I = json.load(open(os.path.join(ROOT, 'data', 'buildings3d', 'integration.json')))
    F = {}
    for g, U in I['footprints'].items():
        for u, v in U.items():
            if u == '*': continue
            F[(g, u)] = unary_union([ring_poly(r) for r in v['rings']])
    return F


def network(log=print):
    d = json.load(open(OSM)); L = json.load(open(os.path.join(ROOT, 'data', 'sfo_landside.json')))
    kept_elev = {r['osm_id'] for r in L['roads'] if r['elevated'] and not r.get('elevated_why')}
    why = {r['osm_id']: r['elevated_why'] for r in L['roads'] if r.get('elevated_why')}
    F = footprints()
    land = unary_union([g for (grp, u), g in F.items() if grp == 'landside' and not u.startswith('airtrain')])
    ways, grade_nodes, stats = [], set(), dict(osm_elevated=0, not_in_app=0, garage_aisles=0, inside_landside_building=0)
    grade_ways = []
    for e in d['elements']:
        t = e.get('tags', {})
        if e['type'] != 'way' or 'geometry' not in e or t.get('highway') not in ROAD_CLASSES or t.get('area') == 'yes': continue
        lay = num(t.get('layer')) or 0.0
        if t.get('tunnel', 'no') != 'no' or lay < 0 or t.get('covered') == 'yes': continue
        elev = t.get('bridge', 'no') != 'no' or lay >= 1
        if not elev:
            grade_nodes.update(e['nodes'])
            wg = num(t.get('width')); lg = num(t.get('lanes'))
            wg = wg if wg is not None else (lg * LANE_W if lg else DEFAULT_W[t['highway']])
            grade_ways.append(dict(id=e['id'], nodes=list(e['nodes']), pts=np.array([GF.wgs84_to_world(g['lat'], g['lon']) for g in e['geometry']]),
                                   w=float(wg), lanes=int(lg) if lg else max(1, int(round(wg / LANE_W))), oneway=t.get('oneway') in ('yes', '1', 'true', '-1'), kind=t['highway']))
            continue
        stats['osm_elevated'] += 1
        if e['id'] in why: stats['garage_aisles'] += 1; continue
        if e['id'] not in kept_elev: stats['not_in_app'] += 1; continue
        pts = [GF.wgs84_to_world(g['lat'], g['lon']) for g in e['geometry']]
        ls = LineString(pts)
        if ls.length < 2.0: continue
        if ls.intersection(land).length > 0.5 * ls.length: stats['inside_landside_building'] += 1; continue
        w = num(t.get('width')); src = 'osm width'
        lanes = num(t.get('lanes'))
        if w is None and lanes: w = lanes * LANE_W; src = 'osm lanes x 3.6 m (inferred lane width)'
        if w is None: w = DEFAULT_W[t['highway']]; src = 'class default (inferred)'
        n_l = int(lanes) if lanes else max(1, int(round(w / LANE_W)))
        ways.append(dict(id=e['id'], nodes=list(e['nodes']), pts=np.array(pts), kind=t['highway'], layer=int(max(1, lay)) if lay >= 1 else 1,
                         bridge=t.get('bridge'), name=t.get('name'), oneway=t.get('oneway') in ('yes', '1', 'true', '-1'), lanes=n_l, w=float(w), w_src=src))
    log('elevated OSM ways %d: kept %d; not in the app (outside APT_RECT / airside) %d, garage aisles %d, inside a landside building %d'
        % (stats['osm_elevated'], len(ways), stats['not_in_app'], stats['garage_aisles'], stats['inside_landside_building']))
    stats['kept'] = len(ways)
    return ways, (grade_nodes, grade_ways), F, stats


def _insert(w, s_new, key):
    """insert a node (key) at arc length s_new into way w (pts, nodes); returns the node id there (an existing vertex
    within 0.3 m is used instead)"""
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(w['pts'], axis=0).T))])
    k = int(np.searchsorted(s, s_new))
    if k < len(s) and abs(s[k] - s_new) < 0.3: return w['nodes'][k]
    if k > 0 and abs(s[k - 1] - s_new) < 0.3: return w['nodes'][k - 1]
    a, b = w['pts'][k - 1], w['pts'][k]; t = (s_new - s[k - 1]) / max(s[k] - s[k - 1], 1e-9)
    w['pts'] = np.insert(w['pts'], k, a + t * (b - a), axis=0); w['nodes'].insert(k, key)
    return key


ELL_G = 45.0       # m, screening length of the at-grade roads' prior (h = 0): how fast a road leaving a bridge end returns to grade [inf]
NEAR_M = 260.0     # at-grade roads within this distance of an elevated way take part in the solve (farther ones stay at grade)


def solve_levels(ways, grade, F, LV, log=print, overhead=None):
    """deck-top level of every node of the elevated ways AND of the at-grade roads near them, in one screened solve (the
    header): elevated ways pulled to their layer prior (ELL), at-grade roads to grade (ELL_G), so the road leaving a bridge
    end rises to it (an approach ramp on fill) instead of the deck dropping to grade at the end; anchored curbs fixed.
    Crossing nodes (lines crossing without a shared node) carry the clearance constraints: deck over deck and deck over
    an at-grade road >= DECK_DEPTH + CLEAR_MIN (anchored levels kept, the other side moved; the higher OSM layer above).
    Every at-grade road with a node above 0.3 m becomes an approach ramp (w['ramp'] = True)."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    grade_nodes, grade_ways = grade
    dom = unary_union([g for (grp, u), g in F.items() if grp == 'domestic'])
    itb = F.get(('itb', 'hall'))
    h_dom = LV['domestic']['curb'] - KERB_M; h_itb = LV['itb']['curb'] - KERB_M
    for w in ways:
        ls = LineString(w['pts']); w['anchor'] = None; w['ramp'] = False
        if w['name'] == 'Departures' and w['layer'] == 1 and ls.distance(dom) < ANCHOR_DOM_M: w['anchor'] = 'domestic'
        elif itb is not None and w['layer'] == 2 and ls.distance(itb) < ANCHOR_ITB_M: w['anchor'] = 'itb'
    E = unary_union([LineString(w['pts']) for w in ways]).buffer(NEAR_M)
    G = []
    for gw in grade_ways:
        if len(gw['pts']) >= 2 and LineString(gw['pts']).intersects(E):
            G.append(dict(id=gw['id'], nodes=list(gw['nodes']), pts=gw['pts'].copy(), layer=0, anchor=None, ramp=False, at_grade=True, w=gw['w'], lanes=gw['lanes'], oneway=gw['oneway'], kind=gw['kind']))
    for w in ways: w['at_grade'] = False
    allw = ways + G
    # crossing nodes: elevated x elevated, elevated over at-grade (lines crossing without a shared node)
    X = []
    lines = [LineString(w['pts']) for w in allw]
    for i, a in enumerate(ways):
        for j in range(i + 1, len(allw)):
            b = allw[j]
            if set(a['nodes']) & set(b['nodes']): continue
            I = lines[i].intersection(lines[j])
            for p in (getattr(I, 'geoms', None) or ([I] if not I.is_empty else [])):
                if p.geom_type == 'Point': X.append((i, j, p))
    # overhead structures (the AirTrain guideway, landside asset): overhead = [(plan polygon, soffit_fn(x, z) -> world-y
    # above grade or None)]; every elevated way under one gets nodes there with an upper bound (deck top + CLEAR_MIN <= soffit)
    UB = []
    for poly, soff in (overhead or []):
        for i, a in enumerate(ways):
            la = LineString(a['pts'])
            if not la.intersects(poly): continue
            I = la.intersection(poly)
            for seg in (getattr(I, 'geoms', None) or [I]):
                if seg.is_empty or seg.length < 0.5: continue
                for f in (0.0, 0.5, 1.0):
                    q = seg.interpolate(f, normalized=True); so = soff(q.x, q.y)
                    if so is None: continue
                    UB.append((i, la.project(q), so - CLEAR_MIN, [round(q.x, 1), round(q.y, 1)], so))
    cons = []
    for k, (i, j, p) in enumerate(X):
        ka = _insert(allw[i], LineString(allw[i]['pts']).project(p), ('X', k))
        kb = _insert(allw[j], LineString(allw[j]['pts']).project(p), ('X', k, 'b'))
        cons.append((ka, kb, i, j, [round(p.x, 1), round(p.y, 1)]))
    ubn = []
    for k, (i, sq, ub, at, so) in enumerate(UB): ubn.append((_insert(allw[i], sq, ('U', k)), ub, at, so, i))
    nid = {}; xy = []
    for w in allw:
        for n, p in zip(w['nodes'], w['pts']):
            if n not in nid: nid[n] = len(xy); xy.append(p)
    xy = np.array(xy); N = len(xy)
    fixed = {}; why = {}
    for w in ways:
        if w['anchor']:
            for n in w['nodes']:
                if n in grade_nodes: continue  # where an anchored way meets an at-grade road its end follows the solve
                fixed[nid[n]] = h_dom if w['anchor'] == 'domestic' else h_itb; why[nid[n]] = 'domestic curb' if w['anchor'] == 'domestic' else 'ITB L3'
    anch = set(fixed)
    # at-grade roads that do not touch an elevated way stay at grade (only the way leaving a bridge end becomes its ramp)
    enodes = {n for w in ways for n in w['nodes']}
    for g in G:
        if set(g['nodes']) & enodes: continue
        for n in g['nodes']:
            if nid[n] not in fixed and n not in enodes: fixed[nid[n]] = 0.0; why[nid[n]] = 'at grade'
    grade_fixed = len(fixed) - len(anch)
    # the lowest anchored level of each connected elevated structure: a deck over an at-grade road inside an anchored
    # structure needs no more clearance than the anchored deck itself has (the domestic loop: the curb placeholder)
    par = list(range(len(ways)))
    def fnd(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    seen = {}
    for i, w in enumerate(ways):
        for n in w['nodes']:
            if n in seen: par[fnd(i)] = fnd(seen[n])
            else: seen[n] = i
    comp_lvl = {}
    for i, w in enumerate(ways):
        if w['anchor']: r = fnd(i); comp_lvl[r] = min(comp_lvl.get(r, 1e9), h_dom if w['anchor'] == 'domestic' else h_itb)
    sep_of = lambda i: min(DECK_DEPTH + CLEAR_MIN, comp_lvl.get(fnd(i), 1e9)) if i < len(ways) else DECK_DEPTH + CLEAR_MIN
    rows, cols, vals = [], [], []; wsum = np.zeros(N); rhs0 = np.zeros(N)
    for w in allw:
        ix = [nid[n] for n in w['nodes']]
        H, ell = (0.0, ELL_G) if w['at_grade'] else (LAYER_H.get(w['layer'], LAYER_H[1]), ELL)
        for a, b in zip(ix[:-1], ix[1:]):
            L = max(0.5, float(np.hypot(*(xy[a] - xy[b]))))
            k = 1.0 / L; rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [k, k, -k, -k]
            for q in (a, b): wsum[q] += L / 2 / ell ** 2; rhs0[q] += H * L / 2 / ell ** 2
    A = (sp.coo_matrix((vals, (rows, cols)), shape=(N, N)).tocsr() + sp.diags(wsum)).tocsr()
    def solve():
        free = np.array([i for i in range(N) if i not in fixed], int); fx = np.array(sorted(fixed), int); hv = np.array([fixed[i] for i in fx])
        h = np.zeros(N); h[fx] = hv
        if len(free): h[free] = spl.spsolve(A[free][:, free].tocsc(), rhs0[free] - (A[free][:, fx] @ hv if len(fx) else 0))
        return h
    SEP = DECK_DEPTH + CLEAR_MIN; unresolved = []
    for it in range(10):
        h = solve(); changed = False
        for ka, kb, i, j, at in cons:
            a, b = nid[ka], nid[kb]; wa, wb = allw[i], allw[j]
            la, lb = wa['layer'], wb['layer']
            up, lo = (a, b) if (la, h[a]) > (lb, h[b]) else (b, a)
            lo_g = allw[i if lo == a else j]['at_grade']
            sep = sep_of(i if up == a else j) if lo_g else SEP
            if h[up] - h[lo] >= sep - 1e-3: continue
            if up in anch and lo in anch: unresolved.append(dict(at=at, up=round(h[up], 2), lo=round(h[lo], 2))); continue
            if up in anch: fixed[lo] = max(0.0, h[up] - SEP); why[lo] = 'clearance under an anchored deck'
            elif lo in anch: fixed[up] = h[lo] + SEP; why[up] = 'clearance over an anchored deck'
            else:
                lo_at_grade = (allw[i if lo == a else j])['at_grade']
                if lo_at_grade: fixed[lo] = 0.0; fixed[up] = max(h[up], sep); why[lo] = 'at grade under a deck'; why[up] = 'clearance over an at-grade road'
                else:
                    # the upper deck goes up (the lower one usually has its own clearance over the roads under it: splitting
                    # the difference pushed it below them, 32 % steps in the first run)
                    fixed[up] = h[lo] + SEP; why[up] = 'clearance (deck over deck)'
            changed = True
        for a, ub, at, so, i in ubn:
            q = nid[a]
            if h[q] <= ub + 1e-3: continue
            if q in anch: unresolved.append(dict(kind='under the guideway', at=at, deck=round(h[q], 2), soffit=round(so, 2))); continue
            fixed[q] = max(0.0, ub); why[q] = 'clearance under the AirTrain guideway'; changed = True
        if not changed: break
    for w in allw:
        w['h'] = np.array([h[nid[n]] for n in w['nodes']])
        w['s'] = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(w['pts'], axis=0).T))])
        w['node_src'] = [why.get(nid[n], 'interpolated (%s)' % ('at-grade prior 0, ELL_G %.0f m' % ELL_G if w['at_grade'] else 'layer prior %.1f m, ELL %.0f m' % (LAYER_H.get(w['layer'], 6.5), ELL))) for n in w['nodes']]
    ramps = [g for g in G if g['h'].max() > 0.3]
    for g in ramps:
        g['ramp'] = True; g['name'] = None
        g['w_src'] = 'the at-grade OSM way\'s own width (lanes x 3.6 / class default)'
    log('levels: %d nodes (%d crossing nodes, %d under the guideway), %d anchored (%.2f m domestic curb, %.2f m ITB L3), %d held at grade, %d clearance '
        'constraints, %d solved; unresolved %d; approach ramps (the at-grade way leaving a bridge end, lifted > 0.3 m) %d'
        % (N, len(X), len(UB), len(anch), h_dom, h_itb, grade_fixed, len(fixed) - len(anch) - grade_fixed, N - len(fixed), len(unresolved), len(ramps)))
    return dict(h_dom=h_dom, h_itb=h_itb, N=N, anchored=len(anch), constraints=len(fixed) - len(anch), crossings=len(X), overhead=len(UB), unresolved=unresolved, ramps=ramps)


def h_at(w, s):
    return float(np.interp(s, w['s'], w['h']))


def checks(ways, ramps, log=print):
    """grades of decks and ramps; deck-to-deck and deck-over-road clearances at every crossing (the constraints'
    outcome); at-grade roads crossing a lifted ramp where it is above 0.3 m"""
    out = dict(grade=[], crossings=[], low=[])
    R = list(ways) + list(ramps)
    for w in R:
        dh = np.diff(w['h']); ds = np.maximum(np.diff(w['s']), 0.5); g = np.abs(dh / ds)
        if len(g): out['grade'].append(dict(id=w['id'], ramp=w.get('ramp', False), max_pct=round(float(g.max()) * 100, 1), at=[round(v, 1) for v in w['pts'][int(np.argmax(g))]]))
    lines = [LineString(w['pts']) for w in R]
    for i, a in enumerate(R):
        for j in range(i + 1, len(R)):
            b = R[j]
            if set(a['nodes']) & set(b['nodes']) - {n for n in a['nodes'] if isinstance(n, tuple)}: continue
            X = lines[i].intersection(lines[j])
            for p in (getattr(X, 'geoms', None) or ([X] if not X.is_empty else [])):
                if p.geom_type != 'Point': continue
                ha, hb = h_at(a, lines[i].project(p)), h_at(b, lines[j].project(p))
                c = dict(a=a['id'], b=b['id'], at=[round(p.x, 1), round(p.y, 1)], ha=round(ha, 2), hb=round(hb, 2), clear_m=round(abs(ha - hb) - DECK_DEPTH, 2))
                out['crossings'].append(c)
                if abs(ha - hb) < DECK_DEPTH + CLEAR_MIN - 0.05: out['low'].append(c)
    gm = sorted(out['grade'], key=lambda g: -g['max_pct'])
    if gm: log('grades: max %.1f %% (%s %s); decks > 8 %%: %d, ramps > 8 %%: %d' % (gm[0]['max_pct'], 'ramp' if gm[0]['ramp'] else 'deck', gm[0]['id'],
               sum(1 for g in gm if g['max_pct'] > 8 and not g['ramp']), sum(1 for g in gm if g['max_pct'] > 8 and g['ramp'])))
    log('crossings among decks and ramps: %d, below %.1f m clearance: %d' % (len(out['crossings']), CLEAR_MIN, len(out['low'])))
    return out
