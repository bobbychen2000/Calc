import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
src = open('graph_qa2.py').read()
exec(src.split("fail = Counter()")[0])
def junction_turns(lids, start):
    """heading change at each node between the end of one link and the start of the next (forward taxi; skip push)."""
    cur = start; prev_dir = None; out = []
    for lid in lids:
        l = Lb[lid]; p = l['pts'] if l['a'] == cur else l['pts'][::-1]; node = cur; cur = l['b'] if l['a'] == cur else l['a']
        if l['kind'] == 'push': prev_dir = None; continue
        d0 = np.subtract(p[1], p[0])
        if prev_dir is not None and np.linalg.norm(d0) > 0.5:
            ang = math.degrees(math.acos(np.clip(np.dot(prev_dir, d0) / np.linalg.norm(prev_dir) / np.linalg.norm(d0), -1, 1)))
            out.append((ang, node, l['kind'], l.get('ref')))
        d1 = np.subtract(p[-1], p[-2]); prev_dir = d1 if np.linalg.norm(d1) > 0.5 else prev_dir
    return out
cnt = Counter(); tot = Counter(); ex = []
for sid in stand_ids:
    d, prev = dijkstra(Gd, sid)
    for e, (nodes, refs) in ends.items():
        reach = [n for n in nodes if n in d]; t = min(reach, key=lambda n: d[n]); p = path(prev, t)
        jt = junction_turns(p, sid); tot['dep'] += 1
        if any(a > 120 for a, *_ in jt): cnt['dep'] += 1; ex.append(('dep', N[sid]['ref'], e, [(round(a), k, r) for a, n, k, r in jt if a > 120][:2]))
Ga = adj('arr')
rx_nodes = {}
for r in T['runways']:
    for c in r['connections']:
        if c.get('rapid_exit_for'): rx_nodes.setdefault(c['rapid_exit_for'], set()).add(c['node'])
for land, nodes in rx_nodes.items():
    for n0 in nodes:
        d, prev = dijkstra(Ga, n0)
        for s in stand_ids:
            jt = junction_turns(path(prev, s), n0); tot['arr'] += 1
            if any(a > 120 for a, *_ in jt): cnt['arr'] += 1; ex.append(('arr', land, N[s]['ref'], [(round(a), k, r) for a, n, k, r in jt if a > 120][:2]))
print('routes with a reversal (> 120 deg) at a graph node:', dict(cnt), 'of', dict(tot))
for e in ex[:6]: print('  ', e)
print('  ', [e for e in ex if e[0] == 'arr'][:6])
json.dump(ex[:400], open('uturns.json', 'w'))
