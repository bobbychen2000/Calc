import sys, os, math, json
sys.argv = ['x', '/home/user/Calc/sha3d/data/sha_taxigraph.json', '/home/user/Calc/sha3d/data/sha_airport.json', '/home/user/Calc/sha3d/data/sha_stands.json']
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rv_route.py')).read().split('# --- 1. the committed turn table')[0])
from collections import Counter
FAIL = '218 219 225 226 227 238A 239 240 240A 271 272 278 279 280'.split()
lanes = [l for l in L if l['kind'] == 'taxilane' and l['dir'] == 'ab']
print('one-way taxilanes:', len(lanes), Counter(l.get('dir_src') for l in lanes), Counter(l['src'] for l in lanes))
g18 = dep_goals('18L', 100.0)
res = {}
for nm in FAIL:
    pl = push_of[nm]; pe = (N[pl['b']]['x'], N[pl['b']]['z'])
    near = [l for l in lanes if min(math.dist(pe, p) for p in l['pts']) < 300]
    hits = []
    for l in near:
        l['dir'] = 'both'
        if route([(pl, pl['b'])], lambda lid, v: (lid, v) in g18, 'departure', nm, 100.0): hits.append((l['id'], round(l['len'], 1)))
        l['dir'] = 'ab'
    res[nm] = hits
    print(nm, 'single lane that unblocks 18L:', hits)
