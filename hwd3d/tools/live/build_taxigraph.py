#!/usr/bin/env python3
"""HWD taxi graph for the live traffic engine -> data/hwd_taxigraph.json + data/hwd_taxigraph.js (TAXIGRAPH).

Replaces sfo3d/tools/live/build_taxigraph.py @ a967f9b (which read SFO's OSM extract into a segment soup). Kept: the
sfo3d-compatible `edges` segment soup ([x0, z0, x1, z1, wayIndex], read by js/live/traffic.js TaxiNet for its grid,
nearest-line matching and `paved` test), `ways[].kind` ('runway' marks runway segments), `halfWidth`, `aprons`; runway
centrelines from the FAA NASR ends, not OSM. New (format 'hwd-taxigraph/1', contract docs/phase2_fork_map.md 2.3): a
node/link graph for routing (dead reckoning across the recorder's 46-s holes must follow pavement, never cut across
grass or buildings), hold-short nodes, runway entry nodes, connectors from every parking spot / helipad / hangar side to
the network, wingspan limits, closed pavement and connectivity checks.

Inputs (all committed; same inputs -> byte-identical output):
  data/hwd_airport.json (Phase 1, frozen): taxiways + taxilanes (OSM, snapped to NAIP paint, junctions as shared
    vertices), runways (NASR ends, widths, outlines), holds, parking, helipads, hangars, buildings, aprons;
  refs/cache/osm/overpass_khwd_at_20261112T000000Z.json (the Phase 1 OSM pin, ODbL): the aerodrome boundary, car parks
    (amenity=parking) and fences (barrier=fence) only - to keep connectors airside;
  refs/cache/naip/naip_2024_hwd_rgb.jpg (USDA NAIP 2024, public domain) through tools/imagery/paintline.py Naip: the
    Phase 1 grey test for hard surface that OSM does not map (hangar fronts, the strip between an apron and a taxiway).
  (docs/phase2_fork_map.md 2.3 named data/hwd_airport.json as the only input; the two others were added because OSM
  aprons stop short of hangar fronts and taxiway edges, and leave three taxilane groups unjoined - docs/phase2_relay.md 6.)

Rules (each with its basis; [obs] = taken from the data, [inf] = a rule of this builder)
  ways      open taxiways and taxilanes are routable (status 'open': 61 + 78); 'abandoned' / 'disused' ways go to
            `closed` (not routable) [obs]. Width: the Phase 1 NAIP grey-test width where it is obs, else the AC default
            (10.67 m = 35 ft, AC 150/5300-13B Chg 1 Table 4-2, TDG 2A/2B) marked inf [obs/inf as in the data].
  junctions every vertex shared (to 0.01 m) by two or more open ways is a node (Phase 1 builds junctions as exactly
            shared vertices) [obs]; open ways that cross without a shared vertex are noded at the crossing (pavement is
            at grade) [inf]; a dead end within GAP_M (3 m) of another way is joined to it by a 'connector' link [inf].
  runways   centreline from the NASR ends (data runways[].ends x, z). A taxi line that crosses the centreline gets a
            node there on both; an end within TOUCH_M (1.5 m) of it is joined to its projection [inf]. Every taxi line
            is also cut where it crosses the runway outline (NASR rectangle, data runways[].outline): links inside it
            carry `runway` (that pavement is the runway: lead-on loops and the runway part of crossings; data
            on_runway) [obs geometry]. Runway nodes at both ends and at the displaced thresholds (thr) [obs].
  holds     each hold bar (data holds[], NAIP-measured) is projected onto its own way (holds[].way), else onto the
            nearest open way within 15 m [inf].
  wingspan  A1 <= 100 ft (30.48 m), Z1 <= 94 ft (28.65 m): ways[].max_span_m from the data (NASR remarks) [obs].
  pavement  for connectors: OSM aprons + taxi lines (width / 2 + 0.5 m) + helipads, minus car parks; elsewhere the
            NAIP 2024 grey test (2-m disc, median saturation < 0.16 and excess green < 8, = Phase 1 on_pavement) but only
            inside the aerodrome boundary and outside car parks, and at most NAIP_MAX_M (15 m) per connector unless it is
            the element's only way in (then `naip_long`). A leg may not cross > NONGREY_RUN_M (6 m) of NAIP non-grey
            (OSM apron polygons include some grass), a fence, a runway outline, or come within CLEAR_M (1.0 m) of a
            building / hangar footprint [inf].
  spots     each parking spot (177), helipad (9) and hangar side is joined to the network by a 'connector' link to a
            point of an open taxi line: the nearest candidate (per way: the closest point and points 5-40 m either side)
            whose straight leg passes the pavement rules; else a two-leg 'dogleg' via a waypoint on pavement (rings of
            8-60 m, 24 bearings, shortest total); else, for helicopter spots and helipads only, an 'air' link (hover /
            air taxi; clear of buildings and runways, not pavement-tested, `air: true`, not in `edges`). None found
            within MAX_CONN_M (150 m) -> node null + why_none [inf].
  hangars   door side unknown (NAIP does not show doors): both long sides of the minimum rectangle, 2 m out (all four
            when its aspect < 1.25; the short sides too when neither long side connects) [inf].
  islands   taxi lines that share no vertex with the network (OSM digitised three taxilane groups on aprons without a
            join) are joined by the shortest straight leg that passes the pavement rules, <= ISLAND_M (80 m) [inf].
  halfWidth 5.33 m: half of the 35-ft AC default width above [inf, AC 150/5300-13B Table 4-2] (TaxiNet.paved).
Licence: the output is a Derivative Database of data/hwd_airport.json and the OSM extract, ODbL 1.0 (OpenStreetMap
contributors; adsb.lol for the ADS-B-observed parking spots); NAIP and NASR are public domain.

usage: python3 tools/live/build_taxigraph.py [--plot]      # --plot also draws out/phase2/taxigraph*.png over NAIP 2024
"""
import argparse, hashlib, json, math, os, sys
from collections import defaultdict, deque

import numpy as np
from shapely.geometry import LineString, Point, Polygon, LinearRing
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
import hwd_frame as F  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'tools', 'imagery'))
from paintline import Naip  # noqa: E402  (committed NAIP 2024 mosaic, public domain; exact world->pixel fit)

SRC = os.path.join(ROOT, 'data', 'hwd_airport.json')
OSM_EXTRACT = os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_khwd_at_20261112T000000Z.json')   # Phase 1 pin
OUT_JSON = os.path.join(ROOT, 'data', 'hwd_taxigraph.json')
OUT_JS = os.path.join(ROOT, 'data', 'hwd_taxigraph.js')
GAP_M = 3.0          # dead end this close to another way: joined [inf]
TOUCH_M = 1.5        # taxi-line end this close to a runway centreline: joined to it [inf]
MERGE_M = 0.05       # cut points closer than this are one node
CLEAR_M = 1.0        # connector clearance from building / hangar footprints [inf]
MAX_CONN_M = 150.0   # longest spot / helipad connector [inf]
MAX_HANGAR_M = 150.0  # longest hangar-side connector (= spots) [inf]
SQUARE_ASPECT = 1.25  # a hangar footprint this close to square has no 'long' sides: all four are tried [inf]
HOLD_SNAP_M = 15.0
EDGE_MAX_M = 50.0    # `edges` segments are chopped to <= 50 m (TaxiNet grid cells are 40 m)
PAV_TOL_M = 0.5      # a connector leg may leave the pavement test by at most this much in total [inf]
NAIP_DISC_M = 2.0    # NAIP grey test disc radius (Phase 1 tools/build_airport.py on_pavement)
NAIP_STEP_M = 0.5    # sampling step of the grey test along a leg that leaves the OSM pavement
SAT_MAX, EG_MAX = 0.16, 8.0   # = tools/build_airport.py SAT_MAX / EG_MAX (aprons 0.04-0.14 saturation, grass 0.19-0.36)
DOGLEG_R = (8.0, 15.0, 25.0, 40.0, 60.0)   # waypoint rings of a two-leg connector [inf]
ISLAND_M = 80.0      # longest join of a taxi-line island to the main network [inf]
NONGREY_RUN_M = 6.0  # longest run of NAIP non-grey (vegetation) a connector leg may cross: paint, aircraft and shadows
                     # make runs of <= 5 m on the paved connectors here (measured 2026-11-13), grass inside an OSM apron
                     # polygon 22 m [inf]
NAIP_MAX_M = 15.0    # a connector may bridge at most this much unmapped (NAIP-grey-only) surface, unless it is the
                     # element's only way in (then flagged naip_long) [inf: OSM aprons stop short of hangar fronts and of
                     # the taxiway edge by up to ~13 m here]
MAX_AIR_M = 400.0    # helicopter spot / helipad without a ground connector: air link to the network up to this [inf]
HALF_WIDTH = round(10.67 / 2, 2)
ATTRIBUTION = ['© OpenStreetMap contributors (ODbL 1.0) - https://www.openstreetmap.org/copyright',
               'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL 1.0 '
               '(parking spots observed from ADS-B stays)',
               'Runways: FAA NASR (public domain)', 'Pavement test: USDA NAIP 2024 imagery (public domain)']


def r2(v): return round(float(v) + 0.0, 2)


def cum(P):
    P = np.asarray(P, float); d = np.hypot(*(P[1:] - P[:-1]).T); return np.concatenate([[0.0], np.cumsum(d)])


def point_at(P, S, s):
    s = min(max(s, 0.0), S[-1]); i = int(np.searchsorted(S, s, side='right') - 1); i = min(i, len(P) - 2)
    t = (s - S[i]) / max(S[i + 1] - S[i], 1e-12); return (P[i][0] + t * (P[i + 1][0] - P[i][0]), P[i][1] + t * (P[i + 1][1] - P[i][1]))


def sub_poly(P, S, s0, s1):
    out = [point_at(P, S, s0)]
    for i in range(len(P)):
        if s0 + 1e-6 < S[i] < s1 - 1e-6:
            out.append((P[i][0], P[i][1]))
    out.append(point_at(P, S, s1))
    return out


def poly_len(pts): return float(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])))


def compass(dx, dz):
    h = math.degrees(math.atan2(dx, -dz)) % 360
    return ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][int((h + 22.5) // 45) % 8]


def width_of(w):
    W = w.get('width') or {}
    if W.get('naip_src') == 'obs' and W.get('naip_grey_width_m'):
        return float(W['naip_grey_width_m']), 'obs'
    return float(W.get('default_m') or 10.67), 'inf'


class Nodes:
    """Cut points merged into nodes within MERGE_M (spatial hash)."""
    def __init__(self): self.xy, self.meta, self.h = [], [], defaultdict(list)
    def key(self, x, z): return (int(math.floor(x / 0.2)), int(math.floor(z / 0.2)))
    def get(self, x, z, **meta):
        kx, kz = self.key(x, z)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for i in self.h[(kx + dx, kz + dz)]:
                    if math.hypot(self.xy[i][0] - x, self.xy[i][1] - z) <= MERGE_M:
                        for k, v in meta.items():
                            self.meta[i].setdefault(k, v)
                        return i
        i = len(self.xy); self.xy.append((x, z)); self.meta.append(dict(meta)); self.h[(kx, kz)].append(i)
        return i


def landside():
    """From the pinned Phase 1 OSM extract (ODbL; the same file data/hwd_airport.json was built from): the aerodrome
    boundary (aeroway=aerodrome), car parks (amenity=parking: landside asphalt that the NAIP grey test cannot tell from an
    apron) and fences (barrier=fence: an aircraft never taxies through one). -> (aerodrome polygon, parking union, fence
    union, ids)"""
    d = json.load(open(OSM_EXTRACT))
    aero, park, fence, ids = [], [], [], {'aerodrome': [], 'parking': [], 'fence': []}
    for e in sorted((e for e in d['elements'] if e['type'] == 'way' and e.get('geometry')), key=lambda e: e['id']):
        t = e.get('tags') or {}
        pts = [F.wgs84_to_world(g['lat'], g['lon']) for g in e['geometry']]
        closed = len(pts) >= 4 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.01
        if t.get('aeroway') == 'aerodrome' and closed:
            aero.append(Polygon(pts).buffer(0)); ids['aerodrome'].append('osm:way/%d' % e['id'])
        elif t.get('amenity') == 'parking' and closed:
            park.append(Polygon(pts).buffer(0)); ids['parking'].append('osm:way/%d' % e['id'])
        elif t.get('barrier') == 'fence':
            fence.append(LineString(pts)); ids['fence'].append('osm:way/%d' % e['id'])
    return unary_union(aero), unary_union(park), unary_union(fence), ids


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--plot', action='store_true')
    ap.add_argument('--crop', action='append', default=[], metavar='NAME:X,Z,HW',
                    help='extra close-up plot centred on world x, z (m) with half-width HW (m); repeatable')
    ap.add_argument('--show-pavement', action='store_true', help='plots: shade the pavement mask the connectors are tested on')
    a = ap.parse_args()
    raw = open(SRC, 'rb').read(); sha = hashlib.sha256(raw).hexdigest(); A = json.loads(raw)
    osm_sha = hashlib.sha256(open(OSM_EXTRACT, 'rb').read()).hexdigest()
    naip_sha = hashlib.sha256(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.jpg'), 'rb').read()).hexdigest()
    allw = sorted(A['taxiways'] + A['taxilanes'], key=lambda w: (w['kind'], w['id']))
    OPEN = [w for w in allw if w['status'] == 'open']
    CLOSED = [w for w in allw if w['status'] != 'open']
    ways, lines = [], []          # ways[] output; lines[i] = (P, S, LineString) for routable polylines
    for w in OPEN:
        wd, ws = width_of(w)
        ways.append({'id': w['id'], 'ref': w.get('ref'), 'kind': w['kind'], 'width_m': r2(wd), 'width_src': ws,
                     'max_span_m': w.get('max_wingspan_m'), 'restriction': (w.get('restriction') or {}).get('text'),
                     'src': w.get('src', 'obs')})
        P = [tuple(p) for p in w['pts']]; lines.append((P, cum(P), LineString(P)))
    n_taxi = len(ways)
    rw = []                       # runway records
    for r in A['runways']:
        e0, e1 = r['ends']
        P = [(e0['x'], e0['z']), (e1['x'], e1['z'])]
        rect = Polygon(r['outline']['ring'])
        wi = len(ways)
        ways.append({'id': 'nasr:' + r['id'], 'ref': r['id'], 'kind': 'runway', 'width_m': r2(r['width_m']), 'width_src': 'obs',
                     'max_span_m': None, 'restriction': 'closed when the tower is closed (NASR remark)' if r.get('closed_when_tower_closed') else None,
                     'src': 'obs'})
        lines.append((P, cum(P), LineString(P)))
        rw.append({'id': r['id'], 'ends': [e0['id'], e1['id']], 'way': wi, 'P': P, 'rect': rect, 'prect': prep(rect),
                   'L': float(cum(P)[-1]), 'ends_rec': (e0, e1)})
    W_CONN = {}
    for k, why in (('gap', 'dead end within %.0f m of another way, or a taxi-line end within %.1f m of a runway centreline' % (GAP_M, TOUCH_M)),
                   ('spot', 'parking spot to the nearest clear paved point of the network'),
                   ('helipad', 'helipad centre to the nearest clear paved point of the network'),
                   ('hangar', 'hangar long side (2 m out) to the nearest clear paved point of the network'),
                   ('island', 'taxi lines sharing no vertex with the network (OSM digitised them on an apron without a '
                              'join) to the nearest clear paved point of the network, max %.0f m' % ISLAND_M),
                   ('air', 'helicopter spot or helipad with no paved connector: hover/air-taxi link to the nearest '
                           'network point clear of buildings and runways (not for fixed-wing routing)')):
        W_CONN[k] = len(ways)
        ways.append({'id': 'conn:' + k, 'ref': None, 'kind': 'connector', 'width_m': None, 'width_src': 'inf',
                     'max_span_m': None, 'restriction': None, 'src': 'inf', 'rule': why, 'air_only': k == 'air',
                     'pavement': None if k == 'air' else 'OSM aprons / taxi lines (width / 2 + 0.5 m) / helipads, '
                                 'or NAIP 2024 grey (Phase 1 test, unmapped hard surface)'})

    nodes = Nodes()
    cuts = defaultdict(list)      # way index -> [(s, node)]
    extra_links = []              # (a, b, way index, pts, runway)

    def cut(wi, s, **meta):
        P, S, _ = lines[wi]; x, z = point_at(P, S, s)
        n = nodes.get(x, z, **meta); cuts[wi].append((float(s), n)); return n

    # (a) ends and shared vertices of open ways
    vmap = defaultdict(list)
    for wi in range(n_taxi):
        P, S, _ = lines[wi]
        for j, p in enumerate(P):
            vmap[(round(p[0], 2), round(p[1], 2))].append((wi, j))
    shared = {k: v for k, v in vmap.items() if len({wi for wi, _ in v}) >= 2}
    for wi in range(n_taxi):
        P, S, _ = lines[wi]
        cut(wi, 0.0); cut(wi, S[-1])
    for k, v in shared.items():
        for wi, j in v:
            cut(wi, lines[wi][1][j])
    # closed ways too, for the reconcile count only
    vmap_all = defaultdict(set)
    for w in allw:
        for p in w['pts']:
            vmap_all[(round(p[0], 2), round(p[1], 2))].add(w['id'])
    shared_all = sum(1 for v in vmap_all.values() if len(v) >= 2)
    # (b) crossings without a shared vertex
    n_cross = 0
    for i in range(n_taxi):
        for j in range(i + 1, n_taxi):
            Li, Lj = lines[i][2], lines[j][2]
            if not Li.intersects(Lj):
                continue
            g = Li.intersection(Lj)
            pts = [g] if g.geom_type == 'Point' else [q for q in getattr(g, 'geoms', []) if q.geom_type == 'Point']
            for q in pts:
                if (round(q.x, 2), round(q.y, 2)) in shared:
                    continue
                if any(math.hypot(q.x - lines[i][0][k][0], q.y - lines[i][0][k][1]) < MERGE_M for k in (0, -1)) and \
                   any(math.hypot(q.x - lines[j][0][k][0], q.y - lines[j][0][k][1]) < MERGE_M for k in (0, -1)):
                    continue                     # ends meeting: already shared
                n = cut(i, Li.project(q)); cuts[j].append((Lj.project(q), n)); nodes.meta[n].setdefault('crossing', True)
                n_cross += 1
    # (d) runway centrelines and (e) outlines
    rw_nodes = defaultdict(list)  # runway index -> [(along, node)]
    for k, R in enumerate(rw):
        wi = R['way']; CL = lines[wi][2]
        for name, s in ((R['ends'][0], 0.0), (R['ends'][1], R['L'])):
            n = cut(wi, s, kind='runway', runway=R['id'], end=name); rw_nodes[k].append((s, n))
        for e in R['ends_rec']:
            if e.get('displaced_threshold'):
                tx, tz = F.thr_world(e['id'])
                s = CL.project(Point(tx, tz)); n = cut(wi, s, kind='runway', runway=R['id'], thr=e['id']); rw_nodes[k].append((s, n))
        ring = LinearRing(R['rect'].exterior.coords)
        for ti in range(n_taxi):
            L = lines[ti][2]
            if not L.intersects(R['rect']):
                continue
            g = L.intersection(CL)
            pts = [g] if g.geom_type == 'Point' else [q for q in getattr(g, 'geoms', []) if q.geom_type == 'Point']
            for q in pts:
                s_r = CL.project(q); x, z = point_at(lines[wi][0], lines[wi][1], s_r)
                n = nodes.get(x, z, kind='runway', runway=R['id'])
                cuts[wi].append((s_r, n)); cuts[ti].append((L.project(q), n)); rw_nodes[k].append((s_r, n))
            for end in (0, -1):
                p = Point(lines[ti][0][end])
                if CL.distance(p) <= TOUCH_M and not any(CL.distance(Point(q.x, q.y)) < 1e-6 and p.distance(q) < MERGE_M for q in pts):
                    s_r = CL.project(p)
                    if 0.0 < s_r < R['L']:
                        x, z = point_at(lines[wi][0], lines[wi][1], s_r)
                        nr = nodes.get(x, z, kind='runway', runway=R['id']); cuts[wi].append((s_r, nr)); rw_nodes[k].append((s_r, nr))
                        nt = cut(ti, 0.0 if end == 0 else lines[ti][1][-1])
                        if nr != nt:
                            extra_links.append((nt, nr, W_CONN['gap'], [nodes.xy[nt], nodes.xy[nr]], R['id']))
            gb = L.intersection(ring)
            bpts = [gb] if gb.geom_type == 'Point' else [q for q in getattr(gb, 'geoms', []) if q.geom_type == 'Point']
            for q in bpts:
                cut(ti, L.project(q), kind='runway_edge', runway=R['id'])
    # (c) dead ends near another way
    deg_ways = defaultdict(set)
    for k, v in vmap.items():
        for wi, j in v:
            deg_ways[k].add(wi)
    n_gap = 0
    for wi in range(n_taxi):
        P = lines[wi][0]
        for end in (0, -1):
            k = (round(P[end][0], 2), round(P[end][1], 2))
            if len(deg_ways[k]) >= 2:
                continue
            p = Point(P[end]); best = None
            for wj in range(n_taxi):
                if wj == wi:
                    continue
                d = lines[wj][2].distance(p)
                if d <= GAP_M and (best is None or d < best[0]):
                    best = (d, wj)
            if best and best[0] > MERGE_M:
                s = lines[best[1]][2].project(p)
                na = cut(wi, 0.0 if end == 0 else lines[wi][1][-1]); nb = cut(best[1], s)
                extra_links.append((na, nb, W_CONN['gap'], [nodes.xy[na], nodes.xy[nb]], None)); n_gap += 1
            elif best:
                cut(best[1], lines[best[1]][2].project(p))
    # (f) holds
    holds_out, holds_unatt = [], []
    by_id = {w['id']: i for i, w in enumerate(ways[:n_taxi])}
    for h in sorted(A['holds'], key=lambda h: h['id']):
        b = h.get('bar') or {}; hx, hz = b.get('x', h['x']), b.get('z', h['z'])
        wi = by_id.get(h.get('way')); p = Point(hx, hz)
        if wi is None or lines[wi][2].distance(p) > HOLD_SNAP_M:
            cand = sorted((lines[j][2].distance(p), j) for j in range(n_taxi))
            wi = cand[0][1] if cand and cand[0][0] <= HOLD_SNAP_M else None
        if wi is None:
            holds_unatt.append(h['id']); continue
        s = lines[wi][2].project(p); n = cut(wi, s, kind='hold', hold=h['id'], runway=h['runway'])
        holds_out.append({'id': h['id'], 'node': n, 'runway': h['runway'], 'x': r2(hx), 'z': r2(hz), 'dir': b.get('dir'),
                          'cl_dist_m': h.get('cl_dist_m'), 'snap_m': r2(lines[wi][2].distance(p)), 'way': wi, 'src': h.get('src', 'obs')})
    # pavement and obstacles for connectors
    taxi_buf = [lines[i][2].buffer(ways[i]['width_m'] / 2 + 0.5, cap_style=2) for i in range(n_taxi)]
    AERO, PARK, FENCE, land_ids = landside()
    pav_osm = unary_union([Polygon(x['ring']) for x in A['aprons']] + taxi_buf + [Polygon(x['ring']).buffer(0.5) for x in A['helipads']])
    park_overlap = pav_osm.intersection(PARK).area
    pav = pav_osm.difference(PARK)
    PAV = prep(pav); PAERO = prep(AERO); PPARK = prep(PARK); PFENCE = prep(FENCE)
    global PAVEMENT
    PAVEMENT = pav
    obst = [(o['id'], Polygon(o['ring'])) for o in A['buildings'] + A['hangars'] if len(o.get('ring') or []) >= 3]
    OBST = dict(obst)
    OB = unary_union([g for _, g in obst])
    rects = unary_union([R['rect'] for R in rw]); PR = prep(rects)
    naip = Naip('2024')
    dg = np.linspace(-NAIP_DISC_M, NAIP_DISC_M, 9); DX, DZ = np.meshgrid(dg, dg)
    msk = np.hypot(DX, DZ) <= NAIP_DISC_M; DX, DZ = DX[msk], DZ[msk]
    stat = defaultdict(int)

    def naip_grey(xs, zs):
        """NAIP 2024 grey test of Phase 1 (tools/build_airport.py on_pavement): median saturation < SAT_MAX and median
        excess green < EG_MAX in a 2-m disc around each point -> bool array"""
        X = np.asarray(xs, float)[:, None] + DX[None, :]; Z = np.asarray(zs, float)[:, None] + DZ[None, :]
        R_, G_, B_ = (naip.sample(X, Z, k) for k in 'RGB')
        mx = np.maximum(np.maximum(R_, G_), B_); mn = np.minimum(np.minimum(R_, G_), B_)
        sat = np.median((mx - mn) / np.maximum(mx, 1.0), axis=1); eg = np.median(G_ - (R_ + B_) / 2.0, axis=1)
        return (sat < SAT_MAX) & (eg < EG_MAX)

    def seg_pavement(a, b):
        """-> (metres on neither OSM pavement nor NAIP grey, metres accepted by the NAIP grey test only)"""
        seg = LineString([a, b])
        off = seg.difference(pav)
        if off.length <= PAV_TOL_M:
            return off.length, 0.0
        pts = []
        for g in getattr(off, 'geoms', [off]):
            if g.length < 1e-6:
                continue
            n = max(1, int(math.ceil(g.length / NAIP_STEP_M)))
            for i in range(n):
                q = g.interpolate((i + 0.5) / n, normalized=True); pts.append((q.x, q.y, g.length / n))
        arr = np.array(pts); ok = naip_grey(arr[:, 0], arr[:, 1])
        for k_, (qx, qz, _) in enumerate(pts):      # airside only: inside the aerodrome boundary, never a car park
            if ok[k_] and (not PAERO.contains(Point(qx, qz)) or PPARK.contains(Point(qx, qz))):
                ok[k_] = False
        return float(arr[~ok, 2].sum()), float(arr[ok, 2].sum())

    def leg(a, b, own=None, air=False, cap=None):
        """One straight connector leg a -> b. -> (None, clearance, naip_m) when acceptable, else (reason, ...)."""
        seg = LineString([a, b]); d = seg.length
        if PR.intersects(seg) and not PR.contains(Point(a)):
            return 'enters a runway', None, 0.0
        if PFENCE.intersects(seg):
            return 'crosses a fence', None, 0.0
        if own is None:
            clr = seg.distance(OB)
        else:   # the first 1.5 m from the own hangar's side are exempt (the side point is 2 m out)
            clr = seg.distance(unary_union([g for i, g in obst if i != own]))
            if d > 1.5:
                clr = min(clr, LineString([seg.interpolate(1.5), b]).distance(OBST[own]))
        if clr < CLEAR_M:
            return 'building clearance', clr, 0.0
        if air:
            return None, clr, 0.0
        off, nm = seg_pavement(a, b)
        if off > PAV_TOL_M:
            return 'off pavement', clr, nm
        if cap is not None and nm > cap:
            return 'NAIP-only stretch > %.0f m' % cap, clr, nm
        if d > NONGREY_RUN_M:          # OSM apron polygons include some grass: NAIP must not see vegetation on the leg
            n = int(math.ceil(d / 1.0)); t = (np.arange(n) + 0.5) / n
            ok = naip_grey(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            run = best = 0
            for v in ok:
                run = 0 if v else run + 1; best = max(best, run)
            if best * d / n > NONGREY_RUN_M:
                return 'vegetation on the leg (NAIP)', clr, nm
        return None, clr, nm

    def connector(x, z, maxd, own=None, air=False, ways_ok=None, cap=NAIP_MAX_M):
        """Straight connector from (x, z) to the nearest acceptable point of an open taxi line.
        -> ((way index, s, (px, pz), length, clearance, naip_m), None) or (None, reason)."""
        p = Point(x, z); cands = []
        for wi in (range(n_taxi) if ways_ok is None else ways_ok):
            L = lines[wi][2]; d0 = L.distance(p)
            if d0 > maxd:
                continue
            s0 = L.project(p)
            for ds in (0, -5, 5, -10, 10, -20, 20, -40, 40):
                s = min(max(s0 + ds, 0.0), L.length); q = L.interpolate(s)
                cands.append((p.distance(q), wi, s, (q.x, q.y)))
        if not cands:
            return None, f'no open taxi line within {maxd:.0f} m'
        cands.sort(key=lambda c: (round(c[0], 3), c[1], c[2])); why = defaultdict(int); done = set()
        for d, wi, s, q in cands:
            if d > maxd:
                break
            k = (wi, round(s, 2))
            if k in done:
                continue
            done.add(k)
            if d < 0.05:
                return (wi, s, q, d, None, 0.0), None
            r, clr, nm = leg((x, z), q, own, air, cap)
            if r:
                why[r] += 1; continue
            return (wi, s, q, d, clr, nm), None
        return None, 'no clear %sstraight line within %.0f m (%s)' % ('' if air else 'paved ', maxd,
                                                                         ', '.join(f'{k}: {v}' for k, v in sorted(why.items())) or 'none tried')

    def dogleg(x, z, maxd, own=None, cap=NAIP_MAX_M):
        """Two legs via a waypoint on pavement (rings of DOGLEG_R m, 24 bearings) when no straight connector exists.
        -> ((way index, s, (px, pz), total length, clearance, naip_m, waypoint), None) or (None, reason)."""
        best = None
        for r in DOGLEG_R:
            for k in range(24):
                a = math.radians(15.0 * k); wx, wz = x + r * math.sin(a), z - r * math.cos(a)
                if not (PAV.contains(Point(wx, wz)) or (PAERO.contains(Point(wx, wz)) and not PPARK.contains(Point(wx, wz))
                                                        and naip_grey([wx], [wz])[0])):
                    continue
                if best is not None and r >= best[3]:
                    continue
                e, c1, n1 = leg((x, z), (wx, wz), own, cap=cap)
                if e:
                    continue
                res, _ = connector(wx, wz, maxd - r, cap=None if cap is None else cap - n1)
                if res is None:
                    continue
                wi, s, q, d, c2, n2 = res
                tot = r + d
                if best is None or tot < best[3] - 1e-6:
                    best = (wi, s, q, tot, min(c1, c2 if c2 is not None else 99.0), n1 + n2, (wx, wz))
        return (best, None) if best else (None, 'no two-leg paved route via a waypoint within %.0f m either' % maxd)

    def join(xy, maxd, own=None, wconn=None, kind=None, air_ok=False, cap=NAIP_MAX_M, **meta):
        """Connect a point to the network: straight, else dog-leg, else (helicopters) an air link. `cap`: the most a
        connector may rely on the NAIP grey test alone (None: no cap, the caller's last resort).
        -> (output record fields, node or None, reason or None)"""
        x, z = xy
        res, why = connector(x, z, maxd, own, cap=cap)
        via = None; mode = 'straight'; why2 = None
        if res is None:
            r2_, why2 = dogleg(x, z, maxd, own, cap=cap)
            if r2_ is not None:
                wi, s, q, d, clr, nm, via = r2_; res = (wi, s, q, d, clr, nm); mode = 'dogleg'
            elif air_ok:
                r3, why3 = connector(x, z, MAX_AIR_M, own, air=True)
                if r3 is not None:
                    res = r3; mode = 'air'
                else:
                    why = why + '; ' + why3
            if res is None:
                return {}, None, why + ('; ' + why2 if why2 else '')
        wi, s, q, d, clr, nm = res
        nt = cut(wi, s)
        pts = [(x, z)] + ([via] if via else []) + [q]
        if d < MERGE_M:
            n0 = nt
            for k_, v_ in meta.items():
                nodes.meta[n0].setdefault(k_, v_)
        else:
            n0 = nodes.get(x, z, kind=kind, **meta)
            if n0 != nt:
                extra_links.append((n0, nt, W_CONN['air'] if mode == 'air' else wconn, pts, None))
        stat[mode] += 1
        if nm > 0.05:
            stat['naip_legs'] += 1; stat['naip_m'] += nm
        rec = {'attach': nt, 'len': r2(d), 'pts': [[r2(a_), r2(b_)] for a_, b_ in pts], 'clear_m': r2(clr) if clr is not None else None,
               'way': wi, 'mode': mode, 'naip_m': r2(nm)}
        if cap is None and nm > NAIP_MAX_M:
            rec['naip_long'] = True; stat['naip_long'] += 1
        return rec, n0, None

    spots_out, conn_lens = [], []
    for sp in sorted(A['parking'], key=lambda s: s['id']):
        x, z = sp['x'], sp['z']
        heli = sp['kind'] == 'helipad'
        rec = {'id': sp['id'], 'kind': sp['kind'], 'src': sp['src'], 'x': r2(x), 'z': r2(z), 'node': None, 'attach': None,
               'len': None, 'pts': None}
        inside = [i for i, g in obst if g.contains(Point(x, z))]
        if inside:
            rec['inside'] = inside[0]
        f, n0, why = join((x, z), MAX_CONN_M, wconn=W_CONN['spot'], kind='helipad' if heli else 'spot', air_ok=False, spot=sp['id'])
        if n0 is None:
            f, n0, why = join((x, z), MAX_CONN_M, wconn=W_CONN['spot'], kind='helipad' if heli else 'spot', air_ok=heli,
                              cap=None, spot=sp['id'])
        if n0 is None:
            rec['why_none'] = why
        else:
            rec.update(f, node=n0); conn_lens.append(f['len'])
        spots_out.append(rec)
    heli_out = []
    for hp in sorted(A['helipads'], key=lambda h: h['id']):
        rec = {'id': hp['id'], 'x': r2(hp['x']), 'z': r2(hp['z']), 'node': None, 'attach': None, 'len': None}
        f, n0, why = join((hp['x'], hp['z']), MAX_CONN_M, wconn=W_CONN['helipad'], kind='helipad', air_ok=False, helipad=hp['id'])
        if n0 is None:
            f, n0, why = join((hp['x'], hp['z']), MAX_CONN_M, wconn=W_CONN['helipad'], kind='helipad', air_ok=True, cap=None,
                              helipad=hp['id'])
        if n0 is None:
            rec['why_none'] = why
        else:
            rec.update(f, node=n0)
        heli_out.append(rec)
    hang_out = []
    for hg in sorted(A['hangars'], key=lambda h: h['id']):
        poly = Polygon(hg['ring']); mrr = poly.minimum_rotated_rectangle; c = list(mrr.exterior.coords)[:4]
        allsides = sorted(((math.hypot(c[(i + 1) % 4][0] - c[i][0], c[(i + 1) % 4][1] - c[i][1]), i) for i in range(4)), reverse=True)
        aspect = allsides[0][0] / max(allsides[-1][0], 1e-6)
        cx, cz = poly.centroid.x, poly.centroid.y; acc = []

        def try_side(i, role, cap=NAIP_MAX_M):
            a_, b_ = c[i], c[(i + 1) % 4]; mx, mz = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
            nx, nz = mx - cx, mz - cz; nl = math.hypot(nx, nz) or 1.0; nx, nz = nx / nl, nz / nl
            px, pz = mx + 2.0 * nx, mz + 2.0 * nz
            side = {'side': compass(nx, nz), 'role': role, 'x': r2(px), 'z': r2(pz), 'node': None, 'attach': None}
            f, n0, why = join((px, pz), MAX_HANGAR_M, own=hg['id'], wconn=W_CONN['hangar'], kind='hangar', cap=cap,
                              hangar=hg['id'], side=side['side'])
            if n0 is None:
                side['why_none'] = why
            else:
                side.update(f, node=n0)
            acc.append(side)
        first = [i for _, i in allsides] if aspect < SQUARE_ASPECT else [i for _, i in allsides[:2]]
        for i in sorted(first):
            try_side(i, 'long' if aspect >= SQUARE_ASPECT else 'square')
        if aspect >= SQUARE_ASPECT and not any(sd['node'] is not None for sd in acc):
            for i in sorted(i for _, i in allsides[2:]):
                try_side(i, 'short')
        if not any(sd['node'] is not None for sd in acc):      # last resort: longer NAIP-only stretches (flagged)
            tried = acc[:]; acc.clear()
            for sd, i in zip(tried, [i for i in sorted(first)] + ([i for i in sorted(i for _, i in allsides[2:])]
                                                                     if aspect >= SQUARE_ASPECT else [])):
                try_side(i, sd['role'], cap=None)
        hang_out.append({'id': hg['id'], 'name': hg.get('name'), 'kind': hg.get('kind'), 'src': 'inf', 'aspect': r2(aspect),
                         'access': acc,
                         'rule': 'door side not known (Phase 1: doors not visible on NAIP); both long sides of the minimum '
                                 'rectangle (all four when its aspect < %.2f; the short sides too when neither long side '
                                 'connects), 2 m out, joined like spots (max %.0f m)' % (SQUARE_ASPECT, MAX_HANGAR_M)})

    def make_links():
        """links along ways (between consecutive cut nodes) + extra links, deduplicated"""
        out = []
        for wi in sorted(cuts):
            P, S, L = lines[wi]
            cs = sorted(set((round(s, 4), n) for s, n in cuts[wi]))
            seq = []
            for s, n in cs:
                if seq and seq[-1][1] == n:
                    continue
                if seq and abs(s - seq[-1][0]) < 1e-6:
                    continue
                seq.append((s, n))
            for (s0, n0), (s1, n1) in zip(seq, seq[1:]):
                if n0 == n1:
                    continue
                pts = sub_poly(P, S, s0, s1)
                runway = None
                if ways[wi]['kind'] == 'runway':
                    runway = ways[wi]['ref']
                else:
                    mid = Point(point_at(P, S, (s0 + s1) / 2))
                    for R in rw:
                        if R['prect'].contains(mid):
                            runway = R['id']
                out.append((n0, n1, wi, pts, runway))
        out += extra_links
        seen, L2 = set(), []
        for l in out:
            k = (min(l[0], l[1]), max(l[0], l[1]), l[2], round(poly_len(l[3]), 2))
            if k in seen:
                continue
            seen.add(k); L2.append(l)
        return L2

    def components(lk):
        adj_ = defaultdict(set)
        for a_, b_, *_ in lk:
            adj_[a_].add(b_); adj_[b_].add(a_)
        comp_, k = {}, 0
        for s0 in sorted(adj_):
            if s0 in comp_:
                continue
            q = deque([s0]); comp_[s0] = k
            while q:
                u = q.popleft()
                for v in adj_[u]:
                    if v not in comp_:
                        comp_[v] = k; q.append(v)
            k += 1
        return comp_

    # islands: taxilane groups that share no vertex with the rest (OSM digitised them on an apron without a join) are
    # joined by the shortest straight paved, clear line from one of their taxi nodes to the main network [inf]
    islands_joined = []
    for _ in range(20):
        links = make_links()
        comp = components(links)
        size = defaultdict(int)
        for v in comp.values():
            size[v] += 1
        main_c = max(size, key=lambda k: (size[k], -k))
        way_comp = {}
        for a_, b_, wi, pts, rwy in links:
            if wi < n_taxi:
                way_comp[wi] = comp[a_]
        main_ways = sorted(wi for wi, c_ in way_comp.items() if c_ == main_c)
        best = None
        for c_ in sorted(set(way_comp.values()) - {main_c}):
            cand_nodes = sorted({n for a_, b_, wi, pts, rwy in links if wi < n_taxi and comp[a_] == c_ for n in (a_, b_)})
            for n in cand_nodes:
                res, _ = connector(*nodes.xy[n], ISLAND_M, ways_ok=main_ways)
                if res is not None and (best is None or res[3] < best[1][3] - 1e-6):
                    best = (n, res, c_)
        if best is None:
            break
        n, (wi, s, q, d, clr, nm), c_ = best
        nt = cut(wi, s)
        extra_links.append((n, nt, W_CONN['island'], [nodes.xy[n], q], None))
        islands_joined.append({'from': [r2(nodes.xy[n][0]), r2(nodes.xy[n][1])], 'to_way': ways[wi]['id'], 'len': r2(d),
                               'clear_m': r2(clr) if clr is not None else None, 'naip_m': r2(nm), 'island_nodes': size[c_]})
        if nm > 0.05:
            stat['naip_legs'] += 1; stat['naip_m'] += nm
    links = make_links()
    # renumber nodes deterministically (by x, z) and drop unused
    used = sorted({n for l in links for n in l[:2]}, key=lambda i: (round(nodes.xy[i][0], 2), round(nodes.xy[i][1], 2)))
    newi = {o: k for k, o in enumerate(used)}
    adj = defaultdict(set); wset = defaultdict(set); adj_g = defaultdict(set)    # adj_g: without air links
    for a_, b_, wi, pts, rwy in links:
        adj[newi[a_]].add(newi[b_]); adj[newi[b_]].add(newi[a_]); wset[newi[a_]].add(wi); wset[newi[b_]].add(wi)
        if wi != W_CONN['air']:
            adj_g[newi[a_]].add(newi[b_]); adj_g[newi[b_]].add(newi[a_])
    nodes_out = []
    for k, o in enumerate(used):
        m = nodes.meta[o]; x, z = nodes.xy[o]
        kind = m.get('kind')
        if kind is None:
            kind = 'spot' if m.get('spot') else ('end' if len(adj[k]) == 1 else 'junction')
        rec = {'id': f'n{k}', 'x': r2(x), 'z': r2(z), 'kind': kind, 'ways': sorted(wset[k]), 'deg': len(adj[k])}
        for f in ('hold', 'runway', 'end', 'thr', 'spot', 'helipad', 'hangar', 'side', 'crossing'):
            if m.get(f) is not None:
                rec[f] = m[f]
        if kind in ('runway', 'runway_edge'):
            R = next(R for R in rw if R['id'] == m['runway'])
            rec['along_m'] = r2(lines[R['way']][2].project(Point(x, z)))
            rec['along_from'] = R['ends'][0]
        nodes_out.append(rec)
    # link polylines end exactly on their nodes (cut points merged within MERGE_M keep the first cut's position)
    links = [(a_, b_, wi, [nodes.xy[a_]] + list(pts[1:-1]) + [nodes.xy[b_]], rwy) for a_, b_, wi, pts, rwy in links]
    links_out = [dict({'a': newi[a_], 'b': newi[b_], 'way': wi, 'len': r2(poly_len(pts)), 'pts': [[r2(p[0]), r2(p[1])] for p in pts],
                       'runway': rwy}, **({'air': True} if wi == W_CONN['air'] else {})) for a_, b_, wi, pts, rwy in links]
    links_out.sort(key=lambda l: (l['way'], l['a'], l['b'], l['len']))
    for s in spots_out + heli_out:
        for f in ('node', 'attach'):
            if s.get(f) is not None:
                s[f] = newi[s[f]]
    for h in holds_out:
        h['node'] = newi[h['node']]
    for hg in hang_out:
        for sd in hg['access']:
            for f in ('node', 'attach'):
                if sd.get(f) is not None:
                    sd[f] = newi[sd[f]]
    runways_out = []
    for k, R in enumerate(rw):
        ns = sorted({(r2(lines[R['way']][2].project(Point(*nodes.xy[n]))), newi[n]) for _, n in rw_nodes[k] if n in newi})
        runways_out.append({'id': R['id'], 'ends': R['ends'], 'way': R['way'], 'len_m': r2(R['L']),
                            'nodes': [{'node': n, 'along_m': s} for s, n in ns]})
    # edges (sfo3d TaxiNet segment soup), chopped to <= EDGE_MAX_M
    edges = []
    for l in links_out:
        if l.get('air'):
            continue                      # not pavement: TaxiNet matching / paved test must not use it
        for p, q in zip(l['pts'], l['pts'][1:]):
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if d < 0.05:
                continue
            n = max(1, int(math.ceil(d / EDGE_MAX_M)))
            for i in range(n):
                u0, u1 = i / n, (i + 1) / n
                edges.append([r2(p[0] + (q[0] - p[0]) * u0), r2(p[1] + (q[1] - p[1]) * u0),
                              r2(p[0] + (q[0] - p[0]) * u1), r2(p[1] + (q[1] - p[1]) * u1), l['way']])
    # checks: components, reachability from both runways
    N = len(nodes_out); comp = [-1] * N; nc = 0; sizes = []
    for s0 in range(N):
        if comp[s0] >= 0:
            continue
        q = deque([s0]); comp[s0] = nc; sz = 0
        while q:
            u = q.popleft(); sz += 1
            for v in adj[u]:
                if comp[v] < 0:
                    comp[v] = nc; q.append(v)
        sizes.append(sz); nc += 1
    def reach(rid, A_):
        seen = set(); q = deque(n['node'] for R in runways_out if R['id'] == rid for n in R['nodes'])
        seen.update(q)
        while q:
            u = q.popleft()
            for v in A_[u]:
                if v not in seen:
                    seen.add(v); q.append(v)
        return seen
    reach_g = {R['id']: reach(R['id'], adj_g) for R in runways_out}      # fixed-wing: pavement only
    reach_a = {R['id']: reach(R['id'], adj) for R in runways_out}        # helicopters: air links too
    def unreachable(recs, heli):
        out = []
        for s_ in recs:
            rr = reach_a if heli(s_) else reach_g
            if s_['node'] is None or any(s_['node'] not in rr[r] for r in rr):
                out.append(s_['id'])
        return sorted(out)
    unreach = unreachable(spots_out, lambda s_: s_['kind'] == 'helipad')
    heli_unreach = unreachable(heli_out, lambda s_: True)
    hold_unreach = sorted({h['id'] for h in holds_out if any(h['node'] not in reach_g[r] for r in reach_g)})
    hang_unreach = sorted({hg['id'] for hg in hang_out if not any(sd['node'] is not None and all(sd['node'] in reach_g[r] for r in reach_g)
                                                                  for sd in hg['access'])})
    # sanity: no taxi link may pass through a building / hangar footprint, no connector either
    thru = []
    for l in links_out:
        if l.get('air'):
            continue
        g = LineString(l['pts']) if len(l['pts']) >= 2 else None
        if g is not None and g.length > 0 and OB.intersects(g) and g.intersection(OB).length > 0.5:
            thru.append({'way': ways[l['way']]['id'], 'kind': ways[l['way']]['kind'], 'inside_m': r2(g.intersection(OB).length),
                         'at': [r2(g.interpolate(0.5, normalized=True).x), r2(g.interpolate(0.5, normalized=True).y)]})
    cl = sorted(conn_lens)
    checks = {
        'components': nc, 'largest_nodes': max(sizes) if sizes else 0, 'component_sizes': sorted(sizes, reverse=True)[:8],
        'unreachable_spots': unreach, 'unreachable_helipads': heli_unreach, 'holds_unattached': holds_unatt,
        'holds_unreachable': hold_unreach,
        'spots_connected': sum(1 for s in spots_out if s['node'] is not None), 'spots_total': len(spots_out),
        'spot_connector_m': {'p50': r2(cl[len(cl) // 2]) if cl else None, 'p90': r2(cl[int(0.9 * (len(cl) - 1))]) if cl else None,
                             'max': r2(cl[-1]) if cl else None},
        'helipads_connected': sum(1 for s in heli_out if s['node'] is not None), 'helipads_total': len(heli_out),
        'hangar_sides_connected': sum(1 for h in hang_out for s in h['access'] if s['node'] is not None),
        'hangar_sides_total': sum(len(h['access']) for h in hang_out),
        'junction_vertices_shared_open': len(shared), 'junction_vertices_shared_all_ways': shared_all,
        'junction_note': 'vertices shared (0.01 m) by >= 2 open taxi ways / by >= 2 ways of any status; the Phase 1 '
                         'report counts 167 junction vertices = 166 shared + 1 shallow fork (204801549 on E: a vertex of '
                         'both ways, so it is in the shared count here)',
        'crossings_noded': n_cross, 'gaps_joined': n_gap,
        'dead_ends': sum(1 for n in nodes_out if n['kind'] == 'end'),
        'links': len(links_out), 'edges': len(edges), 'nodes': N,
        'length_m': {k: r2(sum(l['len'] for l in links_out if ways[l['way']]['kind'] == k)) for k in ('taxiway', 'taxilane', 'runway', 'connector')},
        'links_on_runway': sum(1 for l in links_out if l['runway'] and ways[l['way']]['kind'] != 'runway'),
        'hangars_without_access': hang_unreach,
        'connector_modes': {k: stat[k] for k in ('straight', 'dogleg', 'air')},
        'connector_legs_on_naip_grey': stat['naip_legs'], 'connector_m_on_naip_grey': r2(stat['naip_m']),
        'connectors_naip_long': stat['naip_long'],
        'islands_joined': islands_joined,
        'spots_inside_footprint': sorted(s_['id'] for s_ in spots_out if s_.get('inside')),
        'spots_air_only': sorted(s_['id'] for s_ in spots_out if s_.get('mode') == 'air'),
        'links_through_buildings': thru,
        'taxi_links_crossing_fences': sorted({ways[l['way']]['id'] for l in links_out if len(l['pts']) >= 2 and
                                              PFENCE.intersects(LineString(l['pts']))}),
        'landside': {'osm': land_ids, 'apron_or_taxi_area_inside_car_parks_m2': r2(park_overlap),
                     'rule': 'pavement for connectors = OSM aprons, taxi lines (width / 2 + 0.5 m) and helipads minus '
                             'car parks; NAIP 2024 grey only inside the aerodrome boundary and outside car parks; no '
                             'connector crosses a fence'},
        'wingspan_limited_ways': sorted({(w['ref'] or w['id'], w['max_span_m']) for w in ways if w.get('max_span_m')}),
    }
    G = {'v': 'hwd-taxigraph/1', 'frame': F.FRAME_ID, 'made_by': 'tools/live/build_taxigraph.py',
         'source': f'data/hwd_airport.json sha256 {sha}',
         'inputs': {'airport': f'data/hwd_airport.json sha256 {sha}', 'osm_landside': f'{os.path.relpath(OSM_EXTRACT, ROOT)} sha256 {osm_sha}',
                    'naip': f'refs/cache/naip/naip_2024_hwd_rgb.jpg sha256 {naip_sha} (pavement grey test)'}, 'licence': 'ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)',
         'attribution': ATTRIBUTION, 'halfWidth': HALF_WIDTH,
         'halfWidth_basis': 'half of 35 ft (10.67 m), AC 150/5300-13B Chg 1 Table 4-2 TDG 2A/2B [inf]',
         'ways': ways, 'edges': edges, 'nodes': nodes_out, 'links': links_out, 'holds': holds_out, 'spots': spots_out,
         'helipads': heli_out, 'hangars': hang_out, 'runways': runways_out,
         'aprons': [[[r2(p[0]), r2(p[1])] for p in x['ring']] for x in sorted(A['aprons'], key=lambda x: x['id'])],
         'apron_ids': [x['id'] for x in sorted(A['aprons'], key=lambda x: x['id'])],
         'leadins': [],
         'closed': [{'id': w['id'], 'ref': w.get('ref'), 'pts': [[r2(p[0]), r2(p[1])] for p in w['pts']], 'status': w['status']} for w in CLOSED],
         'rules': {'GAP_M': GAP_M, 'TOUCH_M': TOUCH_M, 'MERGE_M': MERGE_M, 'CLEAR_M': CLEAR_M, 'MAX_CONN_M': MAX_CONN_M,
                   'MAX_HANGAR_M': MAX_HANGAR_M, 'HOLD_SNAP_M': HOLD_SNAP_M, 'EDGE_MAX_M': EDGE_MAX_M, 'PAV_TOL_M': PAV_TOL_M,
                   'NAIP_DISC_M': NAIP_DISC_M, 'SAT_MAX': SAT_MAX, 'EG_MAX': EG_MAX, 'DOGLEG_R': list(DOGLEG_R),
                   'ISLAND_M': ISLAND_M, 'MAX_AIR_M': MAX_AIR_M, 'NAIP_MAX_M': NAIP_MAX_M, 'SQUARE_ASPECT': SQUARE_ASPECT,
                   'NONGREY_RUN_M': NONGREY_RUN_M},
         'checks': checks}
    txt = json.dumps(G, separators=(',', ':'), sort_keys=False, ensure_ascii=False)
    with open(OUT_JSON, 'w') as f:
        f.write(txt + '\n')
    head = ('// generated by tools/live/build_taxigraph.py from data/hwd_airport.json (sha256 %s). Do not edit.\n'
            '// Data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright), and contains information\n'
            '// from ADSB.lol (https://adsb.lol) made available under the ODbL 1.0; runways from FAA NASR, pavement test on USDA NAIP\n'
            '// 2024 imagery (both public domain).\n'
            '// This derived database is licensed under the ODbL 1.0 as well.\n') % sha
    with open(OUT_JS, 'w') as f:
        f.write(head + 'export const TAXIGRAPH = ' + txt + ';\n')
    print(f'{OUT_JSON}: {len(ways)} ways, {N} nodes, {len(links_out)} links, {len(edges)} edges, {len(holds_out)} holds, '
          f'{os.path.getsize(OUT_JSON) / 1e3:.0f} kB')
    print(json.dumps(checks, indent=None))
    if a.plot or a.crop:
        crops = {}
        for c in a.crop:
            nm, xyz = c.split(':'); cx, cz, hw = (float(v) for v in xyz.split(','))
            crops[nm] = (cx, cz, hw)
        plot(G, A, crops, overview=a.plot, show_pav=a.show_pavement)


def plot(G, A, crops=None, overview=True, show_pav=False):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    gj = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.json')))
    e0, n1, g = gj['origin_E'], gj['origin_N'], gj['pixel_size_m']
    def w2px(x, z):
        la, lo = F.world_to_ll(x, z); E, N = F.ll_to_utm10(la, lo)
        return (E - e0) / g - 0.5, (n1 - N) / g - 0.5
    # affine fit world -> px over the field (residual reported)
    xs = np.linspace(-1200, 1200, 7); zs = np.linspace(-1000, 1000, 7)
    W = np.array([(x, z) for x in xs for z in zs]); Pp = np.array([w2px(x, z) for x, z in W])
    M = np.c_[W, np.ones(len(W))]; coef, *_ = np.linalg.lstsq(M, Pp, rcond=None)
    res = np.abs(M @ coef - Pp).max()
    T = lambda pts: np.asarray(pts, float) @ coef[:2] + coef[2]
    im = Image.open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.jpg')).convert('RGB')
    allp = np.array([[n['x'], n['z']] for n in G['nodes']])
    def draw(fn, x0, z0, x1, z1, scale, title, lw=1.0, labels=False):
        c = T([[x0, z0], [x1, z1], [x0, z1], [x1, z0]]); c0, r0 = c.min(0); c1, r1 = c.max(0)
        c0, r0, c1, r1 = int(c0), int(r0), int(c1) + 1, int(r1) + 1
        crop = np.asarray(im.crop((c0, r0, c1, r1))).astype(float) / 255.0
        crop = 0.35 + 0.65 * crop * 0.85
        h, w = crop.shape[:2]
        fig = plt.figure(figsize=(w * scale / 100, h * scale / 100 + 0.9), dpi=100)
        ax = fig.add_axes([0, 0.9 / (h * scale / 100 + 0.9), 1, (h * scale / 100) / (h * scale / 100 + 0.9)])
        ax.imshow(crop, extent=(c0, c1, r1, r0), interpolation='lanczos' if scale > 1 else 'antialiased')
        def L(pts, **kw):
            p = T(pts); ax.plot(p[:, 0], p[:, 1], **kw)
        if show_pav:
            from matplotlib.patches import Polygon as MPoly
            for g in getattr(PAVEMENT, 'geoms', [PAVEMENT]):
                ax.add_patch(MPoly(T(list(g.exterior.coords)), closed=True, fc='#00ff66', ec='#00aa44', alpha=0.18, lw=0.5, zorder=1))
        for o in A['buildings'] + A['hangars']:
            if len(o.get('ring') or []) >= 3:
                L(list(o['ring']) + [o['ring'][0]], color='#ffffff', lw=0.5 * lw, alpha=0.8, zorder=2)
        for cw in G['closed']:
            L(cw['pts'], color='#8a8a8a', lw=lw, ls=(0, (3, 2)), zorder=2)
        colours = {'taxiway': '#ffd21f', 'taxilane': '#3fd0ff', 'runway': '#ffffff', 'connector': '#ff4fd8'}
        for l in G['links']:
            k = G['ways'][l['way']]['kind']
            col = '#ff8a00' if (l['runway'] and k != 'runway') else colours[k]
            ls = (0, (4, 2)) if G['ways'][l['way']].get('max_span_m') else '-'
            if l.get('air'):
                col, ls = '#c58cff', (0, (2, 2))
            L(l['pts'], color=col, lw=lw * (1.6 if k == 'runway' else 1.0), ls=ls, zorder=3, solid_capstyle='round')
        kinds = defaultdict(list)
        for n in G['nodes']:
            kinds[n['kind']].append((n['x'], n['z']))
        sty = {'junction': dict(s=6 * lw, c='#ffffff', marker='o', lw=0), 'end': dict(s=10 * lw, c='#ff2020', marker='s', lw=0),
               'runway': dict(s=18 * lw, c='#ffffff', marker='D', edgecolors='k', linewidths=0.4),
               'runway_edge': dict(s=10 * lw, c='#ff8a00', marker='|', lw=1.2),
               'hold': dict(s=40 * lw, c='#ff2020', marker='_', lw=2.2), 'spot': dict(s=10 * lw, c='#38ff5a', marker='o', lw=0),
               'helipad': dict(s=30 * lw, c='#c58cff', marker='H', lw=0), 'hangar': dict(s=10 * lw, c='#ff4fd8', marker='^', lw=0)}
        for k, pts in kinds.items():
            p = T(pts); ax.scatter(p[:, 0], p[:, 1], zorder=5, **sty.get(k, dict(s=6, c='w')))
        bad = set(G['checks']['unreachable_spots'])
        for s in G['spots']:
            if s['id'] in bad or s['node'] is None:
                p = T([[s['x'], s['z']]]); ax.scatter(p[:, 0], p[:, 1], s=60 * lw, marker='x', c='#ff0000', lw=2, zorder=6)
        if labels:
            for hd in G['holds']:
                p = T([[hd['x'], hd['z']]])[0]; ax.text(p[0] + 4, p[1] - 4, hd['runway'], color='#ffb0b0', fontsize=6, zorder=7)
        ax.set_xlim(c0, c1); ax.set_ylim(r1, r0); ax.axis('off')
        C = G['checks']
        fig.text(0.01, 0.55 * 0.9 / (h * scale / 100 + 0.9), (
            f'{title} - HWD taxi graph (tools/live/build_taxigraph.py) over USDA NAIP 2024 (public domain), UTM-north up. '
            f'{C["nodes"]} nodes, {C["links"]} links, {C["components"]} component(s); spots connected {C["spots_connected"]}/{C["spots_total"]}, '
            f'unreachable {len(C["unreachable_spots"])}; holds {len(G["holds"])}.\n'
            'yellow taxiway, cyan taxilane, white runway (NASR centreline), orange = taxi link inside a runway outline, magenta connector, purple dashed = helicopter air link, '
            'dashed = wingspan limit (A1 100 ft, Z1 94 ft), grey dashed = closed; red bar hold, green dot spot, purple H helipad, '
            'white diamond runway node, red square dead end, red x unreachable.  Data (c) OpenStreetMap contributors (ODbL), ADSB.lol (ODbL), FAA NASR.'),
            fontsize=7 if scale <= 1 else 8, va='center', wrap=True)
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        fig.savefig(fn, dpi=100); plt.close(fig)
        print('plot', fn, f'(affine residual {res:.3f} px)')
    out = os.path.join(ROOT, 'out', 'phase2')
    x0, z0 = allp.min(0) - 60; x1, z1 = allp.max(0) + 60
    views = {}
    if overview:
        draw(os.path.join(out, 'taxigraph.png'), x0, z0, x1, z1, 0.62, 'Whole field', lw=0.9, labels=True)
        views = {'west': (-300, -420, 230), 'east': (330, -40, 230), 'centre': (20, -300, 200), 'south': (300, 230, 200)}
    views.update(crops or {})
    for name, (cx, cz, hw) in views.items():
        draw(os.path.join(out, f'taxigraph_{name}.png'), cx - hw, cz - hw * 0.75, cx + hw, cz + hw * 0.75, 1.6, name.title(),
             lw=1.6, labels=True)


if __name__ == '__main__':
    main()
