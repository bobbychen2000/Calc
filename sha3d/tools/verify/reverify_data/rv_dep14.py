"""Why 14 stands cannot depart: test relaxations one at a time (my rule, theta 100). Counts / stand names only."""
import sys, os, math, json
sys.argv = ['x', '/home/user/Calc/sha3d/data/sha_taxigraph.json', '/home/user/Calc/sha3d/data/sha_airport.json', '/home/user/Calc/sha3d/data/sha_stands.json']
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_route.py')).read().split('# --- 1. the committed turn table')[0])
FAIL = '218 219 225 226 227 238A 239 240 240A 271 272 278 279 280'.split()
ST_by = {s['name']: s for s in ST['stands']}
def dep_count(names, theta=100.0):
    ok = {}
    for nm in names:
        pl = push_of[nm]; n_ok = 0
        for end in ends:
            g = dep_goals(end, theta)
            if route([(pl, pl['b'])], lambda lid, v: (lid, v) in g, 'departure', nm, theta): n_ok += 1
        ok[nm] = n_ok
    return ok
for nm in FAIL:
    pl = push_of[nm]; b = pl['b']
    outs = [(lo['id'], lo['kind'], lo['ref'], lo['use'], lo['dir'], lo.get('dir_src'), round(lo['len'], 1)) for lo in adj[b] if lo is not pl]
    print(nm, 'push %.0f m capped=%s ends at node %d (%s); links there:' % (pl['len'], pl.get('capped'), b, N[b]['kind']), outs)
# relaxation 1: apron-lane (kind taxilane) one-way ignored
saved = {}
for l in L:
    if l['kind'] == 'taxilane' and l['dir'] == 'ab':
        saved[l['id']] = l['dir']; l['dir'] = 'both'
print('relax taxilane one-way (%d links):' % len(saved), dep_count(FAIL))
for i, d in saved.items(): Lb[i]['dir'] = d
# relaxation 2: theta 120
print('theta 120:', dep_count(FAIL, 120.0))
