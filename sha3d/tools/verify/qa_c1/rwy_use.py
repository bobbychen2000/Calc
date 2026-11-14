import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
src = open('graph_qa3.py').read()
exec(src.split("cnt = Counter()")[0])
rl = [l for l in L if l['kind'] == 'runway']
print('runway links (dir, use, status):', Counter((l['dir'], l['use'], l['status']) for l in rl))
GdR = adj('dep', allow_runway=True)
GaR = adj('arr', allow_runway=True)
use_dep = 0; use_arr = 0; tot = 0; ex = []
for sid in stand_ids:
    d, prev = dijkstra(GdR, sid)
    for e, (nodes, refs) in ends.items():
        reach = [n for n in nodes if n in d]; t = min(reach, key=lambda n: d[n]); p = path(prev, t); tot += 1
        rlen = sum(Lb[x]['len'] for x in p if Lb[x]['kind'] == 'runway')
        if rlen > 0: use_dep += 1; ex.append((N[sid]['ref'], e, round(rlen)))
print('shortest departure routes (runway links allowed) that taxi along a runway: %d of %d' % (use_dep, tot), 'max', max(ex, key=lambda e: e[2]))
rx_nodes = {}
for r in T['runways']:
    for c in r['connections']:
        if c.get('rapid_exit_for'): rx_nodes.setdefault(c['rapid_exit_for'], set()).add(c['node'])
cnt = 0; tot = 0; ex = []
for land, nodes in rx_nodes.items():
    for n0 in nodes:
        d, prev = dijkstra(GaR, n0)
        for s in stand_ids:
            p = path(prev, s); tot += 1
            rlen = sum(Lb[x]['len'] for x in p if Lb[x]['kind'] == 'runway')
            if rlen > 0: cnt += 1; ex.append((land, N[s]['ref'], round(rlen)))
print('arrival routes from rapid exits that taxi along a runway: %d of %d' % (cnt, tot), Counter(e[0] for e in ex), max(ex, key=lambda e: e[2]) if ex else None)
