#!/usr/bin/env python3
"""Contract test of data/hwd_taxigraph.{json,js} (format 'hwd-taxigraph/1', docs/phase2_fork_map.md 2.3), independent of
the builder's own `checks`: it re-derives what it tests from the output and from data/hwd_airport.json. No network.

  python3 tools/live/test_taxigraph.py
"""
import json, math, os, re, sys, unittest
from collections import defaultdict, deque

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
G = json.load(open(os.path.join(ROOT, 'data', 'hwd_taxigraph.json')))
A = json.load(open(os.path.join(ROOT, 'data', 'hwd_airport.json')))
KINDS = {'junction', 'end', 'hold', 'runway', 'runway_edge', 'spot', 'helipad', 'hangar'}


def adjacency(air):
    adj = defaultdict(set)
    for l in G['links']:
        if l.get('air') and not air:
            continue
        adj[l['a']].add(l['b']); adj[l['b']].add(l['a'])
    return adj


def reach(adj, starts):
    seen = set(starts); q = deque(starts)
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v); q.append(v)
    return seen


def end_node(rid, end):
    return next(n['node'] for R in G['runways'] if R['id'] == rid for n in R['nodes']
                if G['nodes'][n['node']].get('end') == end)


class Format(unittest.TestCase):
    def test_header_and_licence(self):
        self.assertEqual(G['v'], 'hwd-taxigraph/1'); self.assertEqual(G['frame'], 'ltp-nad83-2011-hwd')
        self.assertIn('ODbL', G['licence'])
        self.assertTrue(any('OpenStreetMap' in a for a in G['attribution']))
        js = open(os.path.join(ROOT, 'data', 'hwd_taxigraph.js')).read()
        self.assertIn('OpenStreetMap contributors, ODbL', js.split('export const')[0])
        self.assertEqual(json.loads(js.split('export const TAXIGRAPH = ', 1)[1].rstrip().rstrip(';')), G)
        for k in ('ways', 'edges', 'nodes', 'links', 'holds', 'spots', 'helipads', 'runways', 'aprons', 'closed', 'checks',
                  'halfWidth'):
            self.assertIn(k, G)

    def test_nodes_links_edges_consistent(self):
        N = len(G['nodes']); W = len(G['ways'])
        for i, n in enumerate(G['nodes']):
            self.assertEqual(n['id'], f'n{i}'); self.assertIn(n['kind'], KINDS)
        for l in G['links']:
            self.assertTrue(0 <= l['a'] < N and 0 <= l['b'] < N and l['a'] != l['b'] and 0 <= l['way'] < W)
            P = l['pts']; a, b = G['nodes'][l['a']], G['nodes'][l['b']]
            self.assertLess(math.hypot(P[0][0] - a['x'], P[0][1] - a['z']), 0.03)
            self.assertLess(math.hypot(P[-1][0] - b['x'], P[-1][1] - b['z']), 0.03)
            self.assertAlmostEqual(l['len'], LineString(P).length, delta=0.05)
            self.assertEqual(bool(l.get('air')), G['ways'][l['way']]['id'] == 'conn:air')
        air_ways = {i for i, w in enumerate(G['ways']) if w.get('air_only')}
        self.assertTrue(all(0 <= e[4] < W and e[4] not in air_ways for e in G['edges']))
        self.assertTrue(all(math.hypot(e[2] - e[0], e[3] - e[1]) <= 50.01 for e in G['edges']))

    def test_ways(self):
        open_ = [w for w in A['taxiways'] + A['taxilanes'] if w['status'] == 'open']
        closed = [w for w in A['taxiways'] + A['taxilanes'] if w['status'] != 'open']
        got = {w['id'] for w in G['ways'] if w['kind'] in ('taxiway', 'taxilane')}
        self.assertEqual(got, {w['id'] for w in open_})
        self.assertEqual({c['id'] for c in G['closed']}, {w['id'] for w in closed})
        span = {w['ref']: w['max_span_m'] for w in G['ways'] if w.get('max_span_m')}
        self.assertAlmostEqual(span['A1'], 100 * 0.3048, places=2); self.assertAlmostEqual(span['Z1'], 94 * 0.3048, places=2)
        self.assertEqual(sorted(w['ref'] for w in G['ways'] if w['kind'] == 'runway'), ['10L/28R', '10R/28L'])


class Topology(unittest.TestCase):
    def test_one_component_and_runways_joined(self):
        adj = adjacency(air=False)
        ground_nodes = {n for l in G['links'] if not l.get('air') for n in (l['a'], l['b'])}
        self.assertEqual(reach(adj, [next(iter(ground_nodes))]), ground_nodes)
        for rid, ends in (('10R/28L', ('10R', '28L')), ('10L/28R', ('10L', '28R'))):
            for e in ends:
                self.assertIn(end_node(rid, e), ground_nodes)

    def test_every_spot_reachable_from_both_runways(self):
        adj_g, adj_a = adjacency(False), adjacency(True)
        starts = {rid: [n['node'] for R in G['runways'] if R['id'] == rid for n in R['nodes']] for rid in ('10R/28L', '10L/28R')}
        rg = {r: reach(adj_g, s) for r, s in starts.items()}; ra = {r: reach(adj_a, s) for r, s in starts.items()}
        self.assertEqual({s['id'] for s in G['spots']}, {p['id'] for p in A['parking']})
        bad = []
        for s in G['spots']:
            rr = ra if s['kind'] == 'helipad' else rg
            if s['node'] is None or not all(s['node'] in rr[r] for r in rr):
                bad.append(s['id'])
            if s.get('mode') == 'air':
                self.assertEqual(s['kind'], 'helipad', s['id'])      # air links only for helicopters
        self.assertEqual(bad, [])
        for h in G['helipads']:
            self.assertTrue(h['node'] is not None and all(h['node'] in ra[r] for r in ra), h['id'])
        for hg in G['hangars']:
            self.assertTrue(any(sd['node'] is not None and all(sd['node'] in rg[r] for r in rg) for sd in hg['access']), hg['id'])

    def test_holds_on_their_way_near_the_bar(self):
        self.assertEqual(len(G['holds']), len(A['holds']))
        for h in G['holds']:
            n = G['nodes'][h['node']]
            self.assertEqual(n['kind'], 'hold'); self.assertEqual(n['hold'], h['id'])
            self.assertLessEqual(math.hypot(n['x'] - h['x'], n['z'] - h['z']), 15.0)
            self.assertRegex(h['runway'], r'^(10R/28L|10L/28R)$')

    def test_runway_links_inside_outline(self):
        rect = {r['id']: Polygon(r['outline']['ring']).buffer(0.05) for r in A['runways']}
        for l in G['links']:
            if l['runway'] and not l.get('air'):
                mid = LineString(l['pts']).interpolate(0.5, normalized=True)
                self.assertTrue(rect[l['runway']].contains(mid), l)

    def test_connectors_clear_of_buildings_and_fences(self):
        ob = unary_union([Polygon(o['ring']) for o in A['buildings'] + A['hangars'] if len(o.get('ring') or []) >= 3])
        conn = {i for i, w in enumerate(G['ways']) if w['kind'] == 'connector'}
        n_conn = 0
        for l in G['links']:
            if l['way'] in conn:
                n_conn += 1
                g = LineString(l['pts'])
                self.assertLess(g.intersection(ob).length, 0.5, (G['ways'][l['way']]['id'], l['pts']))
        self.assertGreater(n_conn, 200)
        self.assertEqual(G['checks']['taxi_links_crossing_fences'], [])

    def test_no_identity_strings(self):
        """D1: the graph is built from aggregated parking spots; no ICAO hex, registration or callsign may appear."""
        txt = json.dumps(G)
        self.assertIsNone(re.search(r'"(hex|flight|registration|callsign|r)"\s*:', txt))
        self.assertIsNone(re.search(r'\bN[1-9][0-9]{0,4}[A-Z]{0,2}\b', ' '.join(str(s.get('zone', '')) for s in G['spots'])))


if __name__ == '__main__':
    unittest.main(verbosity=2)
