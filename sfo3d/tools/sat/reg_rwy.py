"""Airfield screenshot registration with the scale fixed from the map's scale bar and runway outlines only
(runway polygons agree with the FAA runway end coordinates); rotation searched around the compass value."""
import sys, json
sys.path.insert(0, '.')
from register import *
from manual import save
n, th0, s0 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
best = None
for th in np.arange(th0 - 1.5, th0 + 1.51, 0.25):
    r = coarse2(n, th, s0, 2250, s_span=0.0, s_step=0.01, kinds=('runways',), bbox=tuple(D['bounds']), k=1, beta=0.2)
    c = (r[0][0], r[0][1], th, r[0][2], r[0][3], r[0][4])
    if best is None or c[0] > best[0]: best = c
sc, sc2, th, s, tx, ty = best
print(n, 'coarse', round(sc), 'second', round(sc2), 'th', th)
# refine translation + rotation with scale fixed
img, E, v = image_edges(n, 2250)
DT = ndi.distance_transform_edt(~E).astype(np.float32)
P = template_points(0.5, ('runways',)); H, W = E.shape
def cost(p, trunc):
    Q = Sim(s0, p[2], p[0], p[1]).fwd(P)
    k = (Q[:, 0] >= 0) & (Q[:, 1] >= 0) & (Q[:, 0] < W - 1) & (Q[:, 1] < H - 1)
    Qi = Q[k].astype(int); k2 = v[Qi[:, 1], Qi[:, 0]]
    if k2.sum() < 200: return 1e3
    d = ndi.map_coordinates(DT, [Q[k][k2, 1], Q[k][k2, 0]], order=1)
    return float(np.mean(np.minimum(d, trunc) ** 2)) / trunc ** 2
p = np.array([tx, ty, th])
for trunc in (10, 5, 3):
    r = minimize(cost, p, args=(trunc,), method='Nelder-Mead', options={'xatol': 1e-3, 'fatol': 1e-6, 'maxiter': 3000, 'initial_simplex': np.array([p, p + [trunc * 2, 0, 0], p + [0, trunc * 2, 0], p + [0, 0, 0.3]])})
    p = r.x
sim = Sim(s0, p[2], p[0], p[1])
save(n, sim, r.fun, f'runways only, scale fixed from scale bar {s0}')
print('RESULT', n, 's', s0, 'th', round(p[2], 3), 'cost', round(r.fun, 4))
