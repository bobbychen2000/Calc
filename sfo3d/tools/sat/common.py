"""Shared helpers for georeferencing the user's satellite screenshots against the SFO Museum geometry.

Frames (tools/geo_frame.py): everything in world metres is in the current world frame ('ltp-nad83-2011', = js/geo.js)
unless it says otherwise. The screenshot registrations in work/reg.json and the hand measurements in stand_defs.py and
work/*.json were made in the LEGACY frame 'equirect-v1'; registrations carry no 'frame' key, so sim_from_reg()
returns a Sim that converts world -> legacy before applying the similarity (exact), and stand_defs.py converts its
stands on import. New registrations are written with frame = geo_frame.FRAME_ID.
The screenshots are reference only: no committed coordinates may be derived from them any more (owner, 24 Sep 2026).
"""
import json, math, os, sys
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import geo_frame as GF
LEGACY_FRAME = 'equirect-v1'
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
    """world (x east, z south) -> image px: p = c + s * R(theta) * [x', z']  (theta = screen rotation), where
    (x', z') = (x, z) for a registration made in the current world frame, and = geo_frame.world_to_legacy(x, z) for
    one made in the legacy frame (frame=LEGACY_FRAME; all of reg.json as of 24 Sep 2026)."""
    def __init__(self, s, th_deg, tx, ty, frame=None):
        self.s, self.th, self.tx, self.ty = s, th_deg, tx, ty
        self.frame = frame or GF.FRAME_ID
    def M(self):
        t = math.radians(self.th); c, s = math.cos(t), math.sin(t)
        # north_cw = th: world north (0,-1) maps to screen direction (sin th, -cos th)
        # world east (1,0) maps to (cos th, sin th)
        A = self.s * np.array([[c, -s], [s, c]])
        return A, np.array([self.tx, self.ty])
    def fwd(self, P):
        P = np.asarray(P, float)
        if self.frame == LEGACY_FRAME:
            X, Z = GF.world_to_legacy_np(P[..., 0], P[..., 1]); P = np.stack([X, Z], -1)
        A, t = self.M(); return P @ A.T + t
    def inv(self, Q):
        A, t = self.M(); P = (np.asarray(Q, float) - t) @ np.linalg.inv(A).T
        if self.frame == LEGACY_FRAME:
            X, Z = GF.legacy_to_world_np(P[..., 0], P[..., 1]); P = np.stack([X, Z], -1)
        return P
    def to_reg(self):
        return {'s': self.s, 'th': self.th, 'tx': self.tx, 'ty': self.ty, 'frame': self.frame}

def sim_from_reg(r):
    """Sim for a reg.json entry; entries without 'frame' are legacy-frame registrations."""
    return Sim(r['s'], r['th'], r['tx'], r['ty'], frame=r.get('frame', LEGACY_FRAME))
