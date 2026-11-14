"""Taxi graph for SHA Live 3D -> sha3d/data/sha_taxigraph.json and sha_taxigraph.js (window.SHA_TAXIGRAPH). Task A2.

    python3 -I sha3d/tools/airport/build_taxigraph.py [SHA3D_DIR]

Format: sfo3d data/sfo_taxigraph.js (tools/live/build_taxigraph.py) fields kept for the traffic engine (TaxiNet):
  edges [[x0, z0, x1, z1, wayIndex]], ways [{ref, kind, osm}], aprons [[[x, z]..]], leadins [{ref, pts, stop, hdg}],
  halfWidth; plus a routable node / link graph:
  nodes [{id, x, z, kind, ref?, src, evidence}]   kinds: junction, end, stand, hold, rwy, rwy_end, push_end
  links [{id, a, b, kind, ref, len, pts, dir, use, stand?, span_max, src, evidence, ...}]
        kind: taxiway | taxilane | leadin | runway | push ; dir: 'both' | 'ab' (one-way a -> b)
        use: 'all' | 'arrival' | 'departure' | 'runway' | 'stand'
  turns {node: [[link_in, link_out], ...]}: the allowed transitions at every node (turn <= 90 deg, AIP (mirror)
        AD 2.20 2.3.1; one-way and crossing rules applied). A router must be edge-based and use only these.
  runways [{id, ends, connections[], crossing_taxiways_osm}], rules {...} (AIP short facts), checks_at_build.
Routing rules encoded here (QA C1 H2 / M6, lead decisions 2026-11-14):
  * runway links: use 'runway', excluded from normal taxi routing (only an explicit backtrack may use them);
  * rapid exits (acute links off the middle of a runway): one-way runway -> taxiway, use 'arrival', for_landing [end];
  * runway crossings only on the AIP crossing taxiways (H1-H7 for 18R/36L; H1, H4, H7 for 18L/36R);
  * lead-in links of a stand's own lead-in: kind 'leadin', use 'stand', stand = <name>: allowed only as the first or
    last leg of a route of that stand; the other OSM parking_position lines are apron lanes: kind 'taxilane',
    osm_kind 'leadin', src 'inf';
  * push links follow the reversed own lead-in to its first apron lane / junction (data/sha_stands.json push).
Inputs (committed): data/sha_airport.json (A1: taxiways incl. the re-fitted runs, taxilanes, holds, runways, aprons),
refs/cache/osm_pinned/zsss_osm_pinned.geojson (OSM runway ways with their junction nodes, lead-in ways),
data/meas/twy_refit.json (vertex moves, applied to lead-ins that share a moved taxiway vertex), data/sha_stands.json
(stands, push-back). Vertices are joined where they coincide (world coordinates to 0.01 m from the same frame).
"""
import heapq
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
from stand_geom import OsmStands, wxz, hdiff  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402

OUT_JSON = os.path.join(ROOT, 'data/sha_taxigraph.json')
OUT_JS = os.path.join(ROOT, 'data/sha_taxigraph.js')
AIP_TXT = os.path.join(ROOT, 'refs/cache/aip/derived_aip_zsss/ad2_right_column.txt')
R2 = lambda v: round(float(v), 2)  # noqa: E731
HOLD_DIST = 90.0     # m from the runway centreline for inferred runway-holding positions [inf: ICAO Annex 14 Table 3-2,
#                      code 4 precision approach CAT I (from memory); the OSM holds nearest to a runway are at 88.8 m]

AIP_RULES = {
    'arrival_only': dict(refs=['Y1', 'Y2', 'Y3'], text='TWY Y1-Y3 are only used for arrival (AD 2.20 3.1.5).',
                         probe='TWY Y1-Y3 are only used for arrival'),
    'departure_only': dict(refs=['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'L11', 'L12', 'L13', 'L14', 'L15', 'L16', 'L17'],
                           text='TWY M1-M6, L11-L17 are only used for departure; no two aircraft at the same time on any '
                                'of Y1-Y3, M1-M6, L15-L17 (AD 2.20 3.1.5).',
                           probe='M1-M6, L11-L17 are only used for departure'),
    'crossings': dict(text='Use TWY H1-H7 to cross RWY18R/36L; use TWY H1, H4, H7 to cross RWY18L/36R (AD 2.20 2.2.5).',
                      probe='Use TWY H1-H7 to cross RWY18R/36L; use TWY H1, H4, H7 to cross RWY18L/36R'),
    'no_vacate_h345': dict(text='Landing aircraft must not vacate the runway via TWY H3, H4 or H5 (AD 2.20 2.3.2).',
                           probe='vacate RWY via TWY H3, H4 or H5'),
    'no_turn_90': dict(text='Turns of more than 90 deg on a runway or taxiway are forbidden (AD 2.20 2.3.1).',
                       probe='Turn around exceeding 90°on RWY or TWY is'),
    'route_north_south': dict(text='ROUTE-NORTH = TWY BN -> N, ROUTE-SOUTH = TWY BS -> S, one-way, normally for arrivals '
                                   'to the west apron; span < 36 m normal, 36-65 m limited, >= 65 m forbidden; aircraft '
                                   '>= 36 m mainly cross RWY18R (36L) via H2 (H6) (AD 2.20 2.3.3).',
                              probe='ROUTE-NORTH: TWY BN→ TWY N;'),
    'rapid_exit': dict(text='Landing aircraft vacate via the first or second rapid exit within 50 s (AD 2.20 2.1.4.2).',
                       probe='within 50s after touchdown via the first or second rapid'),
    'intersection_departure': dict(text='ATC may clear entry to RWY18R via H2 or RWY36L via H6 for take-off (AD 2.20 2.1.7).',
                                   probe='ATC may instruct aircraft to enter RWY18R via'),
    'no_landing_18R36L_night': dict(text='No landings on RWY18R/36L 1600-2300 UTC except alternates (AD 2.20 2.1.6).',
                                    probe='Aircraft is forbidden to land on RWY18R/36L'),
}


TURN_MAX = 90.0          # deg: AIP (mirror) AD 2.20 2.3.1 "turns of more than 90 deg forbidden"
TURN_TOL = 10.0          # deg: digitising tolerance (OSM junctions have no fillets; a right-angle turn measures 90 +- a
#                          few deg on hand-placed vertices); transitions up to TURN_MAX + TURN_TOL are allowed [inf]
TURN_LOOK = 15.0         # m: link direction at a node = chord to the point this far along the link (digitising noise)
RAPID_END_GUARD = 400.0  # m: acute connections within this distance of a runway end are entries / exits (use 'all')
ENTRY_WIN = 450.0        # m: a take-off may start from a runway node within this distance of its runway end
CROSS = {'18R/36L': {'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7'}, '18L/36R': {'H1', 'H4', 'H7'}}   # AIP (mirror) 2.2.5
NO_VACATE = {'H3', 'H4', 'H5'}                                                                  # AIP (mirror) 2.3.2
INTERSECTION_TO = {'18R': 'H2', '36L': 'H6'}                                                    # AIP (mirror) 2.1.7
AIP_NOTICE = ('AIP China AD 2 ZSSS (CAAC) via an unofficial mirror, EFF 2026-07-08; short cited facts; not covered by '
              'ODbL (the ODbL licence of this file does not apply to this block)')


def key(x, z):
    return (round(x, 2), round(z, 2))


def _dir_at(pts, from_start):
    """unit direction of travel along pts leaving the first point (from_start) or arriving at the last point"""
    P = pts if from_start else pts[::-1]
    acc = 0.0; q = P[-1]
    for a, b in zip(P[:-1], P[1:]):
        d = math.dist(a, b)
        if acc + d >= TURN_LOOK:
            t = (TURN_LOOK - acc) / d; q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])); break
        acc += d
    vx, vz = q[0] - P[0][0], q[1] - P[0][1]
    L = math.hypot(vx, vz) or 1.0
    return (vx / L, vz / L) if from_start else (-vx / L, -vz / L)


def _turn(din, dout):
    c = max(-1.0, min(1.0, din[0] * dout[0] + din[1] * dout[1]))
    return math.degrees(math.acos(c))


def main():
    A = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
    ST = json.load(open(os.path.join(ROOT, 'data/sha_stands.json')))
    O = OsmStands(ROOT)
    aip_txt = open(AIP_TXT, encoding='utf-8').read() if os.path.exists(AIP_TXT) else None
    checks = {}
    # ------------------------------------------------------------------ polylines
    polys = []   # dicts: pts [(x, z)], kind, ref, osm, version, oneway (bool, along pts), status, src, evidence
    for t in A['taxiways'] + A['taxilanes']:
        if not t['pts'] or len(t['pts']) < 2:
            continue
        polys.append(dict(pts=[tuple(p) for p in t['pts']], kind=t['kind'], ref=t.get('ref'),
                          osm=int(t['id'].split('/')[-1]), version=t['evidence']['osm']['version'],
                          oneway=bool(t.get('oneway')), status=t['status'],
                          moved=bool(t.get('vertices_moved'))))
    for f in O.leadin_ways:
        pts = [tuple(R2(v) for v in O.xz(c)) for c in f['geometry']['coordinates']]
        polys.append(dict(pts=pts, kind='leadin', ref=None, osm=f['properties']['@id'], version=f['properties']['@version'],
                          oneway=False, status='open', moved=any(f'{c[0]:.7f},{c[1]:.7f}' in O.moves
                                                                 for c in f['geometry']['coordinates'])))
    rwy_osm = {f['properties']['tags']['ref']: f for f in O.features
               if f['properties']['tags'].get('aeroway') == 'runway' and f['geometry']['type'] == 'LineString'}
    rwy_info = {r['id']: r for r in A['runways']}
    for rid, f in rwy_osm.items():
        pts = [tuple(R2(v) for v in wxz(c)) for c in f['geometry']['coordinates']]
        cl = rwy_info[rid]['centreline']['pts']            # A1 placed ends (north first)
        if math.dist(pts[0], cl[0]) > math.dist(pts[-1], cl[0]):
            pts = pts[::-1]
        pts = [tuple(cl[0])] + pts + [tuple(cl[1])]
        polys.append(dict(pts=pts, kind='runway', ref=rid, osm=f['properties']['@id'], version=f['properties']['@version'],
                          oneway=False, status='open', moved=False))
    # own lead-ins (QA C1 M6): segment sets per stand, in the same world coordinates as the polylines
    own_seg = {}
    for st in O.stands():
        keys, pl = O.own_leadin(st['key'])
        if pl:
            ks = [key(R2(x), R2(z)) for x, z in pl]
            own_seg[st['name']] = {frozenset(p) for p in zip(ks[:-1], ks[1:])}
    # ------------------------------------------------------------------ nodes at junctions / ends
    use = Counter()
    vert_ways = defaultdict(set)
    for wi, p in enumerate(polys):
        for i, q in enumerate(p['pts']):
            use[key(*q)] += 1 if i in (0, len(p['pts']) - 1) else 2
            vert_ways[key(*q)].add(wi)
    hold_keys = {key(h['x'], h['z']): h for h in A['holds']}
    stand_keys = {key(*s['nose']): s for s in ST['stands']}
    # capped push ends become nodes on their own lead-in
    push_end_keys = {}
    for s_ in ST['stands']:
        pu = s_.get('push')
        if pu and pu['capped']:
            push_end_keys[key(*pu['junction'])] = s_['name']
    node_id = {}
    nodes = []

    def nid(k, kind):
        if k not in node_id:
            node_id[k] = len(nodes)
            nodes.append({'id': len(nodes), 'x': k[0], 'z': k[1], 'kind': kind})
        return node_id[k]
    # insert the capped push-end points into their lead-in polylines
    for k, nm in push_end_keys.items():
        P0 = Point(*k)
        best = None
        for wi, p in enumerate(polys):
            if p['kind'] != 'leadin':
                continue
            for i, (a, b) in enumerate(zip(p['pts'][:-1], p['pts'][1:])):
                d = LineString([a, b]).distance(P0)
                if best is None or d < best[0]:
                    best = (d, wi, i)
        d, wi, i = best
        if d < 0.05 and key(*polys[wi]['pts'][i]) != k and key(*polys[wi]['pts'][i + 1]) != k:
            polys[wi]['pts'].insert(i + 1, k)
            if nm in own_seg:      # the split segment stays part of the stand's own lead-in
                a, b = key(*polys[wi]['pts'][i]), key(*polys[wi]['pts'][i + 2])
                own_seg[nm] |= {frozenset((a, k)), frozenset((k, b))}
            vert_ways[k].add(wi)
    for p in polys:
        for i, q in enumerate(p['pts']):
            k = key(*q)
            if i in (0, len(p['pts']) - 1) or use[k] > 2 or k in hold_keys or k in stand_keys or k in push_end_keys:
                nid(k, 'junction')
    # ------------------------------------------------------------------ links
    links = []
    for wi, p in enumerate(polys):
        pts = p['pts']; cur = [pts[0]]
        for q in pts[1:]:
            cur.append(q)
            if key(*q) in node_id:
                a, b = node_id[key(*cur[0])], node_id[key(*q)]
                L = sum(math.dist(u, v) for u, v in zip(cur[:-1], cur[1:]))
                if a != b and L > 0.05:
                    ev = {'osm_way': p['osm'], 'version': p['version']}
                    if p['kind'] == 'runway':
                        ev['note'] = 'OSM runway way, extended to the placed runway ends of data/sha_airport.json (inf)'
                    elif p['moved']:
                        ev['refit'] = 'vertices moved by the taxiway re-fit (data/meas/twy_refit.json)'
                    links.append({'id': len(links), 'a': a, 'b': b, 'kind': p['kind'], 'ref': p['ref'], 'way': wi,
                                  'len': R2(L), 'pts': [[R2(u), R2(v)] for u, v in cur],
                                  'dir': 'ab' if p['oneway'] else 'both', 'use': 'all',
                                  'status': p['status'], 'src': 'obs', 'evidence': ev})
                cur = [q]
    # node kinds
    for k, h in hold_keys.items():
        if k in node_id:
            n = nodes[node_id[k]]; n.update({'kind': 'hold', 'runway': h['runway'], 'osm': h['id']})
    for k, s in stand_keys.items():
        if k in node_id:
            nodes[node_id[k]].update({'kind': 'stand', 'ref': s['name']})
    for k, nm in push_end_keys.items():
        if k in node_id and nodes[node_id[k]]['kind'] == 'junction':
            nodes[node_id[k]].update({'kind': 'push_end', 'ref': nm})
    rwy_nodes = defaultdict(set)
    for l in links:
        if l['kind'] == 'runway':
            for e in (l['a'], l['b']):
                rwy_nodes[l['ref']].add(e)
    for rid, ns in rwy_nodes.items():
        for e in ns:
            if nodes[e]['kind'] == 'junction':
                nodes[e]['kind'] = 'rwy'; nodes[e]['runway'] = rid
        for end, pt in zip(('north', 'south'), rwy_info[rid]['centreline']['pts']):
            e = node_id[key(*pt)]
            nodes[e].update({'kind': 'rwy_end', 'runway': rid, 'end': (rid.split('/')[0] if end == 'north' else rid.split('/')[1])})
    # node provenance
    for k, i in node_id.items():
        n = nodes[i]; ws = sorted({polys[w]['osm'] for w in vert_ways.get(k, ())})
        if n['kind'] == 'rwy_end':
            n.update(src='inf', evidence='placed runway end of data/sha_airport.json (Sentinel-2 / Umbra + AIP length)')
        elif n['kind'] == 'push_end':
            n.update(src='inf', evidence='end of the capped push of stand %s (data/sha_stands.json push, QA C1 M5)'
                     % n['ref'])
        elif n['kind'] == 'hold':
            n.update(src='obs', evidence='OSM aeroway=holding_position %s' % n['osm'])
        elif n['kind'] == 'stand':
            n.update(src='obs', evidence='OSM parking_position ref node (stand %s)' % n['ref'])
        else:
            n.update(src='obs', evidence='vertex of OSM way(s) ' + ', '.join(str(w_) for w_ in ws[:6]))

    # ------------------------------------------------------------------ lead-in classification (QA C1 M6)
    n_own = n_lane = 0
    for l in links:
        if l['kind'] != 'leadin':
            continue
        segs = {frozenset(p) for p in zip([key(*q) for q in l['pts']][:-1], [key(*q) for q in l['pts']][1:])}
        owner = [nm for nm, ss in own_seg.items() if segs <= ss]
        if len(owner) == 1:
            l['stand'] = owner[0]; l['use'] = 'stand'; n_own += 1
            l['evidence']['role'] = 'own lead-in of stand %s (first / last leg of its routes only)' % owner[0]
        else:
            l['kind'] = 'taxilane'; l['osm_kind'] = 'leadin'; l['src'] = 'inf'; n_lane += 1
            l['evidence']['role'] = 'OSM parking_position line used as an apron lane (not the own lead-in of a stand)'

    # ------------------------------------------------------------------ AIP use rules (one-way by purpose)
    d_lines = [LineString(p['pts']) for p in polys if p['ref'] == 'D']

    def toward_d(l):
        """True when travelling a -> b goes towards TWY D. Decided per OSM WAY (its two end points), so that all links
        of one way get the same direction (a per-link test zig-zagged on short links near D)"""
        if l.get('way') is not None:
            wp = polys[l['way']]['pts']
            da = min(Point(wp[0]).distance(x) for x in d_lines); db = min(Point(wp[-1]).distance(x) for x in d_lines)
            fwd = db < da                                    # the way runs towards D
            ia = min(range(len(wp)), key=lambda i: math.dist(wp[i], (nodes[l['a']]['x'], nodes[l['a']]['z'])))
            ib = min(range(len(wp)), key=lambda i: math.dist(wp[i], (nodes[l['b']]['x'], nodes[l['b']]['z'])))
            return fwd == (ib > ia)
        pa = (nodes[l['a']]['x'], nodes[l['a']]['z']); pb = (nodes[l['b']]['x'], nodes[l['b']]['z'])
        da = min(Point(pa).distance(x) for x in d_lines); db = min(Point(pb).distance(x) for x in d_lines)
        return db < da
    for l in links:
        if l['ref'] in AIP_RULES['arrival_only']['refs']:
            l['use'] = 'arrival'; l['rule'] = 'arrival_only'
            if l['dir'] == 'both':
                l['dir'] = 'ba' if toward_d(l) else 'ab'; l['dir_src'] = 'inf (away from TWY D)'
            else:
                l['dir_src'] = 'OSM oneway=yes'
        elif l['ref'] in AIP_RULES['departure_only']['refs']:
            l['use'] = 'departure'; l['rule'] = 'departure_only'
            if l['dir'] == 'both':
                # no OSM oneway tag: the AIP gives the use (departure) and, for L15-L17, one aircraft at a time - not a
                # direction. A2 inferred 'towards TWY D'; with the turn rule that blocked T2 departures (QA C1 fix
                # round 1), so these links stay usable both ways, one aircraft at a time [inf]
                l['dir_src'] = 'no OSM oneway: both directions, departures only, one aircraft at a time (AIP (mirror) 3.1.5)'
            else:
                l['dir_src'] = 'OSM oneway=yes'
        elif l['dir'] == 'ab':
            l['dir_src'] = 'OSM oneway=yes'
        if l['ref'] in ('N', 'S', 'BN', 'BS'):
            l['span_max'] = 65.0; l['span_normal_max'] = 36.0; l['rule'] = 'route_north_south'
            l['note'] = 'AIP (mirror) AD 2.20 2.3.3: span < 36 m normal, 36-65 m limited, >= 65 m forbidden; one-way BN -> N / BS -> S'
    for l in links:
        if l['dir'] == 'ba':
            l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]; l['dir'] = 'ab'
    b_lines = [LineString(p['pts']) for p in polys if p['ref'] == 'B']
    for l in links:
        if l['ref'] in ('BN', 'BS') and l['dir'] == 'both':
            pa = Point(nodes[l['a']]['x'], nodes[l['a']]['z']); pb = Point(nodes[l['b']]['x'], nodes[l['b']]['z'])
            if min(pa.distance(x) for x in b_lines) > min(pb.distance(x) for x in b_lines):
                l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]
            l['dir'] = 'ab'; l['use'] = 'arrival'; l['dir_src'] = 'AIP (mirror) ROUTE-NORTH / SOUTH one-way (direction: away from TWY B)'
    dego = Counter()
    for l in links:
        dego[l['a']] += 1; dego[l['b']] += 1
    for lead, main_ in (('BN', 'N'), ('BS', 'S')):
        ends_l = {e for l in links if l['ref'] == lead for e in (l['a'], l['b']) if dego[e] == 1}
        ends_m = {e for l in links if l['ref'] == main_ for e in (l['a'], l['b']) if dego[e] == 1}
        best = None
        for a in ends_l:
            for b in ends_m:
                d = math.dist((nodes[a]['x'], nodes[a]['z']), (nodes[b]['x'], nodes[b]['z']))
                if d < 150 and (best is None or d < best[0]):
                    best = (d, a, b)
        if best:
            d, a, b = best
            links.append({'id': len(links), 'a': a, 'b': b, 'kind': 'taxiway', 'ref': main_, 'way': None, 'len': R2(d),
                          'pts': [[nodes[a]['x'], nodes[a]['z']], [nodes[b]['x'], nodes[b]['z']]], 'dir': 'both',
                          'use': 'all', 'status': 'open', 'gap': True, 'src': 'inf',
                          'evidence': 'straight join of %s and %s across the part outside the detailed extent '
                                      '(clipped)' % (lead, main_)})
    for lead, main_ in (('BN', 'N'), ('BS', 'S')):
        lead_nodes = {e for l in links if l['ref'] == lead for e in (l['a'], l['b'])}
        ml = [l for l in links if l['ref'] == main_]
        start = {e for l in ml for e in (l['a'], l['b'])} & lead_nodes
        order = {e: 0 for e in start}; q = deque(start)
        while q:
            v = q.popleft()
            for l in ml:
                if v in (l['a'], l['b']):
                    w = l['b'] if l['a'] == v else l['a']
                    if w not in order:
                        order[w] = order[v] + 1; q.append(w)
        for l in ml:
            if l['a'] in order and l['b'] in order and order[l['a']] > order[l['b']]:
                l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]
            elif l['a'] not in order and toward_d(l) is False:
                l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]
            l['dir'] = 'ab'; l['use'] = 'arrival'
            l['dir_src'] = ('AIP (mirror) ROUTE-NORTH / SOUTH one-way (direction: along %s away from %s)' % (main_, lead)
                            if l['a'] in order else 'AIP (mirror) ROUTE-NORTH / SOUTH one-way (direction inf: towards TWY D; '
                            'joined to %s by an unnamed OSM link)' % lead)

    # ------------------------------------------------------------------ runway links, entries / exits / rapid exits
    for l in links:
        if l['kind'] == 'runway':
            l['use'] = 'runway'
            l['rule'] = 'runway: not for taxi routing; only an explicit backtrack (QA C1 H2)'
    adj = defaultdict(list)
    for l in links:
        adj[l['a']].append(l); adj[l['b']].append(l)
    runways = []
    new_holds = []
    rapid = []
    for rid, r in rwy_info.items():
        cl = r['centreline']['pts']; ax = (cl[1][0] - cl[0][0], cl[1][1] - cl[0][1]); La = math.hypot(*ax)
        ux, uz = ax[0] / La, ax[1] / La          # southward unit vector
        exits = []
        for e in sorted(rwy_nodes[rid], key=lambda e: (nodes[e]['x'] - cl[0][0]) * ux + (nodes[e]['z'] - cl[0][1]) * uz):
            s_along = R2((nodes[e]['x'] - cl[0][0]) * ux + (nodes[e]['z'] - cl[0][1]) * uz)
            for l in adj[e]:
                if l['kind'] == 'runway':
                    continue
                pts = l['pts'] if l['a'] == e else l['pts'][::-1]
                far = pts[min(len(pts) - 1, 3)]
                vx, vz = far[0] - nodes[e]['x'], far[1] - nodes[e]['z']; vl = math.hypot(vx, vz) or 1
                cosang = (vx * ux + vz * uz) / vl          # + = leaves towards the south
                side = 'east' if (vx * -uz + vz * ux) < 0 else 'west'
                ang = math.degrees(math.acos(max(-1, min(1, abs(cosang)))))
                rec = {'node': e, 'link': l['id'], 'ref': l['ref'], 's_m': s_along, 'side': side,
                       'angle_deg': R2(ang)}
                if ang < 50:
                    land = rid.split('/')[0] if cosang > 0 else rid.split('/')[1]
                    if RAPID_END_GUARD < s_along < La - RAPID_END_GUARD:
                        rec['rapid_exit_for'] = land
                        rapid.append((e, l, land))
                    else:
                        rec['end_connector'] = 'acute link near the runway end: entry / exit, both directions'
                exits.append(rec)
        crossing_refs = sorted({x['ref'] for x in exits if x['ref'] and re.match(r'^H\d$', x['ref'])})
        runways.append({'id': rid, 'ends': [{'end': rid.split('/')[0], 'xz': cl[0]}, {'end': rid.split('/')[1], 'xz': cl[1]}],
                        'connections': exits, 'crossing_taxiways_osm': crossing_refs, 'src': 'obs',
                        'evidence': 'OSM runway way %d and the taxiway ways that end on it; rapid exits = links '
                                    '< 50 deg off the runway more than %.0f m from either end (inf)'
                                    % (rwy_osm[rid]['properties']['@id'], RAPID_END_GUARD)})
    # rapid exits: one-way away from the runway, arrival only, along the chain of links with the same ref
    n_rapid_links = 0
    for e, l0, land in rapid:
        chain = [(l0, e)]
        if l0['ref']:
            seen = {l0['id']}; frontier = [(l0, e)]
            while frontier:
                l, frm = frontier.pop()
                to = l['b'] if l['a'] == frm else l['a']
                if nodes[to]['kind'] in ('rwy', 'rwy_end'):
                    continue
                for l2 in adj[to]:
                    if l2['id'] not in seen and l2['ref'] == l0['ref'] and l2['kind'] != 'runway':
                        seen.add(l2['id']); chain.append((l2, to)); frontier.append((l2, to))
        for l, frm in chain:
            if l['a'] != frm:
                l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]
            l['dir'] = 'ab'; l['use'] = 'arrival'
            l.setdefault('for_landing', [])
            if land not in l['for_landing']:
                l['for_landing'].append(land)
            l['rule'] = 'rapid_exit'; l['dir_src'] = 'rapid exit: one-way runway -> taxiway (QA C1 H2) [inf]'
            n_rapid_links += 1
    # inferred runway-holding positions (as before)
    for rid, r in rwy_info.items():
        line = LineString(r['centreline']['pts'])
        rkeys = {key(nodes[e]['x'], nodes[e]['z']) for e in rwy_nodes[rid]}
        for p in polys:
            if p['kind'] not in ('taxiway', 'taxilane') or p['status'] != 'open':
                continue
            ks = [key(*q) for q in p['pts']]
            for i, k in enumerate(ks):
                if k not in rkeys:
                    continue
                for step in (1, -1):
                    j = i; prev = p['pts'][i]
                    while 0 <= j + step < len(ks):
                        q = p['pts'][j + step]
                        d0 = line.distance(Point(prev)); d1 = line.distance(Point(q))
                        if d0 < HOLD_DIST <= d1:
                            t = (HOLD_DIST - d0) / max(d1 - d0, 1e-6)
                            hp = (prev[0] + t * (q[0] - prev[0]), prev[1] + t * (q[1] - prev[1]))
                            if not [h for h in A['holds'] if math.dist((h['x'], h['z']), hp) < 30]:
                                cx = line.interpolate(line.project(Point(hp)))
                                side = 'east' if hp[0] > cx.x else 'west'
                                new_holds.append({'x': R2(hp[0]), 'z': R2(hp[1]), 'runway': rid, 'taxiway': p['ref'],
                                                  'osm_way': p['osm'], 'side': side, 'src': 'inf',
                                                  'rule': 'runway-holding position %d m from the centreline (inf)' % HOLD_DIST,
                                                  'evidence': 'ICAO Annex 14 Table 3-2, code 4 precision approach CAT I '
                                                              '(from memory); no OSM hold within 30 m on OSM way %d'
                                                              % p['osm']})
                            break
                        if d1 < d0 - 0.5:
                            break
                        prev = q; j += step
    hold_inf = []
    for h in new_holds:
        if all(math.dist((h['x'], h['z']), (g['x'], g['z'])) > 15 for g in hold_inf):
            hold_inf.append(h)
    for h in hold_inf:
        h['node'] = None
    # ------------------------------------------------------------------ push-back links (along the own lead-in)
    push_of = {}
    for s in ST['stands']:
        p = s.get('push')
        if not p:
            continue
        a = node_id.get(key(*s['nose'])); b = node_id.get(key(*p['junction']))
        if a is None or b is None:
            continue
        pl = {'id': len(links), 'a': a, 'b': b, 'kind': 'push', 'ref': s['name'], 'stand': s['name'], 'way': None,
              'len': R2(p['push_dist_m']), 'pts': p['pts'], 'dir': 'ab', 'use': 'departure', 'status': 'open',
              'tail_headings': p.get('tail_headings'), 'capped': p['capped'], 'src': 'inf',
              'evidence': 'data/sha_stands.json stands[%s].push: %s' % (s['name'], p['rule'])}
        links.append(pl); push_of[s['name']] = pl
    # ------------------------------------------------------------------ allowed transitions (turn table)
    adj = defaultdict(list)
    for l in links:
        adj[l['a']].append(l); adj[l['b']].append(l)

    def can_enter(l, v):           # l can be travelled INTO node v
        return l['b'] == v or (l['dir'] == 'both' and l['a'] == v)

    def can_leave(l, v):
        return l['a'] == v or (l['dir'] == 'both' and l['b'] == v)

    def d_in(l, v):
        return _dir_at(l['pts'] if l['b'] == v else l['pts'][::-1], False)

    def d_out(l, v):
        return _dir_at(l['pts'] if l['a'] == v else l['pts'][::-1], True)
    turns = {}
    tstat = Counter()
    for v, ls in adj.items():
        nk = nodes[v]['kind']
        pairs = []
        for li in ls:
            if not can_enter(li, v):
                continue
            for lo in ls:
                if lo is li or not can_leave(lo, v):
                    continue
                if li['kind'] == 'push':
                    # end of a push: the tail is turned onto the lane (either direction) - no angle limit; never back
                    # onto the own lead-in towards the stand, never into another stand's own lead-in
                    if lo.get('stand') and (lo['stand'] != li['stand'] or not li['capped']):
                        tstat['push_blocked'] += 1; continue
                    pairs.append([li['id'], lo['id']]); tstat['push'] += 1; continue
                if lo['kind'] == 'push':
                    continue
                if nk in ('rwy', 'rwy_end') and li['kind'] != 'runway' and lo['kind'] != 'runway':
                    rid = nodes[v]['runway']
                    if not (li['ref'] in CROSS[rid] and lo['ref'] in CROSS[rid]):
                        tstat['crossing_not_allowed'] += 1; continue
                ang = _turn(d_in(li, v), d_out(lo, v))
                if ang > TURN_MAX + TURN_TOL:
                    tstat['turn_gt_90'] += 1; continue
                pairs.append([li['id'], lo['id']]); tstat['allowed'] += 1
        if pairs:
            turns[str(v)] = pairs
    allowed = {(a, b) for v, ps in turns.items() for a, b in ps}

    # ------------------------------------------------------------------ edge-based reachability (QA C1 H2 item 4)
    def route(start_states, goal, mode, stand):
        """Dijkstra over (link, exit node) states. mode 'arrival' | 'departure'; runway links never used; links with
        use 'stand' only for this stand; returns (length, links, max turn) or None"""
        import heapq as hq_
        dist = {}; prev = {}; h = []
        for l, v in start_states:
            dist[(l['id'], v)] = l['len']; hq_.heappush(h, (l['len'], l['id'], v))
        L_by = {l['id']: l for l in links}
        while h:
            d, lid, v = hq_.heappop(h)
            if d > dist.get((lid, v), 1e18):
                continue
            if goal(lid, v):
                path = [lid]; st = (lid, v)
                while st in prev:
                    st = prev[st]; path.append(st[0])
                return d, path[::-1]
            for lo in adj[v]:
                if (lid, lo['id']) not in allowed or lo['use'] == 'runway' or lo['status'] != 'open':
                    continue
                if lo['use'] not in ('all', mode, 'stand'):
                    continue
                if lo.get('stand') and lo['stand'] != stand:
                    continue
                w = lo['b'] if lo['a'] == v else lo['a']
                nd = d + lo['len']
                if nd < dist.get((lo['id'], w), 1e18):
                    dist[(lo['id'], w)] = nd; prev[(lo['id'], w)] = (lid, v); hq_.heappush(h, (nd, lo['id'], w))
        return None
    L_by = {l['id']: l for l in links}
    stand_node = {s['name']: node_id.get(key(*s['nose'])) for s in ST['stands']}
    # take-off entries: runway nodes within ENTRY_WIN of the runway end (+ the AIP intersection take-offs)
    ends_xy = {}
    for rid, r in rwy_info.items():
        a_, b_ = rid.split('/'); cl = r['centreline']['pts']
        ends_xy[a_] = (cl[0], (cl[1][0] - cl[0][0], cl[1][1] - cl[0][1]), rid)
        ends_xy[b_] = (cl[1], (cl[0][0] - cl[1][0], cl[0][1] - cl[1][1]), rid)
    dep_ok = Counter(); dep_fail = defaultdict(list); dep_len = []
    for end, (pt, ax, rid) in ends_xy.items():
        Lx = math.hypot(*ax); hd = (ax[0] / Lx, ax[1] / Lx)
        entry = {e for e in rwy_nodes[rid] if math.dist((nodes[e]['x'], nodes[e]['z']), pt) <= ENTRY_WIN}
        ix = INTERSECTION_TO.get(end)
        entry_links = set()
        for e in rwy_nodes[rid]:
            for l in adj[e]:
                if l['kind'] == 'runway' or not can_enter(l, e):
                    continue
                if _turn(d_in(l, e), hd) > TURN_MAX + TURN_TOL:   # line-up turn onto the take-off heading
                    continue
                if e in entry or (ix and l['ref'] == ix):
                    entry_links.add((l['id'], e))
        for nm, sn in stand_node.items():
            pl = push_of.get(nm)
            if sn is None or pl is None:
                dep_fail[nm].append('no push link'); continue
            r_ = route([(pl, pl['b'])], lambda lid, v: (lid, v) in entry_links, 'departure', nm)
            if r_:
                dep_ok[end] += 1; dep_len.append(r_[0])
            else:
                dep_fail[nm].append('cannot depart ' + end)
    arr_ok = Counter(); arr_fail = defaultdict(list); arr_pairs = Counter(); arr_len = []
    for end, (pt, ax, rid) in ends_xy.items():
        Lx = math.hypot(*ax); land_hd = (-ax[0] / Lx, -ax[1] / Lx)   # landing on end X rolls away from X's end
        # landing direction 'end': aircraft lands at threshold 'end' and rolls towards the other end
        land_hd = (ax[0] / Lx, ax[1] / Lx)
        starts = []
        for e in rwy_nodes[rid]:
            for l in adj[e]:
                if l['kind'] == 'runway' or not can_leave(l, e) or l['ref'] in NO_VACATE:
                    continue
                if l.get('for_landing') and end not in l['for_landing']:
                    continue
                if _turn(land_hd, d_out(l, e)) > TURN_MAX + TURN_TOL:
                    continue
                starts.append((l, l['b'] if l['a'] == e else l['a']))
        for nm, sn in stand_node.items():
            if sn is None:
                arr_fail[nm].append('no node'); continue
            r_ = route(starts, lambda lid, v, sn=sn: v == sn, 'arrival', nm)
            if r_:
                arr_ok[end] += 1; arr_len.append(r_[0])
            else:
                arr_fail[nm].append('cannot arrive landing ' + end)
        arr_pairs[end] = len(starts)
    # ------------------------------------------------------------------ connectivity (undirected) as before
    N = len(nodes)
    und = defaultdict(set)
    for l in links:
        und[l['a']].add(l['b']); und[l['b']].add(l['a'])
    comp = [-1] * N; ncomp = 0; sizes = []
    for i in range(N):
        if comp[i] >= 0 or i not in und:
            continue
        q = deque([i]); comp[i] = ncomp; c = 0
        while q:
            v = q.popleft(); c += 1
            for w in und[v]:
                if comp[w] < 0:
                    comp[w] = ncomp; q.append(w)
        sizes.append(c); ncomp += 1
    main_c = max(range(ncomp), key=lambda c: sizes[c])
    checks['components'] = {'n': ncomp, 'sizes_top': sorted(sizes, reverse=True)[:8],
                            'nodes_outside_main': sum(1 for i in range(N) if comp[i] not in (-1, main_c))}
    off_main = Counter()
    for l in links:
        if comp[l['a']] != main_c:
            off_main[(l['kind'], l['ref'], l['status'])] += 1
    checks['links_outside_main_component'] = [list(k) + [v] for k, v in off_main.most_common(20)]
    checks['reachability_edge_based'] = {
        'rule': 'Dijkstra over (link, node) states using only the transitions in turns (<= %g deg + tolerance), one-way and use '
                'rules, runway links excluded, own lead-ins only for their stand; departures start with the push link '
                'and end on a link that enters a runway node within %g m of the take-off end (or the AIP intersection '
                'H2 / H6) with a line-up turn <= %g deg; arrivals start on a link leaving the runway (rapid exits for '
                'their landing direction, other exits within %g deg of the landing heading, not H3 / H4 / H5) and end '
                'at the stand node' % (TURN_MAX, ENTRY_WIN, TURN_MAX, TURN_MAX),
        'departures_ok_per_takeoff_end': dict(dep_ok), 'arrivals_ok_per_landing_end': dict(arr_ok),
        'arrival_exit_links_per_landing_end': dict(arr_pairs),
        'stands_total': len(stand_node),
        'stands_ok_all_4_departures_and_arrivals': sum(1 for nm in stand_node if nm not in dep_fail and nm not in arr_fail),
        'failures': {nm: dep_fail.get(nm, []) + arr_fail.get(nm, []) for nm in sorted(set(dep_fail) | set(arr_fail))},
        'route_len_m_median': {'departure': R2(sorted(dep_len)[len(dep_len) // 2]) if dep_len else None,
                               'arrival': R2(sorted(arr_len)[len(arr_len) // 2]) if arr_len else None}}
    checks['turn_table'] = dict(tstat, nodes_with_transitions=len(turns))
    checks['links_by_use'] = dict(Counter(l['use'] for l in links))
    checks['leadin_classification'] = {'own_leadin_links': n_own, 'apron_lane_links_from_leadins': n_lane}
    checks['rapid_exit_links'] = n_rapid_links
    checks['inferred_holds'] = len(hold_inf)
    checks['osm_holds'] = len(A['holds'])
    checks['one_way_links'] = {'%s:%s' % k: v for k, v in sorted(Counter((l['use'], l['ref']) for l in links
                                                                      if l['dir'] == 'ab' and l['kind'] != 'push').items(), key=str)}
    checks['aip_probes'] = {'n': len(AIP_RULES), 'where': 'probed at build time only when the local AIP mirror text '
                            'exists; the result goes to refs/cache/aip_checks/build_taxigraph.json (local only, never '
                            'committed)'}
    if aip_txt:
        norm = lambda t: re.sub(r'\s+', '', t)  # noqa: E731
        nt = norm(aip_txt)
        os.makedirs(os.path.join(ROOT, 'refs/cache/aip_checks'), exist_ok=True)
        json.dump({'aip_probes': {k: norm(v['probe']) in nt for k, v in AIP_RULES.items()}},
                  open(os.path.join(ROOT, 'refs/cache/aip_checks/build_taxigraph.json'), 'w'), indent=1)
    # ------------------------------------------------------------------ sfo3d-compatible fields
    ways = [{'ref': p['ref'], 'kind': p['kind'], 'osm': p['osm'], 'src': 'obs',
             'evidence': {'osm_way': p['osm'], 'version': p['version']}} for p in polys]
    edges = []
    for wi, p in enumerate(polys):
        if p['status'] != 'open':
            continue
        for u, v in zip(p['pts'][:-1], p['pts'][1:]):
            if math.dist(u, v) > 0.05:
                edges.append([R2(u[0]), R2(u[1]), R2(v[0]), R2(v[1]), wi])
    leadins = [{'ref': s['name'], 'pts': s['leadin'], 'stop': s['nose'], 'hdg': s['hdg'], 'src': 'obs',
                'evidence': 'primary lead-in of stand %s over the OSM lead-in network (data/sha_stands.json)' % s['name']}
               for s in ST['stands'] if s['leadin']]
    out = {
        'what': 'ZSSS taxi graph for SHA Live 3D (task A2): OSM taxiway / taxilane / lead-in centrelines, OSM runway '
                'centrelines to the A1 placed ends, holds, push-back links, an allowed-transition (turn) table, AIP '
                '(mirror) use rules',
        'frame': F.FRAME_ID, 'generator': 'tools/airport/build_taxigraph.py',
        'source': 'data/sha_airport.json (OSM pinned 2026-11-14 + A1 re-fit), OSM lead-in ways, data/sha_stands.json',
        'licence': A['licence'], 'attribution': A['attribution'], 'build_note': A['build_note'],
        'src_legend': A['src_legend'],
        'halfWidth': 11.5,
        'halfWidth_note': 'half of the 23 m main-taxiway width (AIP (mirror) AD 2.8) - a "paved" test for gear points',
        'rules': {'notice': AIP_NOTICE, 'src': 'obs', 'refs': ['aip_mirror'],
                  'facts': {k: {'text': v['text'], **({'refs': v['refs']} if 'refs' in v else {})}
                            for k, v in AIP_RULES.items()}},
        'routing': {'turns': 'turns[node] = allowed [link_in, link_out] pairs: turn <= %g deg + %g deg digitising '
                             'tolerance (direction over the first %g m of each link), one-way respected, runway crossings '
                             'only on %s; at a push end any lane direction (the tail is turned)'
                             % (TURN_MAX, TURN_TOL, TURN_LOOK,
                                '; '.join('%s: %s' % (k, ', '.join(sorted(v))) for k, v in sorted(CROSS.items()))),
                    'runway': "links with use 'runway' are not for taxi routing; only an explicit backtrack may use them",
                    'rapid_exits': "use 'arrival', one-way runway -> taxiway, for_landing = landing direction(s)",
                    'stand': "links with use 'stand' (own lead-in, stand = <name>) only as the first or last leg of "
                             "that stand's routes; push links (kind 'push') only as the first leg of a departure",
                    'apron_lanes': "OSM parking_position lines that are not a stand's own lead-in: kind 'taxilane', "
                                   "osm_kind 'leadin', src 'inf'",
                    'src': 'inf', 'evidence': 'QA C1 H2 / M6 (docs/phase1/qa_data.md); AIP (mirror) AD 2.20 2.2.5, '
                                              '2.3.1, 2.3.2, 3.1.5'},
        'rules_note': 'use = arrival / departure from AD 2.20 3.1.5 and 2.3.3; the geometric direction of one-way links '
                      'is the OSM oneway tag where present, else inferred (dir_src). Taxiway span limits on the aprons '
                      '(AD 2.20 3.1.1 chart) are not transcribed. Runway-holding positions: OSM where mapped (src obs), '
                      'else inferred at %d m (hold_inf).' % HOLD_DIST,
        'nodes': nodes, 'links': links, 'turns': turns, 'runways': runways, 'hold_inf': hold_inf,
        'ways': ways, 'edges': edges, 'aprons': [a['ring'] for a in A['aprons']],
        'aprons_src': {'src': 'obs', 'evidence': 'OSM aeroway=apron polygons (data/sha_airport.json aprons[]); kept as '
                                                 'bare rings for sfo3d TaxiNet'},
        'leadins': leadins,
        'checks_at_build': checks,
        'counts': {'nodes': len(nodes), 'links': len(links), 'by_kind': dict(Counter(l['kind'] for l in links)),
                   'by_use': dict(Counter(l['use'] for l in links)), 'turn_pairs': len(allowed),
                   'edges': len(edges), 'ways': len(ways), 'hold_inf': len(hold_inf)},
    }
    s = json.dumps(out, separators=(',', ':'), ensure_ascii=False)
    open(OUT_JSON, 'w').write(s)
    open(OUT_JS, 'w').write('// generated by tools/airport/build_taxigraph.py. ODbL 1.0: contains information from '
                            'OpenStreetMap (c) OpenStreetMap contributors (pinned 2026-11-14); contains modified '
                            'Copernicus Sentinel data 2026; Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0, modified. '
                            'rules: AIP (mirror) short cited facts, not covered by ODbL.\n'
                            'window.SHA_TAXIGRAPH = ' + s + ';\n')
    print(json.dumps(out['counts']))
    print(json.dumps({k: v for k, v in checks.items() if k not in ('one_way_links',)})[:4000])


if __name__ == '__main__':
    main()
