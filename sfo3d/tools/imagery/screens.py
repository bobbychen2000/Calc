"""Helpers to read the owner's Google Maps screenshots and their registrations (reference only - never textures).

Registration model (tools/sat/common.py `Sim`, reproduced here so tools/imagery does not import tools/sat):
    image px = c + s * R(th) * [x, z],  R(th) = [[cos th, -sin th], [sin th, cos th]]   (x east, z south, metres)
Registrations: tools/sat/work/reg.json.  Screens: tools/sat/screens/ (or $SFO_SCREENS).
Valid-area mask: copied from tools/sat/featreg.py `load` (rows 340..2200, map UI buttons and saturated UI colours
removed) so the audit uses exactly the pixels the registration pipeline used.
"""
import json, math, os
import numpy as np
from common import ROOT

SAT = os.path.join(ROOT, 'tools', 'sat')
SCREENS = os.environ.get('SFO_SCREENS', os.path.join(SAT, 'screens'))
REG = json.load(open(os.path.join(SAT, 'work', 'reg.json')))


class Sim:
    def __init__(self, s, th, tx, ty):
        t = math.radians(th); c, sn = math.cos(t), math.sin(t)
        self.s, self.th = s, th
        self.A = s * np.array([[c, -sn], [sn, c]]); self.t = np.array([tx, ty], float)
        self.Ai = np.linalg.inv(self.A)

    def fwd(self, P): return np.asarray(P, float) @ self.A.T + self.t

    def inv(self, Q): return (np.asarray(Q, float) - self.t) @ self.Ai.T


def sim_of(name):
    r = REG[name]; return Sim(r['s'], r['th'], r['tx'], r['ty'])


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
