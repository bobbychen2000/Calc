"""Georeference a Google Maps screenshot (rotation from compass, scale from scale bar) against SFO Museum geometry.
Coarse: FFT correlation of rendered outline edges with an edge-proximity map; fine: chamfer refinement at full res."""
import sys, json, math
from common import *
import numpy as np, cv2
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.optimize import minimize

U = open(SP + 'uniq.txt').read().split()
def path(name): return [u for u in U if name in u][0]

def valid_mask(img, name, bottom):
    H, W = img.shape[:2]
    v = np.ones((H, W), bool)
    v[:330] = False                      # status bar, search box, chips
    v[bottom:] = False                   # bottom sheet / nav bar
    v[330:900, 1090:] = False            # layer + compass buttons
    v[1900:, 1040:] = False              # location + directions buttons
    v[2300:, 700:] = False               # scale bar
    # pins / labels: saturated orange, blue, pink icons and white label text
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = (hsv[..., 1] > 150) & (hsv[..., 2] > 150)
    txt = (img.min(2) > 245)
    bad = ndi.binary_dilation(sat | txt, iterations=6)
    v &= ~bad
    return v

def image_edges(name, bottom):
    img = cv2.imread(path(name))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(gray, (0, 0), 1.6)
    E = cv2.Canny(g, 30, 80) > 0
    v = valid_mask(img, name, bottom)
    E &= v
    return img, E, v

def template_points(step=1.0, kinds=('complex', 'ba', 'structures', 'runways', 'taxiways')):
    P = []
    for k in kinds: P.append(sample_edges(rings_all(k), step))
    return np.concatenate(P)

def render_template(P, sim_small, shape):
    T = np.zeros(shape, np.float32)
    Q = np.round(sim_small.fwd(P)).astype(int)
    m = (Q[:, 0] >= 0) & (Q[:, 1] >= 0) & (Q[:, 0] < shape[1]) & (Q[:, 1] < shape[0])
    T[Q[m, 1], Q[m, 0]] = 1
    return T

def coarse(name, th0, s0, bottom=2200, th_span=2.0, s_span=0.05, k=None, bbox=None):
    img, E, v = image_edges(name, bottom)
    H, W = E.shape
    if k is None: k = max(1, int(round(s0 / 0.8)))
    Hs, Ws = H // k, W // k
    Es = E[:Hs * k, :Ws * k].reshape(Hs, k, Ws, k).any((1, 3))
    vs = v[:Hs * k, :Ws * k].reshape(Hs, k, Ws, k).all((1, 3))
    DT = ndi.distance_transform_edt(~Es)
    Pm = np.exp(-DT ** 2 / (2 * 1.2 ** 2)).astype(np.float32) * vs
    x0, z0, x1, z1 = bbox or D['bounds']
    P = template_points(1.0 * k / s0 * 0.7)
    best = (-1,)
    for th in np.arange(th0 - th_span, th0 + th_span + 1e-6, 0.5):
        for s in s0 * np.arange(1 - s_span, 1 + s_span + 1e-6, 0.01):
            ss = s / k
            # template canvas: world bbox rendered with rotation, offset so all coords positive
            sim = Sim(ss, th, 0, 0)
            C = sim.fwd(np.array([[x0, z0], [x1, z0], [x0, z1], [x1, z1]]))
            off = -C.min(0) + 2
            sim = Sim(ss, th, off[0], off[1])
            shp = (int(C[:, 1].max() - C[:, 1].min()) + 5, int(C[:, 0].max() - C[:, 0].min()) + 5)
            T = render_template(P, sim, shp)
            # correlation: score(t) = sum_p T(p) * Pm(p + t)  -> fftconvolve(Pm, T[::-1, ::-1])
            num = fftconvolve(Pm, T[::-1, ::-1], mode='full')
            den = fftconvolve(vs.astype(np.float32), T[::-1, ::-1], mode='full')
            sc = num / np.maximum(den, 1) * np.minimum(1, den / 300.0)
            i = np.unravel_index(np.argmax(sc), sc.shape)
            if sc[i] > best[0]:
                # full-mode index i corresponds to shift: image pos = template pos + (i - (T.shape - 1))
                ty = i[0] - (T.shape[0] - 1); tx = i[1] - (T.shape[1] - 1)
                best = (float(sc[i]), th, s, (off[0] + tx) * k, (off[1] + ty) * k, float(den[i]))
    return best

def refine(name, sim0, bottom=2200, iters=3):
    img, E, v = image_edges(name, bottom)
    DT = ndi.distance_transform_edt(~E).astype(np.float32)
    P = template_points(0.5)
    H, W = E.shape
    def cost(p, trunc):
        s, th, tx, ty = p
        Q = Sim(s, th, tx, ty).fwd(P)
        m = (Q[:, 0] >= 0) & (Q[:, 1] >= 0) & (Q[:, 0] < W - 1) & (Q[:, 1] < H - 1)
        Qi = Q[m].astype(int); m2 = v[Qi[:, 1], Qi[:, 0]]
        if m2.sum() < 200: return 1e3
        d = ndi.map_coordinates(DT, [Q[m][m2, 1], Q[m][m2, 0]], order=1)
        return float(np.mean(np.minimum(d, trunc) ** 2))
    p = np.array([sim0.s, sim0.th, sim0.tx, sim0.ty])
    for trunc in (12, 6, 3):
        r = minimize(cost, p, args=(trunc,), method='Nelder-Mead', options={'xatol': 1e-3, 'fatol': 1e-4, 'maxiter': 3000, 'initial_simplex': None})
        p = r.x
    return Sim(*p), cost(p, 3)

if __name__ == '__main__':
    name = sys.argv[1]; th0 = float(sys.argv[2]); s0 = float(sys.argv[3]); bottom = int(sys.argv[4]) if len(sys.argv) > 4 else 2200
    b = coarse(name, th0, s0, bottom)
    print('coarse', b)
    sim, c = refine(name, Sim(b[2], b[1], b[3], b[4]), bottom)
    print('refined', sim.s, sim.th, sim.tx, sim.ty, 'cost', c)
    reg = json.load(open(SP + 'reg.json')) if os.path.exists(SP + 'reg.json') else {}
    reg[name] = dict(sim.to_reg(), cost=c, coarse=b[0])
    json.dump(reg, open(SP + 'reg.json', 'w'), indent=1)

def refine2(name, sim0, bottom=2200, kinds=('complex', 'ba'), fix_th=True, truncs=(16, 8, 4), step=0.5, region=None):
    """chamfer refinement of (s, tx, ty) [and optionally th] using only the given outline kinds"""
    img, E, v = image_edges(name, bottom)
    if region is not None:
        x0, y0, x1, y1 = region; m = np.zeros_like(v); m[y0:y1, x0:x1] = True; v = v & m; E = E & m
    DT = ndi.distance_transform_edt(~E).astype(np.float32)
    P = template_points(step, kinds)
    H, W = E.shape
    th0 = sim0.th
    def unpack(p): return (p[0], th0 if fix_th else p[3], p[1], p[2])
    def cost(p, trunc):
        Q = Sim(*unpack(p)).fwd(P)
        m = (Q[:, 0] >= 0) & (Q[:, 1] >= 0) & (Q[:, 0] < W - 1) & (Q[:, 1] < H - 1)
        Qi = Q[m].astype(int); m2 = v[Qi[:, 1], Qi[:, 0]]
        if m2.sum() < 200: return 1e3
        d = ndi.map_coordinates(DT, [Q[m][m2, 1], Q[m][m2, 0]], order=1)
        return float(np.mean(np.minimum(d, trunc) ** 2)) / trunc ** 2
    p = np.array([sim0.s, sim0.tx, sim0.ty] + ([] if fix_th else [sim0.th]))
    for trunc in truncs:
        simplex = [p]
        for i in range(len(p)):
            q = p.copy(); q[i] += [0.05 * p[0], trunc * 1.5, trunc * 1.5, 0.5][i]; simplex.append(q)
        r = minimize(cost, p, args=(trunc,), method='Nelder-Mead', options={'xatol': 1e-4, 'fatol': 1e-6, 'maxiter': 4000, 'initial_simplex': np.array(simplex)})
        p = r.x
        print('  trunc', trunc, 'cost', round(r.fun, 4), 'p', np.round(p, 3))
    return Sim(*unpack(p)), r.fun

def coarse2(name, th, s0, bottom=2200, s_span=0.04, s_step=0.01, kinds=('complex', 'ba'), beta=0.25, bbox=(-1750, -400, -350, 1050), k=None):
    """global translation search with fixed rotation: FFT correlation of outline template vs edge proximity"""
    img, E, v = image_edges(name, bottom)
    H, W = E.shape
    if k is None: k = max(1, int(round(s0 / 1.0)))
    Hs, Ws = H // k, W // k
    Es = E[:Hs * k, :Ws * k].reshape(Hs, k, Ws, k).any((1, 3))
    vs = v[:Hs * k, :Ws * k].reshape(Hs, k, Ws, k).mean((1, 3)) > 0.5
    DT = ndi.distance_transform_edt(~Es)
    Pm = (np.exp(-DT ** 2 / (2 * 1.0 ** 2)) - beta).astype(np.float32) * vs
    P = template_points(0.5 * k / s0, kinds)
    x0, z0, x1, z1 = bbox
    P = P[(P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > z0) & (P[:, 1] < z1)]
    res = []
    for s in s0 * np.arange(1 - s_span, 1 + s_span + 1e-9, s_step):
        ss = s / k
        sim = Sim(ss, th, 0, 0)
        C = sim.fwd(np.array([[x0, z0], [x1, z0], [x0, z1], [x1, z1]]))
        off = -C.min(0) + 2
        sim = Sim(ss, th, off[0], off[1])
        shp = (int(C[:, 1].max() - C[:, 1].min()) + 5, int(C[:, 0].max() - C[:, 0].min()) + 5)
        T = render_template(P, sim, shp)
        sc = fftconvolve(Pm, T[::-1, ::-1], mode='full')
        i = np.unravel_index(np.argmax(sc), sc.shape)
        ty = i[0] - (T.shape[0] - 1); tx = i[1] - (T.shape[1] - 1)
        # second best (non-max suppression radius 20 small px)
        sc2 = sc.copy(); sc2[max(0, i[0] - 20):i[0] + 20, max(0, i[1] - 20):i[1] + 20] = -1e9
        res.append((float(sc[i]), float(sc2.max()), s, (off[0] + tx) * k, (off[1] + ty) * k))
    res.sort(reverse=True)
    return res
