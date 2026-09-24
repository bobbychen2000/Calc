import sys, json
from common import *
from register import refine
def sim_from(th, s, wpt, ipt):
    S = Sim(s, th, 0, 0); q = S.fwd(np.array([wpt], float))[0]
    return Sim(s, th, ipt[0] - q[0], ipt[1] - q[1])
def fit_points(W, I):
    """least-squares similarity from >=2 correspondences (world Nx2, image Nx2)"""
    W = np.asarray(W, float); I = np.asarray(I, float)
    wc, ic = W.mean(0), I.mean(0); w = W - wc; i = I - ic
    # complex-number similarity: i = a * w  (with z-axis as imaginary part, same handedness in both frames)
    zw = w[:, 0] + 1j * w[:, 1]; zi = i[:, 0] + 1j * i[:, 1]
    a = (np.conj(zw) @ zi) / (np.conj(zw) @ zw)
    s = abs(a); th = math.degrees(math.atan2(a.imag, a.real))
    S = Sim(s, th, 0, 0); q = S.fwd(wc[None])[0]
    return Sim(s, th, ic[0] - q[0], ic[1] - q[1])
def save(name, sim, cost=None, note=''):
    reg = json.load(open(SP + 'reg.json')) if os.path.exists(SP + 'reg.json') else {}
    reg[name] = {'s': sim.s, 'th': sim.th, 'tx': sim.tx, 'ty': sim.ty, 'cost': cost, 'note': note}
    json.dump(reg, open(SP + 'reg.json', 'w'), indent=1)
