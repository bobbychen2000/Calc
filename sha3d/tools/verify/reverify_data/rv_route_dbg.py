"""debug helpers for rv_route (counts / ids of graph links only; no AIP or sensitive data)"""
import sys, os, math, json
sys.argv = ['x', '/home/user/Calc/sha3d/data/sha_taxigraph.json', '/home/user/Calc/sha3d/data/sha_airport.json', '/home/user/Calc/sha3d/data/sha_stands.json']
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_route.py')).read().split('# --- 1. the committed turn table')[0]
exec(src)
table = {(a, b) for v, ps in T['turns'].items() for a, b in ps}
tbl_node = {(a, b): int(v) for v, ps in T['turns'].items() for a, b in ps}
mine = set()
for v, ls in adj.items():
    for li in ls:
        for lo in ls:
            if my_allowed(li, lo, v, 100.0): mine.add((li['id'], lo['id']))
for p in sorted({p for p in table if Lb[p[0]]['use'] != 'runway' and Lb[p[1]]['use'] != 'runway'} - mine):
    v = tbl_node[p]; li, lo = Lb[p[0]], Lb[p[1]]
    print('table-only', p, 'node', v, N[v]['kind'], li['ref'], li['kind'], li['use'], '->', lo['ref'], lo['kind'], lo['use'], 'turn15 %.1f' % turn_deg(li, lo, v, 15), 'rwy_of', rwy_of(v) if N[v]['kind'] in ('rwy','rwy_end') else '')
# sharp first/last segments: links whose first or last segment deviates > 90 deg from the 15 m chord
bad = []
for l in L:
    for fs in (True, False):
        P = l['pts'] if fs else l['pts'][::-1]
        if len(P) < 3: continue
        d1 = dir_at(P, 0.01, True); d15 = dir_at(P, 15.0, True)
        a_ = ang(d1, d15)
        if a_ > 60: bad.append((l['id'], l['kind'], l['ref'], round(a_, 1), round(math.dist(P[0], P[1]), 2), 'start' if fs else 'end'))
print('links with a first/last segment > 60 deg off the 15 m chord:', len(bad))
for b in bad[:30]: print('  ', b)
