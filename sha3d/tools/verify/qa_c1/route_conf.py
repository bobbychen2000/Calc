import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
src = open('graph_qa3.py').read()
exec(src.split("cnt = Counter()")[0])
exec(open('push_conf.py').read().split("hits = []")[0])
from shapely.geometry import LineString
from shapely.ops import unary_union
routes = []
for sid in stand_ids:
    d, prev = dijkstra(Gd, sid)
    me = N[sid]['ref']; grp = set([me] + by[me]['excl'])
    for e, (nodes, refs) in ends.items():
        reach = [n for n in nodes if n in d]; t = min(reach, key=lambda n: d[n]); p = path(prev, t)
        pts = []
        for lid in p: pts += Lb[lid]['pts']
        ls = LineString(pts)
        inside = 0; who = set()
        for j in tree.query(ls):
            nm = names[j]
            if nm in grp: continue
            x = P[nm].intersection(ls).length
            if x > 5: inside += x; who.add(nm)
        routes.append((round(inside), me, e, sorted(who)[:6], len(who)))
r = np.array([x[0] for x in routes])
print('shortest departure routes running > 5 m through other stands\' reference planforms: %d of %d; > 50 m: %d; max %d m' % ((r > 0).sum(), len(r), (r > 50).sum(), r.max()))
print('stands affected (any end):', len(set(x[1] for x in routes if x[0] > 0)))
for x in sorted(routes, reverse=True)[:8]: print('  ', x)
json.dump(routes, open('route_conf.json', 'w'))
