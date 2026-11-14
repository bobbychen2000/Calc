import sys, os, math, json, itertools
sys.argv = ['x', '/home/user/Calc/sha3d/data/sha_taxigraph.json', '/home/user/Calc/sha3d/data/sha_airport.json', '/home/user/Calc/sha3d/data/sha_stands.json']
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_route.py')).read().split('# --- 1. the committed turn table')[0])
lanes = [l for l in L if l['kind'] == 'taxilane' and l['dir'] == 'ab']
g = {e: dep_goals(e, 100.0) for e in ends}
for nm in ('227', '238A'):
    pl = push_of[nm]; pe = (N[pl['b']]['x'], N[pl['b']]['z'])
    near = [l for l in lanes if min(math.dist(pe, p) for p in l['pts']) < 400]
    print(nm, 'near one-way lanes', len(near), 'push end', pl['b'])
    # which lanes can it reach at all (forward reachability, my rule)
    found = None
    for a, b in itertools.combinations(near, 2):
        a['dir'] = b['dir'] = 'both'
        if route([(pl, pl['b'])], lambda lid, v: (lid, v) in g['18L'], 'departure', nm, 100.0): found = (a['id'], a['len'], b['id'], b['len']); 
        a['dir'] = b['dir'] = 'ab'
        if found: break
    print('  pair that unblocks 18L:', found)
    # theta 120 route: which turn > 100 does it use?
    r = route([(pl, pl['b'])], lambda lid, v: (lid, v) in g['18L'], 'departure', nm, 120.0)
    big = [(lid, v, round(turn_deg(Lb[lid], Lb[l2], v, 15), 1)) for (lid, v), (l2, v2) in zip(r[1][:-1], r[1][1:]) if Lb[lid]['kind'] != 'push' and turn_deg(Lb[lid], Lb[l2], v, 15) > 100]
    print('  theta-120 route uses turns > 100:', big)
