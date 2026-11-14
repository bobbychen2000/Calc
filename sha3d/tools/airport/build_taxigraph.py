"""Taxi graph for SHA Live 3D -> sha3d/data/sha_taxigraph.json and sha_taxigraph.js (window.SHA_TAXIGRAPH). Task A2.

    python3 -I sha3d/tools/airport/build_taxigraph.py [SHA3D_DIR]

Format: sfo3d data/sfo_taxigraph.js (tools/live/build_taxigraph.py) fields kept for the traffic engine (TaxiNet):
  edges [[x0, z0, x1, z1, wayIndex]], ways [{ref, kind, osm}], aprons [[[x, z]..]], leadins [{ref, pts, stop, hdg}],
  halfWidth; plus a routable node / link graph:
  nodes [{id, x, z, kind, ref?, ...}]   kinds: junction, end, stand, hold, hold_inf, rwy, rwy_end
  links [{id, a, b, kind, ref, len, pts, dir, use, span_max, ...}]
        kind: taxiway | taxilane | leadin | runway | push ; dir: 'both' | 'ab' (one-way a -> b)
        use: 'all' | 'arrival' | 'departure' (AIP (mirror) AD 2.20 3.1.5; ROUTE-NORTH / ROUTE-SOUTH 2.3.3)
  runways [{id, ends, entries[], exits[], crossings[]}], rules {...} (AIP short facts), checks_at_build.
Inputs (committed): data/sha_airport.json (A1: taxiways incl. the two re-fitted runs, taxilanes, holds, runways,
aprons), refs/cache/osm_pinned/zsss_osm_pinned.geojson (OSM runway ways with their junction nodes, lead-in ways),
data/sha_stands.json (stands, push-back options). Vertices are joined where they coincide (shared OSM nodes; world
coordinates to 0.01 m from the same frame).
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


def key(x, z):
    return (round(x, 2), round(z, 2))


def main():
    A = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
    ST = json.load(open(os.path.join(ROOT, 'data/sha_stands.json')))
    O = OsmStands(ROOT)
    aip_txt = open(AIP_TXT, encoding='utf-8').read() if os.path.exists(AIP_TXT) else None
    checks = {}
    # ------------------------------------------------------------------ polylines
    polys = []   # dicts: pts [(x, z)], kind, ref, osm, oneway (bool, along pts), status
    for t in A['taxiways'] + A['taxilanes']:
        if len(t['pts']) < 2:
            continue
        ow = bool(t.get('oneway'))
        polys.append(dict(pts=[tuple(p) for p in t['pts']], kind=t['kind'], ref=t.get('ref'),
                          osm=int(t['id'].split('/')[-1]), oneway=ow, status=t['status']))
    for f in O.leadin_ways:
        pts = [tuple(R2(v) for v in wxz(c)) for c in f['geometry']['coordinates']]
        polys.append(dict(pts=pts, kind='leadin', ref=None, osm=f['properties']['@id'], oneway=False, status='open'))
    rwy_osm = {f['properties']['tags']['ref']: f for f in O.features
               if f['properties']['tags'].get('aeroway') == 'runway' and f['geometry']['type'] == 'LineString'}
    rwy_info = {r['id']: r for r in A['runways']}
    for rid, f in rwy_osm.items():
        pts = [tuple(R2(v) for v in wxz(c)) for c in f['geometry']['coordinates']]
        cl = rwy_info[rid]['centreline']['pts']            # A1 placed ends (north first)
        if math.dist(pts[0], cl[0]) > math.dist(pts[-1], cl[0]):
            pts = pts[::-1]
        pts = [tuple(cl[0])] + pts + [tuple(cl[1])]
        polys.append(dict(pts=pts, kind='runway', ref=rid, osm=f['properties']['@id'], oneway=False, status='open'))
    # ------------------------------------------------------------------ nodes at junctions / ends
    use = Counter()
    for p in polys:
        for i, q in enumerate(p['pts']):
            use[key(*q)] += 1 if i in (0, len(p['pts']) - 1) else 2
    hold_keys = {key(h['x'], h['z']): h for h in A['holds']}
    stand_keys = {key(*s['nose']): s for s in ST['stands']}
    node_id = {}
    nodes = []

    def nid(k, kind):
        if k not in node_id:
            node_id[k] = len(nodes)
            nodes.append({'id': len(nodes), 'x': k[0], 'z': k[1], 'kind': kind})
        return node_id[k]
    for p in polys:
        for i, q in enumerate(p['pts']):
            k = key(*q)
            if i in (0, len(p['pts']) - 1) or use[k] > 2 or k in hold_keys or k in stand_keys:
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
                    links.append({'id': len(links), 'a': a, 'b': b, 'kind': p['kind'], 'ref': p['ref'], 'way': wi,
                                  'len': R2(L), 'pts': [[R2(u), R2(v)] for u, v in cur],
                                  'dir': 'ab' if p['oneway'] else 'both', 'use': 'all',
                                  'status': p['status']})
                cur = [q]
    # node kinds
    for k, h in hold_keys.items():
        if k in node_id:
            n = nodes[node_id[k]]; n.update({'kind': 'hold', 'runway': h['runway'], 'osm': h['id'], 'src': 'obs'})
    for k, s in stand_keys.items():
        if k in node_id:
            nodes[node_id[k]].update({'kind': 'stand', 'ref': s['name']})
    deg = Counter()
    for l in links:
        deg[l['a']] += 1; deg[l['b']] += 1
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

    # ------------------------------------------------------------------ AIP use rules (one-way by purpose)
    d_lines = [LineString(p['pts']) for p in polys if p['ref'] == 'D']

    def toward_d(l):
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
                l['dir'] = 'ab' if toward_d(l) else 'ba'; l['dir_src'] = 'inf (towards TWY D)'
            else:
                l['dir_src'] = 'OSM oneway=yes'
        elif l['dir'] == 'ab':
            l['dir_src'] = 'OSM oneway=yes'
        if l['ref'] in ('N', 'S', 'BN', 'BS'):
            l['span_max'] = 65.0; l['span_normal_max'] = 36.0; l['rule'] = 'route_north_south'
            l['note'] = 'AIP (mirror) AD 2.20 2.3.3: span < 36 m normal, 36-65 m limited, >= 65 m forbidden; one-way BN -> N / BS -> S'
    # normalise 'ba' to 'ab' by swapping
    for l in links:
        if l['dir'] == 'ba':
            l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]; l['dir'] = 'ab'
    # ROUTE-NORTH / SOUTH direction (AIP: BN -> N, BS -> S): BN / BS run from TWY B outwards; N / S are oriented
    # along their chain away from the node they share with BN / BS (breadth-first order)
    b_lines = [LineString(p['pts']) for p in polys if p['ref'] == 'B']
    for l in links:
        if l['ref'] in ('BN', 'BS') and l['dir'] == 'both':
            pa = Point(nodes[l['a']]['x'], nodes[l['a']]['z']); pb = Point(nodes[l['b']]['x'], nodes[l['b']]['z'])
            if min(pa.distance(x) for x in b_lines) > min(pb.distance(x) for x in b_lines):
                l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]
            l['dir'] = 'ab'; l['use'] = 'arrival'; l['dir_src'] = 'AIP (mirror) ROUTE-NORTH / SOUTH one-way (direction: away from TWY B)'
    # the extent clip cuts ROUTE-NORTH between the end of BN and the start of N (both run outside the 23.5 km2
    # extent): join the two dead ends with a straight gap link (inf) so that the route stays usable in the graph
    dego = Counter()
    for l in links:
        dego[l['a']] += 1; dego[l['b']] += 1
    for lead, main in (('BN', 'N'), ('BS', 'S')):
        ends_l = {e for l in links if l['ref'] == lead for e in (l['a'], l['b']) if dego[e] == 1}
        ends_m = {e for l in links if l['ref'] == main for e in (l['a'], l['b']) if dego[e] == 1}
        best = None
        for a in ends_l:
            for b in ends_m:
                d = math.dist((nodes[a]['x'], nodes[a]['z']), (nodes[b]['x'], nodes[b]['z']))
                if d < 150 and (best is None or d < best[0]):
                    best = (d, a, b)
        if best:
            d, a, b = best
            links.append({'id': len(links), 'a': a, 'b': b, 'kind': 'taxiway', 'ref': main, 'way': None, 'len': R2(d),
                          'pts': [[nodes[a]['x'], nodes[a]['z']], [nodes[b]['x'], nodes[b]['z']]], 'dir': 'both',
                          'use': 'all', 'status': 'open', 'gap': True, 'src': 'inf',
                          'note': 'straight join of %s and %s across the part outside the detailed extent (clipped)' % (lead, main)})
    for lead, main in (('BN', 'N'), ('BS', 'S')):
        lead_nodes = {e for l in links if l['ref'] == lead for e in (l['a'], l['b'])}
        ml = [l for l in links if l['ref'] == main]
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
                # not linked to the lead taxiway by name inside the extent: orient towards TWY D (the west side)
                l['a'], l['b'] = l['b'], l['a']; l['pts'] = l['pts'][::-1]
            l['dir'] = 'ab'; l['use'] = 'arrival'
            l['dir_src'] = ('AIP (mirror) ROUTE-NORTH / SOUTH one-way (direction: along %s away from %s)' % (main, lead)
                            if l['a'] in order else 'AIP (mirror) ROUTE-NORTH / SOUTH one-way (direction inf: towards TWY D; '
                            'joined to %s by an unnamed OSM link)' % lead)

    # ------------------------------------------------------------------ runway entries / exits / crossings, inferred holds
    adj = defaultdict(list)
    for l in links:
        adj[l['a']].append(l); adj[l['b']].append(l)
    runways = []
    new_holds = []
    for rid, r in rwy_info.items():
        cl = r['centreline']['pts']; ax = (cl[1][0] - cl[0][0], cl[1][1] - cl[0][1]); La = math.hypot(*ax)
        ux, uz = ax[0] / La, ax[1] / La          # southward unit vector
        line = LineString(cl)
        entries, exits = [], []
        for e in sorted(rwy_nodes[rid], key=lambda e: (nodes[e]['x'] - cl[0][0]) * ux + (nodes[e]['z'] - cl[0][1]) * uz):
            s_along = R2((nodes[e]['x'] - cl[0][0]) * ux + (nodes[e]['z'] - cl[0][1]) * uz)
            for l in adj[e]:
                if l['kind'] == 'runway':
                    continue
                # direction of the taxiway leaving the runway node
                pts = l['pts'] if l['a'] == e else l['pts'][::-1]
                far = pts[min(len(pts) - 1, 3)]
                vx, vz = far[0] - nodes[e]['x'], far[1] - nodes[e]['z']; vl = math.hypot(vx, vz) or 1
                cosang = (vx * ux + vz * uz) / vl          # + = leaves towards the south
                side = 'east' if (vx * -uz + vz * ux) < 0 else 'west'
                ang = math.degrees(math.acos(max(-1, min(1, abs(cosang)))))
                rec = {'node': e, 'link': l['id'], 'ref': l['ref'], 's_m': s_along, 'side': side,
                       'angle_deg': R2(ang)}
                if ang < 50:
                    rec['rapid_exit_for'] = rid.split('/')[0] if cosang > 0 else rid.split('/')[1]   # landing direction
                exits.append(rec)
        crossing_refs = sorted({x['ref'] for x in exits if x['ref'] and re.match(r'^H\d$', x['ref'])})
        runways.append({'id': rid, 'ends': [{'end': rid.split('/')[0], 'xz': cl[0]}, {'end': rid.split('/')[1], 'xz': cl[1]}],
                        'connections': exits, 'crossing_taxiways_osm': crossing_refs})
    # inferred runway-holding positions: along every taxiway polyline (OSM way) with a vertex on a runway node, walk
    # away from the runway in both directions to HOLD_DIST from that runway's centreline (unless an OSM hold is within
    # 30 m of that point)
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
                                                  'rule': 'runway-holding position %d m from the centreline (inf)' % HOLD_DIST})
                            break
                        if d1 < d0 - 0.5:     # coming back towards the runway: stop
                            break
                        prev = q; j += step
    # dedupe inferred holds (same taxiway / side / runway within 15 m)
    hold_inf = []
    for h in new_holds:
        if all(math.dist((h['x'], h['z']), (g['x'], g['z'])) > 15 for g in hold_inf):
            hold_inf.append(h)
    for h in hold_inf:
        h['node'] = None
    # ------------------------------------------------------------------ push-back links
    for s in ST['stands']:
        p = s.get('push')
        if not p:
            continue
        a = node_id.get(key(*s['nose'])); b = node_id.get(key(*p['junction']))
        if a is None or b is None:
            continue
        links.append({'id': len(links), 'a': a, 'b': b, 'kind': 'push', 'ref': s['name'], 'way': None,
                      'len': R2(math.dist(s['nose'], p['junction'])), 'pts': [s['nose'], p['junction']], 'dir': 'ab',
                      'use': 'departure', 'status': 'open', 'tail_headings': p.get('tail_headings'), 'src': 'inf'})
    # ------------------------------------------------------------------ connectivity checks
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

    def reach(src, mode, reverse=False):
        """BFS over directed links usable in mode ('arrival' | 'departure'); lead-ins: arrival a->b towards the stand
        is allowed both ways geometrically, departures leave stands only by the push link"""
        out = defaultdict(list)
        for l in links:
            if l['status'] != 'open':
                continue
            if l['use'] not in ('all', mode):
                continue
            if l['kind'] == 'push' and mode != 'departure':
                continue
            pairs = [(l['a'], l['b'])] if l['dir'] == 'ab' else [(l['a'], l['b']), (l['b'], l['a'])]
            for a, b in pairs:
                if reverse:
                    a, b = b, a
                out[a].append(b)
        seen = set(src); q = deque(src)
        while q:
            v = q.popleft()
            for w in out[v]:
                if w not in seen:
                    seen.add(w); q.append(w)
        return seen
    rwy_all = {e for rid in rwy_nodes for e in rwy_nodes[rid]}
    stand_nodes = {s['name']: node_id.get(key(*s['nose'])) for s in ST['stands']}
    per_rwy = {}
    bad = defaultdict(list)
    for rid in rwy_nodes:
        rn = rwy_nodes[rid]
        dep_reach = reach(list(rn), 'departure', reverse=True)    # nodes that can reach this runway (departure)
        arr_reach = reach(list(rn), 'arrival')                      # nodes reachable from this runway (arrival)
        per_rwy[rid] = (dep_reach, arr_reach)
        for nm, sn in stand_nodes.items():
            if sn is None:
                bad[nm].append('no node'); continue
            # departures: the stand must reach a non-runway taxiway node next to the runway, then the runway
            if sn not in dep_reach:
                bad[nm].append('cannot depart to ' + rid)
            if sn not in arr_reach:
                bad[nm].append('cannot arrive from ' + rid)
    checks['components'] = {'n': ncomp, 'sizes_top': sorted(sizes, reverse=True)[:8],
                            'nodes_outside_main': sum(1 for i in range(N) if comp[i] not in (-1, main_c))}
    off_main = Counter()
    for l in links:
        if comp[l['a']] != main_c:
            off_main[(l['kind'], l['ref'], l['status'])] += 1
    checks['links_outside_main_component'] = [list(k) + [v] for k, v in off_main.most_common(20)]
    checks['stands_failing_reachability'] = dict(bad)
    checks['stands_ok_both_runways_arr_dep'] = sum(1 for nm in stand_nodes if nm not in bad)
    checks['stands_total'] = len(stand_nodes)
    checks['inferred_holds'] = len(hold_inf)
    checks['osm_holds'] = len(A['holds'])
    checks['one_way_links'] = {'%s:%s' % k: v for k, v in sorted(Counter((l['use'], l['ref']) for l in links
                                                                      if l['dir'] == 'ab' and l['kind'] != 'push').items(), key=str)}
    if aip_txt:
        norm = lambda t: re.sub(r'\s+', '', t)  # noqa: E731
        nt = norm(aip_txt)
        checks['aip_probes'] = {k: norm(v['probe']) in nt for k, v in AIP_RULES.items()}
    # ------------------------------------------------------------------ sfo3d-compatible fields
    ways = [{'ref': p['ref'], 'kind': p['kind'], 'osm': p['osm']} for p in polys]
    edges = []
    for wi, p in enumerate(polys):
        if p['status'] != 'open':
            continue
        for u, v in zip(p['pts'][:-1], p['pts'][1:]):
            if math.dist(u, v) > 0.05:
                edges.append([R2(u[0]), R2(u[1]), R2(v[0]), R2(v[1]), wi])
    leadins = [{'ref': s['name'], 'pts': s['leadin'], 'stop': s['nose'], 'hdg': s['hdg']} for s in ST['stands'] if s['leadin']]
    out = {
        'what': 'ZSSS taxi graph for SHA Live 3D (task A2): OSM taxiway / taxilane / lead-in centrelines, OSM runway '
                'centrelines to the A1 placed ends, holds, push-back links, AIP (mirror) use rules',
        'frame': F.FRAME_ID, 'generator': 'tools/airport/build_taxigraph.py',
        'source': 'data/sha_airport.json (OSM pinned 2026-11-14 + A1 re-fit), OSM lead-in ways, data/sha_stands.json',
        'licence': 'ODbL 1.0', 'attribution': '(c) OpenStreetMap contributors',
        'halfWidth': 11.5,
        'halfWidth_note': 'half of the 23 m main-taxiway width (AIP (mirror) AD 2.8) - a "paved" test for gear points',
        'rules': {k: {'text': v['text'], 'src': 'AIP (mirror)', **({'refs': v['refs']} if 'refs' in v else {})}
                  for k, v in AIP_RULES.items()},
        'rules_note': 'use = arrival / departure from AD 2.20 3.1.5 and 2.3.3; the geometric direction of one-way links '
                      'is the OSM oneway tag where present, else inferred (dir_src). Taxiway span limits on the aprons '
                      '(AD 2.20 3.1.1 chart) are not transcribed. Runway-holding positions: OSM where mapped (src obs), '
                      'else inferred at %d m (hold_inf).' % HOLD_DIST,
        'nodes': nodes, 'links': links, 'runways': runways, 'hold_inf': hold_inf,
        'ways': ways, 'edges': edges, 'aprons': [a['ring'] for a in A['aprons']], 'leadins': leadins,
        'checks_at_build': checks,
        'counts': {'nodes': len(nodes), 'links': len(links), 'by_kind': dict(Counter(l['kind'] for l in links)),
                   'edges': len(edges), 'ways': len(ways), 'hold_inf': len(hold_inf)},
    }
    s = json.dumps(out, separators=(',', ':'))
    open(OUT_JSON, 'w').write(s)
    open(OUT_JS, 'w').write('// generated by tools/airport/build_taxigraph.py from OpenStreetMap (pinned 2026-11-14). Data (c) '
                            'OpenStreetMap contributors, ODbL 1.0; AIP (mirror) rules are short cited facts.\n'
                            'window.SHA_TAXIGRAPH = ' + s + ';\n')
    print(json.dumps(out['counts']))
    print(json.dumps({k: v for k, v in checks.items() if k not in ('one_way_links',)})[:3000])


if __name__ == '__main__':
    main()
