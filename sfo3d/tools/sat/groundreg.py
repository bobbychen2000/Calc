"""Ground-level translation check: chamfer fit of taxiway/runway polygon edges only (no roofs) around the current
registration; reports the translation (world metres) that best aligns ground features."""
import sys, math, json
import numpy as np, cv2
from scipy import ndimage as ndi
from scipy.optimize import minimize
from common import *
from register import image_edges, template_points
from rectify import sim_of
def ground_shift(name, bottom=2200, kinds=('taxiways', 'runways'), search=30, step=1.0):
    img, E, v = image_edges(name, bottom)
    DT = ndi.distance_transform_edt(~E).astype(np.float32)
    S = sim_of(name); P = template_points(0.5, kinds)
    H, W = E.shape
    Q0 = S.fwd(P)
    m = (Q0[:, 0] > 5) & (Q0[:, 1] > 5) & (Q0[:, 0] < W - 5) & (Q0[:, 1] < H - 5)
    P = P[m]
    def cost(dx, dz, trunc=6):
        Q = S.fwd(P + np.array([dx, dz]))
        k = (Q[:, 0] >= 0) & (Q[:, 1] >= 0) & (Q[:, 0] < W - 1) & (Q[:, 1] < H - 1)
        Qi = Q[k].astype(int); k2 = v[Qi[:, 1], Qi[:, 0]]
        if k2.sum() < 100: return 1e3, 0
        d = ndi.map_coordinates(DT, [Q[k][k2, 1], Q[k][k2, 0]], order=1)
        return float(np.mean(np.minimum(d, trunc) ** 2)) / trunc ** 2, int(k2.sum())
    best = (9, 0, 0, 0)
    for dx in np.arange(-search, search + 0.1, step):
        for dz in np.arange(-search, search + 0.1, step):
            c, n = cost(dx, dz)
            if c < best[0]: best = (c, dx, dz, n)
    c0, n0 = cost(0, 0)
    return {'n_pts': best[3], 'cost_at_0': round(c0, 4), 'best_cost': round(best[0], 4), 'shift_world_xz': (best[1], best[2])}
if __name__ == '__main__':
    for n in sys.argv[1:]:
        print(n, ground_shift(n))
