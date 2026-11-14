"""Re-verify (data) H2/M5/M6: independent edge-based router on sha_taxigraph.json.

It does NOT use the committed `turns` table for routing. Transitions come from my own rule computed on the link
geometry:
  * one-way (dir 'ab' = a->b only), status open;
  * use: departure routes may use 'all'/'departure', arrival routes 'all'/'arrival'; 'runway' links never;
    'stand' links only for the own stand (first leg of an arrival end / last leg); push links only as first leg;
  * turn angle at the node <= THETA, measured as the chord over the last/first LOOK m of each link;
  * a pass through a runway node from a non-runway link to a non-runway link is a crossing: allowed only when both
    links carry a crossing ref of that runway (AIP (mirror) 2.2.5 as cited in rules.facts.crossings);
  * at the end of a push the tail is turned onto the lane (either direction), as the builder documents.
Departure goal: a link entering a runway node of the take-off runway within ENTRY m of the take-off end (or the
intersection taxiway H2/H6 for 18R/36L) with a line-up turn <= THETA. Arrival start: a link leaving a runway node
with a turn from the landing heading <= THETA, not H3/H4/H5, and a rapid exit only for its for_landing.
Then: the committed turns table is compared with my rule; route metrics are measured on my routes and on routes found
with the committed table. Counts only. usage: python3 -I rv_route.py TAXIGRAPH_JSON AIRPORT_JSON STANDS_JSON
"""
import json, math, sys, heapq
from collections import defaultdict, Counter
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

T = json.load(open(sys.argv[1])); A = json.load(open(sys.argv[2])); ST = json.load(open(sys.argv[3]))
N = {n['id']: n for n in T['nodes']}; L = T['links']; Lb = {l['id']: l for l in L}
adj = defaultdict(list)
for l in L:
    adj[l['a']].append(l); adj[l['b']].append(l)
CROSS = {'18R/36L': {'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'H7'}, '18L/36R': {'H1', 'H4', 'H7'}}
NO_VAC = {'H3', 'H4', 'H5'}
INTER = {'18R': 'H2', '36L': 'H6'}


def dir_at(pts, look, from_start):
    P = pts if from_start else pts[::-1]
    acc = 0.0; q = P[-1]
    for a, b in zip(P[:-1], P[1:]):
        d = math.dist(a, b)
        if acc + d >= look:
            t = (look - acc) / d; q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])); break
        acc += d
    vx, vz = q[0] - P[0][0], q[1] - P[0][1]; n = math.hypot(vx, vz) or 1.0
    return (vx / n, vz / n) if from_start else (-vx / n, -vz / n)


def ang(u, v):
    return math.degrees(math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1]))))


def enters(l, v): return l['b'] == v or (l['dir'] == 'both' and l['a'] == v)
def leaves(l, v): return l['a'] == v or (l['dir'] == 'both' and l['b'] == v)
def pts_into(l, v): return l['pts'] if l['b'] == v else l['pts'][::-1]
def pts_from(l, v): return l['pts'] if l['a'] == v else l['pts'][::-1]
def other(l, v): return l['b'] if l['a'] == v else l['a']


def turn_deg(li, lo, v, look):
    return ang(dir_at(pts_into(li, v), look, False), dir_at(pts_from(lo, v), look, True))


# runway ids per runway node: nearest runway centreline
rwy_cl = {r['id']: LineString(r['centreline']['pts']) for r in A['runways']}
rwy_poly = {r['id']: Polygon(r['outline']['ring']) for r in A['runways']}
def rwy_of(v):
    p = Point(N[v]['x'], N[v]['z']); return min(rwy_cl, key=lambda k: rwy_cl[k].distance(p))
rnodes = defaultdict(set)
for n in T['nodes']:
    if n['kind'] in ('rwy', 'rwy_end'):
        rnodes[rwy_of(n['id'])].add(n['id'])


def my_allowed(li, lo, v, theta, look=15.0):
    if lo is li or not enters(li, v) or not leaves(lo, v):
        return False
    if lo['kind'] == 'push' or lo['use'] == 'runway' or li['use'] == 'runway' or lo['status'] != 'open':
        return False
    if li['kind'] == 'push':
        return not lo.get('stand')          # tail turned onto a lane; never into a stand lead-in
    if N[v]['kind'] in ('rwy', 'rwy_end'):
        rid = rwy_of(v)
        if not (li['ref'] in CROSS[rid] and lo['ref'] in CROSS[rid]):
            return False
    return turn_deg(li, lo, v, look) <= theta


def route(starts, goal, mode, stand, theta, table=None):
    dist = {}; prev = {}; h = []
    for l, v in starts:
        dist[(l['id'], v)] = l['len']; heapq.heappush(h, (l['len'], l['id'], v))
    while h:
        d, lid, v = heapq.heappop(h)
        if d > dist.get((lid, v), 1e18):
            continue
        if goal(lid, v):
            p = [(lid, v)]; st = (lid, v)
            while st in prev:
                st = prev[st]; p.append(st)
            return d, p[::-1]
        li = Lb[lid]
        for lo in adj[v]:
            if table is not None:
                if (lid, lo['id']) not in table or lo['use'] == 'runway' or lo['status'] != 'open':
                    continue
            elif not my_allowed(li, lo, v, theta):
                continue
            if lo['use'] not in ('all', mode, 'stand'):
                continue
            if lo.get('stand') and lo['stand'] != stand:
                continue
            w = other(lo, v); nd = d + lo['len']
            if nd < dist.get((lo['id'], w), 1e18):
                dist[(lo['id'], w)] = nd; prev[(lo['id'], w)] = (lid, v); heapq.heappush(h, (nd, lo['id'], w))
    return None


ends = {}
for r in T['runways']:
    (e0, e1) = r['ends']
    p0, p1 = e0['xz'], e1['xz']; ax = (p1[0] - p0[0], p1[1] - p0[1]); n = math.hypot(*ax)
    ends[e0['end']] = (p0, (ax[0] / n, ax[1] / n), r['id'])
    ends[e1['end']] = (p1, (-ax[0] / n, -ax[1] / n), r['id'])
stand_node = {}
for s in ST['stands']:
    k = (round(s['nose'][0], 2), round(s['nose'][1], 2))
    cand = [n['id'] for n in T['nodes'] if n['kind'] == 'stand' and (round(n['x'], 2), round(n['z'], 2)) == k]
    stand_node[s['name']] = cand[0] if cand else None
push_of = {l['stand']: l for l in L if l['kind'] == 'push'}


def dep_goals(end, theta):
    pt, hd, rid = ends[end]; g = set()
    for e in rnodes[rid]:
        near = math.dist((N[e]['x'], N[e]['z']), pt) <= 450.0
        for l in adj[e]:
            if l['kind'] == 'runway' or not enters(l, e):
                continue
            if ang(dir_at(pts_into(l, e), 15.0, False), hd) > theta:
                continue
            if near or (INTER.get(end) and l['ref'] == INTER[end]):
                g.add((l['id'], e))
    return g


def arr_starts(end, theta):
    pt, hd, rid = ends[end]; s = []
    for e in rnodes[rid]:
        for l in adj[e]:
            if l['kind'] == 'runway' or not leaves(l, e) or l['ref'] in NO_VAC:
                continue
            if l.get('for_landing') and end not in l['for_landing']:
                continue
            if ang(hd, dir_at(pts_from(l, e), 15.0, True)) > theta:
                continue
            s.append((l, other(l, e)))
    return s


rw_union = unary_union(list(rwy_poly.values()))


def metrics(path, mode):
    """max turn (15 m chord and first/last segment), runway-link use, other-stand lead-ins, length inside the runway
    outlines excluding the first (arrival) / last (departure) link, crossings off the AIP list"""
    mx15 = 0.0; mxseg = 0.0; rw = 0; other_li = 0; badx = 0
    ids = [lid for lid, _ in path]
    for (lid, v), (lid2, v2) in zip(path[:-1], path[1:]):
        li, lo = Lb[lid], Lb[lid2]
        if li['kind'] == 'push':
            continue
        mx15 = max(mx15, turn_deg(li, lo, v, 15.0)); mxseg = max(mxseg, turn_deg(li, lo, v, 0.01))
        if N[v]['kind'] in ('rwy', 'rwy_end') and li['kind'] != 'runway' and lo['kind'] != 'runway':
            rid = rwy_of(v)
            if not (li['ref'] in CROSS[rid] and lo['ref'] in CROSS[rid]):
                badx += 1
    for lid in ids:
        if Lb[lid]['use'] == 'runway':
            rw += 1
    inner = ids[1:] if mode == 'arrival' else ids[:-1]
    inside = 0.0
    for lid in inner:
        g = LineString(Lb[lid]['pts']).intersection(rw_union); inside = max(inside, g.length)
    return mx15, mxseg, rw, badx, inside


def run(theta, table=None, tag=''):
    dep_ok = Counter(); arr_ok = Counter(); fails = defaultdict(list); M = {'dep': [], 'arr': []}
    for end in ends:
        goals = dep_goals(end, theta)
        for nm, sn in stand_node.items():
            pl = push_of.get(nm)
            r = route([(pl, pl['b'])], lambda lid, v: (lid, v) in goals, 'departure', nm, theta, table) if pl else None
            if r:
                dep_ok[end] += 1; M['dep'].append((nm, end, r[0]) + metrics(r[1], 'departure'))
            else:
                fails[nm].append('dep ' + end)
        st = arr_starts(end, theta)
        for nm, sn in stand_node.items():
            r = route(st, lambda lid, v, sn=sn: v == sn, 'arrival', nm, theta, table)
            if r:
                arr_ok[end] += 1; M['arr'].append((nm, end, r[0]) + metrics(r[1], 'arrival'))
            else:
                fails[nm].append('arr ' + end)
    print('== %s theta=%g' % (tag, theta))
    print('  departures ok per take-off end', dict(dep_ok))
    print('  arrivals ok per landing end', dict(arr_ok))
    nf = {k: v for k, v in fails.items()}
    print('  stands with any failure: %d' % len(nf))
    by = Counter(tuple(v) for v in nf.values())
    for k, c in by.most_common():
        print('    %d stands: %s -> %s' % (c, ', '.join(k), ' '.join(sorted(n for n in nf if tuple(nf[n]) == k))))
    # per-runway reachability (at least one direction / both directions)
    rw_dep = Counter()
    for nm in stand_node:
        f = set(nf.get(nm, []))
        for rid, (a, b) in (('18L/36R', ('18L', '36R')), ('18R/36L', ('18R', '36L'))):
            ok = [x for x in (a, b) if 'dep ' + x not in f]
            rw_dep[(rid, len(ok))] += 1
    print('  departure ends reachable per runway (runway, n of 2 directions): stands', dict(rw_dep))
    for k in ('dep', 'arr'):
        m = M[k]
        if not m:
            continue
        print('  %s routes %d: max turn15 %.1f, max turn seg %.1f; turn15>90: %d, >100: %d; seg>90: %d, >120: %d; '
              'runway links used: %d; bad crossings: %d; max contiguous runway-outline length off first/last link: %.0f m'
              % (k, len(m), max(x[3] for x in m), max(x[4] for x in m), sum(x[3] > 90 for x in m), sum(x[3] > 100 for x in m),
                 sum(x[4] > 90 for x in m), sum(x[4] > 120 for x in m), sum(x[5] > 0 for x in m), sum(x[6] > 0 for x in m),
                 max(x[7] for x in m)))
        lens = sorted(x[2] for x in m); print('    route length median %.0f m, max %.0f m' % (lens[len(lens) // 2], lens[-1]))
    return nf, M


# --- 1. the committed turn table against my rule
table = {(a, b) for v, ps in T['turns'].items() for a, b in ps}
tbl_node = {(a, b): int(v) for v, ps in T['turns'].items() for a, b in ps}
c = Counter()
for (a, b), v in tbl_node.items():
    li, lo = Lb[a], Lb[b]
    if not enters(li, v): c['in-link cannot enter node (one-way/topology)'] += 1
    if not leaves(lo, v): c['out-link cannot leave node (one-way/topology)'] += 1
    if lo['kind'] == 'push': c['into a push link'] += 1
    if li['use'] == 'runway' or lo['use'] == 'runway': c['involves a runway link (allowed only for backtrack)'] += 1
    if li['kind'] == 'push':
        if lo.get('stand'): c['push end into a stand lead-in'] += 1
        continue
    t15 = turn_deg(li, lo, v, 15.0)
    if t15 > 100.0001: c['turn15 > 100'] += 1
    elif t15 > 90: c['turn15 in (90,100]'] += 1
    if N[v]['kind'] in ('rwy', 'rwy_end') and li['kind'] != 'runway' and lo['kind'] != 'runway':
        rid = rwy_of(v)
        if not (li['ref'] in CROSS[rid] and lo['ref'] in CROSS[rid]): c['crossing off the AIP list'] += 1
        else: c['crossing on the AIP list'] += 1
print('turn table pairs: %d; checks:' % len(table), dict(c))
mine = set()
for v, ls in adj.items():
    for li in ls:
        for lo in ls:
            if my_allowed(li, lo, v, 100.0):
                mine.add((li['id'], lo['id']))
tbl_taxi = {p for p in table if Lb[p[0]]['use'] != 'runway' and Lb[p[1]]['use'] != 'runway'}
print('my rule (theta 100) pairs %d; in mine not in table %d; in table (non-runway) not in mine %d'
      % (len(mine), len(mine - tbl_taxi), len(tbl_taxi - mine)))
diff = Counter()
for p in tbl_taxi - mine:
    li, lo = Lb[p[0]], Lb[p[1]]
    diff[(li['kind'], lo['kind'], 'push-end' if li['kind'] == 'push' else '')] += 1
print('  table-only pairs by kind:', dict(diff))
diff2 = Counter((Lb[p[0]]['kind'], Lb[p[1]]['kind']) for p in mine - tbl_taxi)
print('  mine-only pairs by kind:', dict(diff2))

# --- 2. reachability with my rule, theta 90 (strict AIP) and 100 (builder tolerance), and with the committed table
for th in (90.0, 100.0):
    run(th, None, 'my rule')
nf_t, M_t = run(100.0, table, 'committed turn table')
json.dump({'fails_table': nf_t}, open('rv_route_out.json', 'w'), indent=1)
