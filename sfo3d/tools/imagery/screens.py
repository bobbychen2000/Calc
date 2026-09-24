"""Helpers to read the owner's Google Maps screenshots and their registrations (reference only - never textures).

Registration model (tools/sat/common.py `Sim`, reproduced here so tools/imagery does not import tools/sat):
    image px = c + s * R(th) * [x, z],  R(th) = [[cos th, -sin th], [sin th, cos th]]   (x east, z south, metres)
Registrations: tools/sat/work/reg.json.  Screens: tools/sat/screens/ (or $SFO_SCREENS).
Valid-area mask: copied from tools/sat/featreg.py `load` (rows 340..2200, map UI buttons and saturated UI colours
removed) so the audit uses exactly the pixels the registration pipeline used.
"""
import json, math, os
import numpy as np
from common import ROOT, GF

SAT = os.path.join(ROOT, 'tools', 'sat')
SCREENS = os.environ.get('SFO_SCREENS', os.path.join(SAT, 'screens'))
REG = json.load(open(os.path.join(SAT, 'work', 'reg.json')))


class Sim:
    """frame = 'equirect-v1' (legacy; every reg.json entry without a 'frame' key) or the current frame id: a legacy
    registration is applied to world_to_legacy(x, z) (exact, tools/geo_frame.py)."""
    def __init__(self, s, th, tx, ty, frame=None):
        t = math.radians(th); c, sn = math.cos(t), math.sin(t)
        self.s, self.th = s, th; self.frame = frame or GF.FRAME_ID
        self.A = s * np.array([[c, -sn], [sn, c]]); self.t = np.array([tx, ty], float)
        self.Ai = np.linalg.inv(self.A)

    def fwd(self, P):
        P = np.asarray(P, float)
        if self.frame == 'equirect-v1':
            X, Z = GF.world_to_legacy_np(P[..., 0], P[..., 1]); P = np.stack([X, Z], -1)
        return P @ self.A.T + self.t

    def inv(self, Q):
        P = (np.asarray(Q, float) - self.t) @ self.Ai.T
        if self.frame == 'equirect-v1':
            X, Z = GF.legacy_to_world_np(P[..., 0], P[..., 1]); P = np.stack([X, Z], -1)
        return P

    def as_world_sim(self, wc, half=800.0):
        """least-squares similarity in the CURRENT frame equivalent to this one over +-half m around world point wc
        (a legacy registration composed with the exact frame mapping is not a similarity; residual < 0.1 m)."""
        if self.frame == GF.FRAME_ID: return self
        g = np.linspace(-half, half, 9); W = np.array([(wc[0] + a, wc[1] + b) for a in g for b in g])
        Q = self.fwd(W)
        M = np.zeros((2 * len(W), 4)); M[0::2] = np.c_[W[:, 0], -W[:, 1], np.ones(len(W)), np.zeros(len(W))]
        M[1::2] = np.c_[W[:, 1], W[:, 0], np.zeros(len(W)), np.ones(len(W))]
        p, *_ = np.linalg.lstsq(M, Q.ravel(), rcond=None)            # q = [[a, -b], [b, a]] w + t
        return Sim(math.hypot(p[0], p[1]), math.degrees(math.atan2(p[1], p[0])), p[2], p[3], GF.FRAME_ID)


def sim_of(name):
    r = REG[name]; return Sim(r['s'], r['th'], r['tx'], r['ty'], r.get('frame', 'equirect-v1'))


def path_of(name):
    for f in os.listdir(SCREENS):
        if f.startswith(name): return os.path.join(SCREENS, f)
    raise FileNotFoundError(name)


def load(name):
    """BGR image + uint8 validity mask (255 = map pixels)."""
    import cv2
    img = cv2.imread(path_of(name))
    m = np.zeros(img.shape[:2], np.uint8); m[340:2200, 10:1280] = 255
    m[330:910, 1070:] = 0; m[1880:, 1020:] = 0
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ui = ((hsv[..., 1] > 150) & (hsv[..., 2] > 150)) | (img.min(2) > 245)
    ui = cv2.dilate(ui.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    m[ui] = 0
    return img, m


def rectify(img, mask, sim, X, Z):
    """sample the screenshot at world points (X, Z arrays of equal shape) -> (gray float32, valid bool)."""
    import cv2
    P = sim.fwd(np.stack([X.ravel(), Z.ravel()], 1)).astype(np.float32)
    mx = P[:, 0].reshape(X.shape); my = P[:, 1].reshape(X.shape)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out = cv2.remap(g, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float32)
    val = cv2.remap(mask, mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0
    return out, val
