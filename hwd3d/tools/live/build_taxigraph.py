#!/usr/bin/env python3
"""HWD taxi graph for the live traffic engine -> data/hwd_taxigraph.json + data/hwd_taxigraph.js (TAXIGRAPH).

Replaces sfo3d/tools/live/build_taxigraph.py @ a967f9b (which read SFO's OSM extract into a segment soup). Kept: the
sfo3d-compatible `edges` segment soup ([x0, z0, x1, z1, wayIndex], read by js/live/traffic.js TaxiNet for its grid,
nearest-line matching and `paved` test), `ways[].kind` ('runway' marks runway segments), `halfWidth`, `aprons`; runway
centrelines from the FAA NASR ends, not OSM. New (format 'hwd-taxigraph/1', contract docs/phase2_fork_map.md 2.3): a
node/link graph for routing (dead reckoning across the recorder's 46-s holes must follow pavement, never cut across
grass or buildings), hold-short nodes, runway entry nodes, connectors from every parking spot / helipad / hangar side to
the network, wingspan limits, closed pavement and connectivity checks.

Input: data/hwd_airport.json ONLY (Phase 1, frozen; deterministic): taxiways + taxilanes (OSM, snapped to NAIP paint in
Phase 1, junctions as shared vertices), runways (NASR ends, widths, outlines), holds, parking, helipads, hangars,
buildings, aprons. Same input -> byte-identical output.

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
  spots     each parking spot (177), helipad (9) and hangar long side (34 hangars) is joined to the network by a
            straight 'connector' link to a point of an open taxi line: the nearest candidate (per way: the closest
            point and points 5-40 m either side of it) whose segment lies on pavement (aprons, taxi lines within their
            half width + 0.5 m, helipads; at most 0.5 m off it) and keeps >= CLEAR_M (1.0 m) from every building and
            hangar footprint (the first 1.5 m from a hangar side excepted), and does not enter a runway outline [inf].
            None found within MAX_CONN_M (150 m; hangars 60 m) -> node null + why_none.
  halfWidth 5.33 m: half of the 35-ft AC default width above [inf, AC 150/5300-13B Table 4-2] (TaxiNet.paved).
Licence: the output is a Derivative Database of data/hwd_airport.json, itself ODbL 1.0 (OpenStreetMap contributors;
adsb.lol for the ADS-B-observed parking spots).

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

SRC = os.path.join(ROOT, 'data', 'hwd_airport.json')
OUT_JSON = os.path.join(ROOT, 'data', 'hwd_taxigraph.json')
OUT_JS = os.path.join(ROOT, 'data', 'hwd_taxigraph.js')
GAP_M = 3.0          # dead end this close to another way: joined [inf]
TOUCH_M = 1.5        # taxi-line end this close to a runway centreline: joined to it [inf]
MERGE_M = 0.05       # cut points closer than this are one node
CLEAR_M = 1.0        # connector clearance from building / hangar footprints [inf]
MAX_CONN_M = 150.0   # longest spot / helipad connector [inf]
MAX_HANGAR_M = 60.0  # longest hangar-side connector [inf]
HOLD_SNAP_M = 15.0
EDGE_MAX_M = 50.0    # `edges` segments are chopped to <= 50 m (TaxiNet grid cells are 40 m)
HALF_WIDTH = round(10.67 / 2, 2)
ATTRIBUTION = ['© OpenStreetMap contributors (ODbL 1.0) - https://www.openstreetmap.org/copyright',
               'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL 1.0 '
               '(parking spots observed from ADS-B stays)',
               'Runways: FAA NASR (public domain)']


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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--plot', action='store_true'); a = ap.parse_args()
    raw = open(SRC, 'rb').read(); sha = hashlib.sha256(raw).hexdigest(); A = json.loads(raw)
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
                   ('hangar', 'hangar long side (2 m out) to the nearest clear paved point of the network')):
        W_CONN[k] = len(ways)
        ways.append({'id': 'conn:' + k, 'ref': None, 'kind': 'connector', 'width_m': None, 'width_src': 'inf',
                     'max_span_m': None, 'restriction': None, 'src': 'inf', 'rule': why})

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
    pav = unary_union([Polygon(x['ring']) for x in A['aprons']] + taxi_buf + [Polygon(x['ring']).buffer(0.5) for x in A['helipads']])
    PAV = prep(pav)
    obst = [(o['id'], Polygon(o['ring'])) for o in A['buildings'] + A['hangars'] if len(o.get('ring') or []) >= 3]
    OB = unary_union([g for _, g in obst]); POB = prep(OB)
    rects = unary_union([R['rect'] for R in rw]); PR = prep(rects)

    def connector(x, z, maxd, own=None):
        """-> (way index, s, (px, pz), length, clearance) or (None, reason)."""
        p = Point(x, z); cands = []
        for wi in range(n_taxi):
            L = lines[wi][2]; d0 = L.distance(p)
            if d0 > maxd:
                continue
            s0 = L.project(p)
            for ds in (0, -5, 5, -10, 10, -20, 20, -40, 40):
                s = min(max(s0 + ds, 0.0), L.length); q = L.interpolate(s)
                cands.append((p.distance(q), wi, s, (q.x, q.y)))
        if not cands:
            return None, f'no open taxi line within {maxd:.0f} m'
        cands.sort(key=lambda c: (round(c[0], 3), c[1], c[2])); why = {}
        ob = OB if own is None else unary_union([g for i, g in obst if i != own])
        for d, wi, s, q in cands:
            if d > maxd:
                break
            if d < 0.05:
                return (wi, s, q, d, None), None
            seg = LineString([(x, z), q])
            off = seg.difference(pav).length
            if off > 0.5:
                why.setdefault('off pavement', 0); why['off pavement'] += 1; continue
            if PR.intersects(seg) and not PR.contains(Point(x, z)):
                why.setdefault('enters a runway', 0); why['enters a runway'] += 1; continue
            clr = seg.distance(ob)
            if own is not None:
                own_g = dict(obst)[own]
                tail = LineString([seg.interpolate(min(1.5, d * 0.5)), q]) if d > 1.5 else None
                c2 = tail.distance(own_g) if tail is not None else 99.0
                clr = min(clr, c2)
            if clr < CLEAR_M:
                why.setdefault('building clearance', 0); why['building clearance'] += 1; continue
            return (wi, s, q, d, clr), None
        return None, 'no clear paved straight line within %.0f m (%s)' % (maxd, ', '.join(f'{k}: {v}' for k, v in sorted(why.items())) or 'none tried')

    spots_out, conn_lens = [], []
    for sp in sorted(A['parking'], key=lambda s: s['id']):
        x, z = sp['x'], sp['z']
        res, why = connector(x, z, MAX_CONN_M)
        rec = {'id': sp['id'], 'kind': sp['kind'], 'src': sp['src'], 'x': r2(x), 'z': r2(z), 'node': None, 'attach': None,
               'len': None, 'pts': None}
        if res is None:
            rec['why_none'] = why
        else:
            wi, s, q, d, clr = res
            nt = cut(wi, s)
            if d < MERGE_M:
                ns = nt; nodes.meta[ns].setdefault('spot', sp['id'])
            else:
                ns = nodes.get(x, z, kind='spot', spot=sp['id'])
                extra_links.append((ns, nt, W_CONN['spot'], [(x, z), q], None))
            rec.update(node=ns, attach=nt, len=r2(d), pts=[[r2(x), r2(z)], [r2(q[0]), r2(q[1])]],
                       clear_m=r2(clr) if clr is not None else None, way=wi)
            conn_lens.append(d)
        spots_out.append(rec)
    heli_out = []
    for hp in sorted(A['helipads'], key=lambda h: h['id']):
        res, why = connector(hp['x'], hp['z'], MAX_CONN_M)
        rec = {'id': hp['id'], 'x': r2(hp['x']), 'z': r2(hp['z']), 'node': None, 'attach': None, 'len': None}
        if res is None:
            rec['why_none'] = why
        else:
            wi, s, q, d, clr = res; nt = cut(wi, s)
            nh = nodes.get(hp['x'], hp['z'], kind='helipad', helipad=hp['id'])
            if nh != nt:
                extra_links.append((nh, nt, W_CONN['helipad'], [(hp['x'], hp['z']), q], None))
            rec.update(node=nh, attach=nt, len=r2(d), pts=[[r2(hp['x']), r2(hp['z'])], [r2(q[0]), r2(q[1])]], way=wi)
        heli_out.append(rec)
    hang_out = []
    for hg in sorted(A['hangars'], key=lambda h: h['id']):
        poly = Polygon(hg['ring']); mrr = poly.minimum_rotated_rectangle; c = list(mrr.exterior.coords)[:4]
        sides = sorted(((math.hypot(c[(i + 1) % 4][0] - c[i][0], c[(i + 1) % 4][1] - c[i][1]), i) for i in range(4)), reverse=True)[:2]
        cx, cz = poly.centroid.x, poly.centroid.y; acc = []
        for _, i in sorted(sides, key=lambda t: t[1]):
            a_, b_ = c[i], c[(i + 1) % 4]; mx, mz = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
            nx, nz = mx - cx, mz - cz; nl = math.hypot(nx, nz) or 1.0; nx, nz = nx / nl, nz / nl
            px, pz = mx + 2.0 * nx, mz + 2.0 * nz
            res, why = connector(px, pz, MAX_HANGAR_M, own=hg['id'])
            side = {'side': compass(nx, nz), 'x': r2(px), 'z': r2(pz), 'node': None, 'attach': None}
            if res is None:
                side['why_none'] = why
            else:
                wi, s, q, d, clr = res; nt = cut(wi, s)
                nh = nodes.get(px, pz, kind='hangar', hangar=hg['id'], side=side['side'])
                if nh != nt:
                    extra_links.append((nh, nt, W_CONN['hangar'], [(px, pz), q], None))
                side.update(node=nh, attach=nt, len=r2(d), way=wi)
            acc.append(side)
        hang_out.append({'id': hg['id'], 'name': hg.get('name'), 'kind': hg.get('kind'), 'src': 'inf', 'access': acc,
                         'rule': 'door side not known (Phase 1: doors not visible on NAIP); both long sides of the '
                                 'minimum rectangle, 2 m out, joined like spots (max %.0f m)' % MAX_HANGAR_M})

    # links along ways
    links = []
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
            links.append((n0, n1, wi, pts, runway))
    links += extra_links
    # dedupe identical links
    seen, L2 = set(), []
    for l in links:
        k = (min(l[0], l[1]), max(l[0], l[1]), l[2], round(poly_len(l[3]), 2))
        if k in seen:
            continue
        seen.add(k); L2.append(l)
    links = L2
    # renumber nodes deterministically (by x, z) and drop unused
    used = sorted({n for l in links for n in l[:2]}, key=lambda i: (round(nodes.xy[i][0], 2), round(nodes.xy[i][1], 2)))
    newi = {o: k for k, o in enumerate(used)}
    adj = defaultdict(set); wset = defaultdict(set)
    for a_, b_, wi, pts, rwy in links:
        adj[newi[a_]].add(newi[b_]); adj[newi[b_]].add(newi[a_]); wset[newi[a_]].add(wi); wset[newi[b_]].add(wi)
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
    links_out = [{'a': newi[a_], 'b': newi[b_], 'way': wi, 'len': r2(poly_len(pts)), 'pts': [[r2(p[0]), r2(p[1])] for p in pts],
                  'runway': rwy} for a_, b_, wi, pts, rwy in links]
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
    def reach(rid):
        seen = set(); q = deque(n['node'] for R in runways_out if R['id'] == rid for n in R['nodes'])
        seen.update(q)
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); q.append(v)
        return seen
    reach_rw = {R['id']: reach(R['id']) for R in runways_out}
    unreach = sorted({s['id'] for s in spots_out if s['node'] is None or any(s['node'] not in reach_rw[r] for r in reach_rw)})
    heli_unreach = sorted({s['id'] for s in heli_out if s['node'] is None or any(s['node'] not in reach_rw[r] for r in reach_rw)})
    hold_unreach = sorted({h['id'] for h in holds_out if any(h['node'] not in reach_rw[r] for r in reach_rw)})
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
    }
    G = {'v': 'hwd-taxigraph/1', 'frame': F.FRAME_ID, 'made_by': 'tools/live/build_taxigraph.py',
         'source': f'data/hwd_airport.json sha256 {sha}', 'licence': 'ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)',
         'attribution': ATTRIBUTION, 'halfWidth': HALF_WIDTH,
         'halfWidth_basis': 'half of 35 ft (10.67 m), AC 150/5300-13B Chg 1 Table 4-2 TDG 2A/2B [inf]',
         'ways': ways, 'edges': edges, 'nodes': nodes_out, 'links': links_out, 'holds': holds_out, 'spots': spots_out,
         'helipads': heli_out, 'hangars': hang_out, 'runways': runways_out,
         'aprons': [[[r2(p[0]), r2(p[1])] for p in x['ring']] for x in sorted(A['aprons'], key=lambda x: x['id'])],
         'apron_ids': [x['id'] for x in sorted(A['aprons'], key=lambda x: x['id'])],
         'leadins': [],
         'closed': [{'id': w['id'], 'ref': w.get('ref'), 'pts': [[r2(p[0]), r2(p[1])] for p in w['pts']], 'status': w['status']} for w in CLOSED],
         'rules': {'GAP_M': GAP_M, 'TOUCH_M': TOUCH_M, 'MERGE_M': MERGE_M, 'CLEAR_M': CLEAR_M, 'MAX_CONN_M': MAX_CONN_M,
                   'MAX_HANGAR_M': MAX_HANGAR_M, 'HOLD_SNAP_M': HOLD_SNAP_M, 'EDGE_MAX_M': EDGE_MAX_M},
         'checks': checks}
    txt = json.dumps(G, separators=(',', ':'), sort_keys=False, ensure_ascii=False)
    with open(OUT_JSON, 'w') as f:
        f.write(txt + '\n')
    head = ('// generated by tools/live/build_taxigraph.py from data/hwd_airport.json (sha256 %s). Do not edit.\n'
            '// Data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright), and contains information\n'
            '// from ADSB.lol (https://adsb.lol) made available under the ODbL 1.0; runways from FAA NASR (public domain).\n'
            '// This derived database is licensed under the ODbL 1.0 as well.\n') % sha
    with open(OUT_JS, 'w') as f:
        f.write(head + 'export const TAXIGRAPH = ' + txt + ';\n')
    print(f'{OUT_JSON}: {len(ways)} ways, {N} nodes, {len(links_out)} links, {len(edges)} edges, {len(holds_out)} holds, '
          f'{os.path.getsize(OUT_JSON) / 1e3:.0f} kB')
    print(json.dumps(checks, indent=None))
    if a.plot:
        plot(G, A)


def plot(G, A):
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
        for cw in G['closed']:
            L(cw['pts'], color='#8a8a8a', lw=lw, ls=(0, (3, 2)), zorder=2)
        colours = {'taxiway': '#ffd21f', 'taxilane': '#3fd0ff', 'runway': '#ffffff', 'connector': '#ff4fd8'}
        for l in G['links']:
            k = G['ways'][l['way']]['kind']
            col = '#ff8a00' if (l['runway'] and k != 'runway') else colours[k]
            ls = (0, (4, 2)) if G['ways'][l['way']].get('max_span_m') else '-'
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
            for h in G['holds']:
                p = T([[h['x'], h['z']]])[0]; ax.text(p[0] + 4, p[1] - 4, h['runway'], color='#ffb0b0', fontsize=6, zorder=7)
        ax.set_xlim(c0, c1); ax.set_ylim(r1, r0); ax.axis('off')
        C = G['checks']
        fig.text(0.01, 0.55 * 0.9 / (h * scale / 100 + 0.9), (
            f'{title} - HWD taxi graph (tools/live/build_taxigraph.py) over USDA NAIP 2024 (public domain), UTM-north up. '
            f'{C["nodes"]} nodes, {C["links"]} links, {C["components"]} component(s); spots connected {C["spots_connected"]}/{C["spots_total"]}, '
            f'unreachable {len(C["unreachable_spots"])}; holds {len(G["holds"])}.\n'
            'yellow taxiway, cyan taxilane, white runway (NASR centreline), orange = taxi link inside a runway outline, magenta connector, '
            'dashed = wingspan limit (A1 100 ft, Z1 94 ft), grey dashed = closed; red bar hold, green dot spot, purple H helipad, '
            'white diamond runway node, red square dead end, red x unreachable.  Data (c) OpenStreetMap contributors (ODbL), ADSB.lol (ODbL), FAA NASR.'),
            fontsize=7 if scale <= 1 else 8, va='center', wrap=True)
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        fig.savefig(fn, dpi=100); plt.close(fig)
        print('plot', fn, f'(affine residual {res:.3f} px)')
    out = os.path.join(ROOT, 'out', 'phase2')
    x0, z0 = allp.min(0) - 60; x1, z1 = allp.max(0) + 60
    draw(os.path.join(out, 'taxigraph.png'), x0, z0, x1, z1, 0.62, 'Whole field', lw=0.9, labels=True)
    for name, (cx, cz, hw) in {'west': (-300, -420, 230), 'east': (330, -40, 230), 'centre': (20, -300, 200),
                               'south': (300, 230, 200)}.items():
        draw(os.path.join(out, f'taxigraph_{name}.png'), cx - hw, cz - hw * 0.75, cx + hw, cz + hw * 0.75, 1.6, name.title(),
             lw=1.6, labels=True)


if __name__ == '__main__':
    main()
