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


def network(log=print, F=None):
    """F: {(group, unit): plan footprint}; default the stored integration.json footprints (build_roadways passes the ones
    it measured on the current GLBs)"""
    d = json.load(open(OSM)); L = json.load(open(os.path.join(ROOT, 'data', 'sfo_landside.json')))
    kept_elev = {r['osm_id'] for r in L['roads'] if r['elevated'] and not r.get('elevated_why')}
    why = {r['osm_id']: r['elevated_why'] for r in L['roads'] if r.get('elevated_why')}
    F = footprints() if F is None else F
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
# guideway clearance (review round 2, finding 5): bound sampled every UB_STEP along a way, UB_NX points across its ribbon
# (half width = carriageway / 2 + 0.6 m shoulder + 0.4 m parapet), a margin for the deck triangulation (the deck top is
# linear between the solve's nodes and across the triangles)
UB_STEP, UB_NX, UB_MARGIN = 2.0, 5, 0.05
# deck over deck (review round 2): the crossing constraint held the separation only at the two centrelines' crossing point;
# where two ribbons of different layers overlap at a skew the soffit-to-deck distance away from that point was 3.9-4.4 m
# (92 m2). Now the overlap of the two ribbons is sampled every X_STEP and each sample is a constraint pair (OVERLAP
# below); a flat margin on the separation (tried: 0.7 m) only steepened the ramps (max 16.9 %) and did not reach them
X_MARGIN = 0.0
X_STEP = 4.0
X_OVERLAP = False   # superseded by the per-crossing deficit (XS_* below). Tried (review round 2): 215 samples; with the stacked south legs of the ITB loop (OSM 41015123 under 38853121
                    # for ~45 m, both anchored at one end) the constraints conflict and the solve produced a 286 % step and MORE
                    # deck-over-deck area (230 m2 against 92 m2); off until the stacked legs are resolved (open item)
def ub_half(w): return w / 2 + 0.6 + 0.4


def shapely_coords(ln, step):
    """points along a LineString every `step` m, both ends included"""
    L = ln.length
    return [ln.interpolate(s).coords[0] for s in np.linspace(0.0, L, max(2, int(math.ceil(L / step)) + 1))]
# deck over deck at skewed crossings (review round 2): instead of a flat margin or a constraint per overlap sample, each
# centreline crossing keeps ONE constraint pair, and its separation is raised by the deficit measured over the overlap of
# the two ribbons (deck + parapet, sampled every XS_STEP; heights interpolated along each way at the sample's projection)
# after each solve, XS_ITER rounds at most, XS_CAP m at most per crossing: only the crossings that need it get steeper
# Samples within the crossing's parallelogram (+2 m). Two ways that meet at < XS_MIN_DEG run stacked along each other:
# their deficit counts only when it is within XS_CAP before any raise (the lower outer roadway OSM 739695588 under the
# layer-3 ramp 681667027 west of the ITB: 0.69 m over ~50 m, 89 m2 of deck at 3.9-4.6 m in the integration check r7);
# a larger one, or one with an anchored way (the deficit grows as the free way moves against the fixed one), is the trim's
# stacked cut (the ITB loop's lower outer roadway under its anchored departures leg: first run without the angle limit, a
# 3-m deficit there and a 64 % step on OSM 41015123; with the XS_CAP rule alone a 33 % step)
XS_STEP, XS_ITER, XS_CAP, XS_MIN_DEG = 2.0, 5, 1.5, 20.0
XS_TARGET = 0.0   # m over deck + clearance. Tried 0.1 (r10 left 3.7 m2 at 4.55-4.59 m: the deck top is linear between the solve's nodes,
                  # the samples XS_STEP apart): 72 crossings raised instead of 36, a 14.6 % grade, and 31.6 m2 at 2.59-4.6 m near (-1390, 308)
# stacked pairs (close-out round 3, fix round 2; verifier v1 / v2): two elevated ways of different OSM layers without a shared
# node whose ribbons (+ parapet) overlap in plan - a ramp running over the edge of a lower roadway (OSM 1205493778 over 739695588
# north of the ITB: 81 m2, 4.3-5.8 m deck to deck, no centreline crossing, so no constraint at all) or along it (681667027 over
# 739695588: 527 m2; the crossing deficit above raised ONE crossing node by up to 1.2 m for samples up to 90 m away - the 14.1 %
# hump at (-1423.8, 344.0)). Each pair's overlap is sampled every STK_STEP and every sample is a constraint (deck top to deck top
# >= DECK_DEPTH + CLEAR_MIN + STK_MARGIN) held by LOWERING the lower way's node there (the upper deck keeps its profile: raising it
# toward its anchored end steepened it to 15.6-27.8 % in the round-3 variants); a pair is constrained when the lower way is
# not anchored (the upper may be: the ITB loop's lower roadway under its anchored departures legs), the two are not a same-level merge (median separation >= 1 m) and the deficit before any change is <= STK_CAP; the
# lowering stays within STK_CAP of the free solve and never moves a node held by an anchor or a deck plate. What is left (an
# anchored way, a larger deficit, a held node) goes to build_roadways' stacked cut, which cuts along the upper deck's edge or
# reports the pair (stacked_cut_refused). Its crossings no longer take the per-crossing deficit raise (XS_*). The bound is spread along
# the lower way as a cone of slope STK_GRADE (the verifier's 'grade-limited smoothing pass on the stacked pair's nodes') [inf]
STK_STEP, STK_CAP, STK_MARGIN = 2.0, 2.0, 0.05
STK_FLOOR_MARGIN = 0.10   # m over the at-grade roads under a lowered way: the integration check samples their edges 0.3 m inside, where the
                          # deck is linear between nodes (fix 2: 41015123 lowered to 4.59 m over at-grade 93671776 with 0.05) [inf]
STK_FLOOR_FLAT = 4.0      # m: ... held flat this far either side of a crossing sample before the cone (the road's half-width: r21 dipped a node
                          # 2 m off the samples to 5.76 m, 4.59 m over 93671776's edge) [inf]
STK_RUN = 80.0     # m: a lowered stretch this close to a held node runs to it without a crest [inf]
STK_GRADE = 0.06   # the lowered profile's grade limit [inf]. Fix 2: 8 % (the grade the build reports decks against) left the curved
                   # ribbons' mesh at 8.0-9.7 % over ~150 m of 739695588 (the inner edge is shorter); 6 % holds the same 8 pairs with the same
                   # deficits left (solve variants SP c3/integration/f2/solve_g*.log), 739695588 at <= 6.0 % node grade


def solve_levels(ways, grade, F, LV, log=print, overhead=None, plates=None):
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
    # overhead structures (the AirTrain guideway, landside asset): overhead = [(plan polygon, soffit_fn(x, z) -> height
    # above grade or None)]; every way under one gets nodes there with an upper bound (deck top + CLEAR_MIN <= soffit).
    # Integration review round 2 (finding 5: decks 4.22-4.56 m under the guideway soffit, 150 m2 below 4.6 m): the bound was
    # sampled at three points per crossing on the centreline only, so between them (the deck is linear between nodes, the
    # soffit is not) and across the ribbon (the guideway slopes and turns over a 10-m deck) it was not enforced. Now a
    # hard bound every UB_STEP along the way wherever any of UB_NX points across the ribbon (deck edge + parapet
    # included) lies under the guideway, with the LOWEST soffit across the section; at-grade roads lifted into ramps too.
    UB = []
    for poly, soff in (overhead or []):
        pb = poly.buffer(ub_half(30.0)) if not poly.is_empty else poly
        for i, a in enumerate(allw):
            la = LineString(a['pts'])
            if not la.intersects(pb): continue
            half = ub_half(a['w']); L = la.length
            for sq in np.arange(0.0, L + 1e-6, UB_STEP) if L > 0 else []:
                q = la.interpolate(sq); q2 = la.interpolate(min(L, sq + 0.5)); q1 = la.interpolate(max(0.0, sq - 0.5))
                t = np.array([q2.x - q1.x, q2.y - q1.y]); t /= max(np.linalg.norm(t), 1e-9); nrm = np.array([-t[1], t[0]])
                so = [soff(q.x + nrm[0] * o, q.y + nrm[1] * o) for o in np.linspace(-half, half, UB_NX)]
                so = [s for s in so if s is not None]
                if not so: continue
                UB.append((i, sq, min(so) - CLEAR_MIN - UB_MARGIN, [round(q.x, 1), round(q.y, 1)], min(so)))
    # ribbon overlaps of elevated ways on DIFFERENT layers without a shared node (skewed crossings, a ramp running under a
    # deck for a stretch): sampled every X_STEP inside the overlap of their ribbons (+ parapet); each sample becomes a
    # constraint pair at the two centreline projections, as a crossing (review round 2)
    nX = len(X)
    for i, a in (enumerate(ways) if X_OVERLAP else []):
        ra = LineString(a['pts']).buffer(ub_half(a['w']), cap_style='flat')
        for j in range(i + 1, len(ways)):
            b = ways[j]
            if a['layer'] == b['layer'] or set(a['nodes']) & set(b['nodes']): continue
            rb = LineString(b['pts']).buffer(ub_half(b['w']), cap_style='flat')
            if not ra.intersects(rb): continue
            O = ra.intersection(rb)
            if O.area < 4.0: continue
            x0, z0, x1, z1 = O.bounds
            for x in np.arange(x0 + X_STEP / 2, x1, X_STEP):
                for z in np.arange(z0 + X_STEP / 2, z1, X_STEP):
                    if O.contains(Point(x, z)): X.append((i, j, Point(x, z)))
    log('deck crossings: %d centreline crossings, %d overlap samples (different layers, every %.0f m)' % (nX, len(X) - nX, X_STEP))
    cons = []
    for k, (i, j, p) in enumerate(X):
        ka = _insert(allw[i], LineString(allw[i]['pts']).project(p), ('X', k))
        kb = _insert(allw[j], LineString(allw[j]['pts']).project(p), ('X', k, 'b'))
        cons.append((ka, kb, i, j, [round(p.x, 1), round(p.y, 1)]))
    xsam = []   # per crossing: (s along way i, s along way j) of the overlap samples around the crossing point
    xstk = []   # per crossing: True when the two ways meet at < XS_MIN_DEG (stacked; see XS_MIN_DEG)
    stk_pre = set()
    for k, (i, j, p) in enumerate(X[:nX]):
        la, lb = LineString(allw[i]['pts']), LineString(allw[j]['pts'])
        O = la.buffer(ub_half(allw[i]['w']), cap_style='flat').intersection(lb.buffer(ub_half(allw[j]['w']), cap_style='flat'))
        O = [g for g in (getattr(O, 'geoms', None) or [O]) if isinstance(g, Polygon) and g.distance(p) < 1.0]
        S = []
        def tng(l):
            sp = l.project(p); q1, q2 = l.interpolate(max(0.0, sp - 1.0)), l.interpolate(min(l.length, sp + 1.0))
            t = np.array([q2.x - q1.x, q2.y - q1.y]); return t / max(np.linalg.norm(t), 1e-9)
        sn = abs(float(np.cross(tng(la), tng(lb))))                       # sin of the crossing angle
        xstk.append(sn < math.sin(math.radians(XS_MIN_DEG)))
        if xstk[-1] and any(allw[q].get('anchor') for q in (i, j)): stk_pre.add(k)   # stacked on an anchored way: the trim's
        rmax = (ub_half(allw[i]['w']) + ub_half(allw[j]['w'])) / max(sn, 1e-3) + 2.0
        if O:
            O = O[0]; x0, z0, x1, z1 = O.bounds
            for x in np.arange(x0 + XS_STEP / 2, x1, XS_STEP):
                for z in np.arange(z0 + XS_STEP / 2, z1, XS_STEP):
                    q = Point(x, z)
                    if O.contains(q) and q.distance(p) <= rmax: S.append((la.project(q), lb.project(q)))
        xsam.append(np.array(S).reshape(-1, 2))
    ubn = []
    for k, (i, sq, ub, at, so) in enumerate(UB): ubn.append((_insert(allw[i], sq, ('U', k)), ub, at, so, i))
    # stacked pairs (STK_*): stations every STK_STEP along the lower-layer way where its ribbon overlaps the upper one's; each
    # station gets a node on the lower way and the arc-length interval of the upper way over that cross-section of the overlap
    # (the lowest upper deck over it is the bound: one target per lower node, so the lowered profile follows the upper deck
    # smoothly - a 2-D grid of samples gave adjacent nodes different targets, 79 % steps). Pairs with a skewed crossing
    # (>= XS_MIN_DEG) keep the per-crossing deficit (XS_*), which works for a local overlap
    skew = set()
    for k, (i, j, p) in enumerate(X[:nX]):
        if not xstk[k]: skew.add(frozenset((i, j)))
    stk, stk_pairs = [], []
    rib = [LineString(w['pts']).buffer(ub_half(w['w']), cap_style='flat') for w in ways]
    for i, a in enumerate(ways):
        for j in range(i + 1, len(ways)):
            b = ways[j]
            if a['layer'] == b['layer'] or frozenset((i, j)) in skew or not rib[i].intersects(rib[j]): continue
            if (a if a['layer'] < b['layer'] else b)['anchor']: continue   # the lower way is moved: never an anchored one
            if {n for n in a['nodes'] if not isinstance(n, tuple)} & {n for n in b['nodes'] if not isinstance(n, tuple)}: continue
            O = rib[i].intersection(rib[j])
            if O.area < 1.0: continue
            lo, up = (i, j) if a['layer'] < b['layer'] else (j, i)
            Llo, Lup = LineString(ways[lo]['pts']), LineString(ways[up]['pts'])
            # the lower way's stations whose cross-section meets the overlap
            sa = [Llo.project(Point(c)) for g in (getattr(O, 'geoms', None) or [O]) if isinstance(g, Polygon) for c in g.exterior.coords]
            if not sa: continue
            half = ub_half(ways[lo]['w']) + 0.5; S = []
            for s in np.arange(max(0.0, min(sa)), min(Llo.length, max(sa)) + 1e-6, STK_STEP):
                q = Llo.interpolate(s); q2 = Llo.interpolate(min(Llo.length, s + 0.5)); q1 = Llo.interpolate(max(0.0, s - 0.5))
                t = np.array([q2.x - q1.x, q2.y - q1.y]); t /= max(np.linalg.norm(t), 1e-9); nrm = np.array([-t[1], t[0]])
                cs = LineString([(q.x - nrm[0] * half, q.y - nrm[1] * half), (q.x + nrm[0] * half, q.y + nrm[1] * half)]).intersection(O)
                pts = [c for g in (getattr(cs, 'geoms', None) or [cs]) if not g.is_empty and g.geom_type == 'LineString' for c in shapely_coords(g, 1.0)]
                if not pts: continue
                su = [Lup.project(Point(c)) for c in pts]
                S.append((s, min(su), max(su), [round(q.x, 1), round(q.y, 1)]))
            if not S: continue
            pk = len(stk_pairs); stk_pairs.append((lo, up))
            for sl, s1, s2, at in S: stk.append((_insert(ways[lo], sl, ('S', pk, round(sl, 2))), sl, lo, up, s1, s2, at, pk))
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
    # deck plates (review round 2, finding 1: the ITB departures deck measured on NAIP 2024, build_roadways.itb_plate):
    # every node of an elevated way inside a plate is held at the plate's level, so the ways that run onto it (the outer
    # light-concrete roadway, OSM layer 1) leave it at that level and their ends are solved as before
    nplate = 0
    for pl in (plates or []):
        pg = pl['poly'].buffer(0.5)
        for w in ways:
            for n, p in zip(w['nodes'], w['pts']):
                if n in grade_nodes or not pg.contains(Point(p)): continue
                if nid[n] not in fixed: nplate += 1
                fixed[nid[n]] = pl['h']; why[nid[n]] = pl['why']
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
    sep_of = lambda i: min(DECK_DEPTH + CLEAR_MIN + X_MARGIN, comp_lvl.get(fnd(i), 1e9)) if i < len(ways) else DECK_DEPTH + CLEAR_MIN + X_MARGIN
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
    SEP = DECK_DEPTH + CLEAR_MIN + X_MARGIN; unresolved = []; ub_bad = {}; xm = {}; stk_off = set(stk_pre)
    sk = []
    for w in allw: sk.append((np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(w['pts'], axis=0).T))]), np.array([nid[n] for n in w['nodes']])))
    def up_min(h, i, s1, s2):
        # the lowest deck top of way i over its arc-length interval [s1, s2] (piecewise linear: the ends and the nodes inside)
        si, ni = sk[i]; inner = h[ni[(si > s1) & (si < s2)]]
        return float(min(np.interp(s1, si, h[ni]), np.interp(s2, si, h[ni]), inner.min() if len(inner) else 1e9))
    def xdef(h, final=False):
        # separation deficit per crossing over its overlap samples (deck top to deck top against the base separation);
        # crossings already raised by XS_CAP are left as they are (but reported in the final count)
        out = {}
        for k, (ka, kb, i, j, at) in enumerate(cons):
            S = xsam[k] if k < len(xsam) else None
            if S is None or not len(S) or k in stk_off or (xm.get(k, 0.0) >= XS_CAP and not final): continue
            (si, ni), (sj, nj) = sk[i], sk[j]
            hi = np.interp(S[:, 0], si, h[ni]); hj = np.interp(S[:, 1], sj, h[nj])
            a, b = nid[ka], nid[kb]; upi = (allw[i]['layer'], h[a]) > (allw[j]['layer'], h[b])
            d = (hi - hj) if upi else (hj - hi)
            lo_g = allw[j if upi else i]['at_grade']
            sep = sep_of(i if upi else j) if lo_g else SEP
            dk = float(sep + XS_TARGET - d.min())
            # a stacked pair (< XS_MIN_DEG) whose deficit before any raise is beyond XS_CAP is the trim's stacked cut, not
            # this (the ITB loop's lower outer roadway under its anchored departures leg: 3 m, a 64 % step when raised)
            if xstk[k] and k not in xm and dk > XS_CAP and not final: stk_off.add(k); continue
            if dk > XS_TARGET + 0.02 or (not final and dk > 0.02): out[k] = dk
        return out
    SEPK = DECK_DEPTH + CLEAR_MIN + STK_MARGIN; stk_on = None; stk_low = {}
    # the floor of each elevated way over the at-grade roads it crosses (the crossing point and its overlap samples), for STK
    stk_floor = {}   # way index -> [(s on the way, at-grade way index, s on it)]
    for k, (i, j, p) in enumerate(X[:nX]):
        if i >= len(ways) or not allw[j].get('at_grade'): continue
        S_ = [(LineString(allw[i]['pts']).project(p), LineString(allw[j]['pts']).project(p))] + ([tuple(r) for r in xsam[k]] if k < len(xsam) and len(xsam[k]) else [])
        stk_floor.setdefault(i, []).extend((a_, j, b_) for a_, b_ in S_)
    def stk_decide(h):
        # which stacked pairs the solve holds (STK_*), decided on the first converged solve (crossing and guideway
        # constraints in place, no crossing deficit raised yet); their crossings drop the per-crossing deficit raise
        on = {}
        for pk, (lo, up) in enumerate(stk_pairs):
            d = np.array([up_min(h, u2, s1, s2) - h[nid[ka]] for ka, sl, l2, u2, s1, s2, at, q in stk if q == pk])
            dk = SEPK - float(d.min())
            if np.median(np.abs(d)) >= 1.0 and 0.0 < dk <= STK_CAP: on[pk] = dk
        on_pairs = {frozenset(stk_pairs[pk]) for pk in on}
        for k in range(nX):
            if frozenset((cons[k][2], cons[k][3])) in on_pairs: stk_off.add(k)
        return on
    for rnd in range(XS_ITER + 1):
      unresolved = []
      for it in range(20):
        h = solve(); changed = False
        for k, (ka, kb, i, j, at) in enumerate(cons):
            a, b = nid[ka], nid[kb]; wa, wb = allw[i], allw[j]
            la, lb = wa['layer'], wb['layer']
            up, lo = (a, b) if (la, h[a]) > (lb, h[b]) else (b, a)
            lo_g = allw[i if lo == a else j]['at_grade']
            sep = (sep_of(i if up == a else j) if lo_g else SEP) + xm.get(k, 0.0)
            if h[up] - h[lo] >= sep - 1e-3: continue
            if up in anch and lo in anch: unresolved.append(dict(at=at, up=round(h[up], 2), lo=round(h[lo], 2))); continue
            if up in anch: fixed[lo] = max(0.0, h[up] - sep); why[lo] = 'clearance under an anchored deck'
            elif lo in anch: fixed[up] = h[lo] + sep; why[up] = 'clearance over an anchored deck'
            else:
                lo_at_grade = (allw[i if lo == a else j])['at_grade']
                if lo_at_grade: fixed[lo] = 0.0; fixed[up] = max(h[up], sep); why[lo] = 'at grade under a deck'; why[up] = 'clearance over an at-grade road'
                else:
                    # the upper deck goes up (the lower one usually has its own clearance over the roads under it: splitting
                    # the difference pushed it below them, 32 % steps in the first run)
                    fixed[up] = h[lo] + sep; why[up] = 'clearance (deck over deck)'
            changed = True
        for a, ub, at, so, i in ubn:
            q = nid[a]
            if h[q] <= ub + 1e-3: continue
            if q in anch or (q in fixed and fixed[q] <= max(0.0, ub) + 1e-6):
                ub_bad[q] = dict(kind='under the guideway', at=at, deck=round(float(h[q]), 2), soffit=round(so, 2), anchored=q in anch); continue
            fixed[q] = max(0.0, ub); why[q] = 'clearance under the AirTrain guideway'; changed = True
        for pk in (stk_on or {}):
            # the bound under the upper deck at the pair's stations, spread along the lower way as a cone of slope STK_GRADE
            # (so the lowered stretch and its run-out stay within that grade: the lowering is spread, not a local dip)
            lo, up = stk_pairs[pk]; St = [(nid[ka], sl, up_min(h, u2, s1, s2) - SEPK) for ka, sl, l2, u2, s1, s2, at, q in stk if q == pk]
            ss = np.array([x[1] for x in St]); bb = np.array([x[2] for x in St])
            si, ni = sk[lo]
            o = np.argsort(ss); ss, bb = ss[o], bb[o]
            B = (bb[None, :] + STK_GRADE * np.abs(si[:, None] - ss[None, :])).min(1)
            inr = (si >= ss[0]) & (si <= ss[-1])   # between stations: the bounds' linear interpolation (no cone V at each station)
            B[inr] = np.minimum(B[inr], np.interp(si[inr], ss, bb))
            # no crest between the lowered stretch and a held node (anchor / plate) within STK_RUN: the free solve's layer
            # prior would lift the run between them (739695588: 5.80 at the lower level's end, 6.63 crest, 5.83 under the ramp)
            ha = np.array([n in anch for n in ni])
            for side, edge, bnd in ((-1, ss[0], bb[0]), (1, ss[-1], bb[-1])):
                sa_ = si[ha & ((si < edge) if side < 0 else (si > edge))]
                if not len(sa_): continue
                s_a = sa_.max() if side < 0 else sa_.min()
                if abs(edge - s_a) > STK_RUN: continue
                k_a = int(np.argmin(np.abs(si - s_a))); run = (si > min(s_a, edge)) & (si < max(s_a, edge))
                B[run] = np.minimum(B[run], max(bnd, h[ni[k_a]]))
            # and never more than STK_GRADE x the distance below a held node of the same way (an anchor, a deck plate, another
            # constraint): a lowered node beside the ITB lower level's held 5.80 m made a 264 % step; what cannot be met
            # within that is left to the trim's stacked cut
            held = np.array([n in anch or (n in fixed and n not in stk_low) for n in ni])
            if lo in stk_floor:   # nodes over an at-grade road's overlap are the crossing's (XS_*): held as they are
                fs0 = np.array([a_ for a_, j_, b_ in stk_floor[lo]])
                held |= (np.abs(si[:, None] - fs0[None, :]) < 2.0).any(1) & np.array([n not in stk_low for n in ni])
            if held.any():
                Lw = (h[ni[held]][None, :] - STK_GRADE * np.abs(si[:, None] - si[held][None, :])).max(1)
                B = np.maximum(B, Lw)
            # nor below its clearance over the at-grade roads it crosses (their overlap samples, the same cone): lowering the ITB
            # loop's lower roadway to 5.50 m under the departures legs put it 0.3 m below that, and the crossing deficit then
            # lifted the crossing nodes to 7.30 m between lowered neighbours (228 % steps)
            if lo in stk_floor:
                fs = np.array([a_ for a_, j_, b_ in stk_floor[lo]])
                fh = np.array([np.interp(b_, sk[j_][0], h[sk[j_][1]]) for a_, j_, b_ in stk_floor[lo]]) + sep_of(lo) + STK_FLOOR_MARGIN
                B = np.maximum(B, (fh[None, :] - STK_GRADE * np.maximum(0.0, np.abs(si[:, None] - fs[None, :]) - STK_FLOOR_FLAT)).max(1))
            for n, bnd, hd in zip(ni, B, held):
                if hd or h[n] <= bnd + 1e-3: continue
                if bnd < max(0.0, h_free[n] - STK_CAP) - 1e-6: continue   # beyond the cap: the trim's stacked cut
                fixed[n] = bnd; why[n] = 'clearance under a stacked deck (lowered, fix 2)'; stk_low[n] = (pk, h_free[n] - bnd); changed = True
        if not changed:
            if stk_on is None:
                h_free = h.copy(); stk_on = stk_decide(h)
                if stk_on: continue
            break
      dfc = xdef(h)
      if rnd == XS_ITER or not dfc: break
      for k, dk in dfc.items(): xm[k] = min(XS_CAP, xm.get(k, 0.0) + dk + 0.05)
    dfc = xdef(h, final=True)
    log('skewed crossings: %d of %d raised by the deficit over their ribbon overlap (max %.2f m, %d rounds; %d of them stacked, < %.0f deg); deficit left at %d (max %.2f m); '
        'stacked pairs left to the trim (on an anchored way, or deficit > %.1f m): %d %s'
        % (len(xm), len(cons), max(xm.values(), default=0.0), rnd, sum(1 for k in xm if xstk[k]), XS_MIN_DEG, len(dfc), max(dfc.values(), default=0.0),
           XS_CAP, len(stk_off), [(allw[cons[k][2]]['id'], allw[cons[k][3]]['id']) for k in sorted(stk_off)]))
    stk_on = stk_on if stk_on is not None else {}
    stk_rep = []
    for pk, (lo, up) in enumerate(stk_pairs):
        d = np.array([up_min(h, u2, s1, s2) - h[nid[ka]] for ka, sl, l2, u2, s1, s2, at, q in stk if q == pk])
        if pk in stk_on or (np.median(np.abs(d)) >= 1.0 and d.min() < SEPK - 1e-3):
            low = [v for q, v in stk_low.values() if q == pk]
            stk_rep.append(dict(lower=ways[lo]['id'], upper=ways[up]['id'], samples=int(len(d)), held=pk in stk_on, deficit_free_m=round(stk_on.get(pk, float('nan')), 2) if pk in stk_on else None,
                                lowered_nodes=len(low), lowered_max_m=round(max(low, default=0.0), 2), min_sep_m=round(float(d.min()), 2), left_m=round(max(0.0, SEP - float(d.min())), 2)))
    log('stacked pairs (fix 2, STK_*): %d sampled (%d samples), %d held by lowering the lower way (%d nodes, max %.2f m); left to the trim: %s'
        % (len(stk_pairs), len(stk), len(stk_on), len(stk_low), max((v for q, v in stk_low.values()), default=0.0),
           [(r['lower'], r['upper'], r['left_m']) for r in stk_rep if r['left_m'] > 0.0] or 'none'))
    # the guideway bounds the solve could not meet (anchored decks; a node held by another constraint), final values only
    ubq = {}
    for a, ub, *_ in ubn: ubq[nid[a]] = min(ub, ubq.get(nid[a], 1e9))
    unresolved += [u for q, u in ub_bad.items() if h[q] > ubq[q] + 1e-3]
    unresolved = list({(u.get('kind', 'crossing'), tuple(u['at'])): u for u in unresolved}.values())  # last (final) entry per place
    for w in allw:
        w['h'] = np.array([h[nid[n]] for n in w['nodes']])
        w['s'] = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(w['pts'], axis=0).T))])
        w['node_src'] = [why.get(nid[n], 'interpolated (%s)' % ('at-grade prior 0, ELL_G %.0f m' % ELL_G if w['at_grade'] else 'layer prior %.1f m, ELL %.0f m' % (LAYER_H.get(w['layer'], 6.5), ELL))) for n in w['nodes']]
    ramps = [g for g in G if g['h'].max() > 0.3]
    for g in ramps:
        g['ramp'] = True; g['name'] = None
        g['w_src'] = 'the at-grade OSM way\'s own width (lanes x 3.6 / class default)'
    log('levels: %d nodes (%d crossing nodes, %d guideway bound samples), %d anchored (%.2f m domestic curb, %.2f m ITB L3, %d on deck plates), %d held at grade, %d clearance '
        'constraints, %d solved; unresolved %d; approach ramps (the at-grade way leaving a bridge end, lifted > 0.3 m) %d'
        % (N, len(X), len(UB), len(anch), h_dom, h_itb, nplate, grade_fixed, len(fixed) - len(anch) - grade_fixed, N - len(fixed), len(unresolved), len(ramps)))
    return dict(h_dom=h_dom, h_itb=h_itb, N=N, anchored=len(anch), plate_nodes=nplate, constraints=len(fixed) - len(anch), crossings=len(X), overhead=len(UB), unresolved=unresolved, ramps=ramps,
                stacked=stk_rep)


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
