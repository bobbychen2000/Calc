import sys, json
sys.path.insert(0, '.')
from register import *
from manual import save
n, th0, s0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
best = None
for th in (th0 - 1.0, th0, th0 + 1.0):
    r = coarse2(n, th, s0, 2250, s_span=0.22, s_step=0.02, kinds=('complex', 'ba', 'structures', 'runways', 'taxiways'), bbox=tuple(D['bounds']), k=2)
    c = (r[0][0], r[0][1], th, r[0][2], r[0][3], r[0][4])
    print(n, 'th', th, 'best', [round(float(v), 3) for v in c], flush=True)
    if best is None or c[0] > best[0]: best = c
sc, sc2, th, s, tx, ty = best
sim, cost = refine2(n, Sim(s, th, tx, ty), 2250, kinds=('complex', 'ba', 'structures', 'runways', 'taxiways'), fix_th=False)
save(n, sim, cost, f'coarse2(k=2)+refine2 free th; coarse score {sc:.0f} vs 2nd {sc2:.0f}')
print('RESULT', n, round(sim.s, 4), round(sim.th, 3), round(sim.tx, 1), round(sim.ty, 1), 'cost', round(cost, 4), flush=True)
