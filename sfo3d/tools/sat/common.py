"""Shared helpers for georeferencing the user's satellite screenshots against the SFO Museum geometry."""
import json, math, os
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
_HERE = os.path.dirname(os.path.abspath(__file__))
# the user's Google Maps satellite screenshots (1290x2796 iPhone PNGs; reference only - never used as textures)
UP = os.environ.get('SFO_SCREENS', os.path.join(_HERE, 'screens')) + os.sep
# working directory: registrations (reg.json), detections, debug renders
SP = os.environ.get('SFO_SATWORK', os.path.join(_HERE, 'work')) + os.sep
os.makedirs(SP, exist_ok=True)
# uniq.txt = absolute paths of the screenshots, resolved from work/screens.txt (basename stems, extension-agnostic)
def _write_uniq():
    lst = os.path.join(SP, 'screens.txt')
    if not os.path.exists(lst): return
    files = os.listdir(UP) if os.path.isdir(UP) else []
    out = []
    for stem in open(lst).read().split():
        m = [f for f in files if f.startswith(stem)]
        out.append(os.path.join(UP, m[0]) if m else os.path.join(UP, stem + '-image.png'))
    open(os.path.join(SP, 'uniq.txt'), 'w').write('\n'.join(out))
_write_uniq()

def rings_all(kind):
    """list of rings ([[x,z],...]) for a category"""
    out = []
    if kind == 'complex':
        for poly in D['terminalComplex']: out += poly
    elif kind == 'ba':
        for b in D['boardingAreas']:
            for poly in b['polys']: out += poly
    elif kind == 'terminals':
        for t in D['terminals']:
            for poly in t['polys']: out += poly
    elif kind == 'taxiways':
        for t in D['taxiways']:
            for poly in t['polys']: out += poly
    elif kind == 'runways':
        for r in D['runways']:
            for poly in r['polys']: out += poly
    elif kind == 'structures':
        for s in D['structures']:
            if s['kind'] == 'rail': continue
            for poly in s['polys']: out += poly
    return out

def sample_edges(rings, step=1.0):
    pts = []
    for r in rings:
        n = len(r)
        for i in range(n):
            a = np.array(r[i], float); b = np.array(r[(i + 1) % n], float)
            L = np.linalg.norm(b - a)
            k = max(1, int(L / step))
            for t in np.arange(k) / k: pts.append(a + (b - a) * t)
    return np.array(pts)

class Sim:
    """world (x east, z south) -> image px: p = c + s * R(theta) * [x, z]  (theta = screen rotation)."""
    def __init__(self, s, th_deg, tx, ty):
        self.s, self.th, self.tx, self.ty = s, th_deg, tx, ty
    def M(self):
        t = math.radians(self.th); c, s = math.cos(t), math.sin(t)
        # north_cw = th: world north (0,-1) maps to screen direction (sin th, -cos th)
        # world east (1,0) maps to (cos th, sin th)
        A = self.s * np.array([[c, -s], [s, c]])
        return A, np.array([self.tx, self.ty])
    def fwd(self, P):
        A, t = self.M(); return P @ A.T + t
    def inv(self, Q):
        A, t = self.M(); return (Q - t) @ np.linalg.inv(A).T
