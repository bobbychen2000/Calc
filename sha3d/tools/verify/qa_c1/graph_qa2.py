import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
exec(open('graph_qa.py').read().split("stand_node = ")[0].split("# integrity")[0])
exec("def adj" + open('graph_qa.py').read().split("def adj")[1].split("stand_node = ")[0])
Lb = {l['id']: l for l in L}
# rapid exits: direction/use
rx = Counter(); rx_list = []
for r in T['runways']:
    for c in r['connections']:
        l = Lb[c['link']]
        if c.get('rapid_exit_for'):
            rx[(l['dir'], l['use'])] += 1; rx_list.append((r['id'], c.get('ref'), c['rapid_exit_for'], c['s_m'], l['dir'], l['use'], c['angle_deg']))
print('rapid-exit links (dir, use):', dict(rx))
# take-off entry nodes per departure end
Gd = adj('dep')
ends = {}
for r in T['runways']:
    Lr = math.dist(r['ends'][0]['xz'], r['ends'][1]['xz'])
    for e in r['ends']:
        nodes = set(); refs = []
        for c in r['connections']:
            s = c['s_m']; near = (s < 450) if e['end'] in ('18L', '18R') else (s > Lr - 450 - 9)
            if near:
                l = Lb[c['link']]
                # the link must be traversable towards the runway node in the departure graph
                nodes.add(c['node']); refs.append((c.get('ref'), round(s), l['dir'], l['use'], c.get('angle_deg')))
        ends[e['end']] = (nodes, refs)
        print(e['end'], 'entry connections within 450 m of the take-off end:', refs)
stand_ids = [i for i in N if N[i]['kind'] == 'stand']
def dijkstra(G, src):
    d = {src: 0}; prev = {}; pq = [(0, src)]
    while pq:
        c, u = heapq.heappop(pq)
        if c > d[u]: continue
        if u != src and N[u]['kind'] == 'stand': continue
        for v, w, lid in G[u]:
            if c + w < d.get(v, 1e18):
                d[v] = c + w; prev[v] = (u, lid); heapq.heappush(pq, (c + w, v))
    return d, prev
def path(prev, t):
    out = []
    while t in prev: u, lid = prev[t]; out.append(lid); t = u
    return out[::-1]
def turns(lids, start):
    # max heading change between consecutive link directions along the path (forward taxi only; skip the push link)
    pts = []
    cur = start
    for lid in lids:
        l = Lb[lid]; p = l['pts'] if l['a'] == cur else l['pts'][::-1]; cur = l['b'] if l['a'] == cur else l['a']
        if l['kind'] == 'push': pts = [p[-1]]; continue
        pts += p[1:] if pts else p
    mx = 0
    for i in range(1, len(pts) - 1):
        a = np.subtract(pts[i], pts[i - 1]); b = np.subtract(pts[i + 1], pts[i])
        if np.linalg.norm(a) < 1 or np.linalg.norm(b) < 1: continue
        ang = math.degrees(math.acos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1)))
        mx = max(mx, ang)
    return mx
fail = Counter(); sharp = Counter(); ex = []; via = Counter()
for sid in stand_ids:
    d, prev = dijkstra(Gd, sid)
    for e, (nodes, refs) in ends.items():
        reach = [n for n in nodes if n in d]
        if not reach: fail[e] += 1; continue
        t = min(reach, key=lambda n: d[n]); p = path(prev, t)
        mx = turns(p, sid)
        if mx > 100: sharp[e] += 1; ex.append((N[sid]['ref'], e, round(mx), round(d[t])))
        via[(e, Lb[p[-1]].get('ref'))] += 1
print('stands that cannot reach a take-off-end entry (<=450 m) in the departure graph:', dict(fail))
print('shortest departure routes with a heading change > 100 deg (U-turn) somewhere:', dict(sharp), 'examples', ex[:8])
print('last link used to enter, by end:', dict(via))
# arrivals: from each rapid exit node to stands
Ga = adj('arr')
fa = Counter(); sharpa = Counter(); exa = []
for (rid, ref, land, s, dr, use, ang) in rx_list:
    pass
rx_nodes = {}
for r in T['runways']:
    for c in r['connections']:
        if c.get('rapid_exit_for'): rx_nodes.setdefault(c['rapid_exit_for'], set()).add(c['node'])
for land, nodes in rx_nodes.items():
    for n0 in nodes:
        d, prev = dijkstra(Ga, n0)
        miss = [N[s]['ref'] for s in stand_ids if s not in d]
        if miss: fa[(land, n0)] = len(miss)
        for s in stand_ids:
            if s in d:
                mx = turns(path(prev, s), n0)
                if mx > 100: sharpa[land] += 1
print('rapid-exit nodes from which some stands are unreachable (arrival graph):', dict(fa))
print('arrival shortest routes with > 100 deg heading change:', dict(sharpa))
