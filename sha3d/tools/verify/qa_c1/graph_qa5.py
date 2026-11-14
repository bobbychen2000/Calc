import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
from shapely.geometry import LineString, Point
src = open('graph_qa3.py').read()
exec(src.split("cnt = Counter()")[0])
own = defaultdict(set)   # stand ref -> lead-in link ids on its primary lead-in
for li in T['leadins']:
    g = LineString(li['pts']).buffer(0.6)
    for l in L:
        if l['kind'] == 'leadin' and all(g.contains(Point(p)) for p in l['pts']):
            own[li['ref']].add(l['id'])
allown = set().union(*own.values())
print('lead-in links on some primary lead-in: %d of %d' % (len(allown), sum(1 for l in L if l['kind'] == 'leadin')))
def adj2(mode, keep):
    G = defaultdict(list)
    for l in L:
        if l['status'] != 'open' or l['kind'] == 'runway': continue
        if l['kind'] == 'leadin' and l['id'] not in keep: continue
        if l['kind'] == 'push':
            if mode == 'dep': G[l['a']].append((l['b'], l['len'], l['id']))
            continue
        if mode == 'dep' and l['use'] not in ('all', 'departure'): continue
        if mode == 'arr' and l['use'] not in ('all', 'arrival'): continue
        G[l['a']].append((l['b'], l['len'], l['id']))
        if l['dir'] == 'both': G[l['b']].append((l['a'], l['len'], l['id']))
    return G
rwy_nodes = defaultdict(set)
for i, n in N.items():
    if n["kind"] in ("rwy", "rwy_end"): rwy_nodes[n["runway"]].add(i)
Gd0 = adj2('dep', set())
fail_dep = []; fail_arr = []
for sid in stand_ids:
    d, prev = dijkstra(Gd0, sid)
    for e, (nodes, refs) in ends.items():
        if not any(n in d for n in nodes): fail_dep.append((N[sid]['ref'], e))
    Ga1 = adj2('arr', own[N[sid]['ref']])
    Gr = defaultdict(list)
    for u, lst in Ga1.items():
        for v, w, lid in lst: Gr[v].append((u, w, lid))
    d, _ = dijkstra(Gr, sid)
    for r, nodes in rwy_nodes.items():
        if not any(x in d for x in nodes): fail_arr.append((N[sid]['ref'], r))
fd = sorted(set(x[0] for x in fail_dep)); fa = sorted(set(x[0] for x in fail_arr))
print('stands that cannot depart without using other lead-in lines after the push: %d' % len(fd), fd)
print('stands that cannot arrive via taxiways/taxilanes + their OWN primary lead-in: %d' % len(fa), fa)
json.dump({'fd': fd, 'fa': fa}, open('leadin_dep.json', 'w'))
