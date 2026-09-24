"""Shared helpers for the livery tools (tools/liveries/*): paths, the runtime type table (js/aircraft/types.js + fit.js,
run under node so the painter uses exactly the fit the app renders), the fuselage section envelope of a model
(data/models/features.json `sec`), and the Python port of js/live/models.js applyStretch."""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
MD = os.path.join(ROOT, 'data', 'models')
LIV = os.path.join(ROOT, 'data', 'liveries')
CACHE = os.path.join(ROOT, 'refs', 'cache', 'liveries')
ORIG = os.path.join(ROOT, 'refs', 'cache', 'models_orig')   # pre-atlas .sfom backups (tools/liveries/atlas.py)
sys.path.insert(0, HERE)

NODE_DUMP = r"""
import { TYPES, SPEC, ICAO_TYPES } from './js/aircraft/types.js';
import { TYPE_MODEL, MODEL_BASE } from './js/aircraft/fit.js';
const o = { typeModel: TYPE_MODEL, base: MODEL_BASE, icao: ICAO_TYPES, types: {} };
for (const k in TYPES) { const T = TYPES[k]; if (k !== T.key) continue; const f = T.fit || null;
  o.types[k] = { name: T.name, L: T.L, R: T.R, top: T.top || 1.03, cls: T.cls, win: T.win, doors: T.doors, doorsOpt: T.doorsOpt || null,
    cockpit: T.cockpit || null, fin: T.fin, hstab: T.hstab, eng: T.eng || null, rear: T.rear || null,
    fit: f && { model: f.model, base: f.base, s: f.s, s0: f.s0, plugs: f.plugs, stretch: f.stretch } };
}
console.log(JSON.stringify(o));
"""
_app = None


def app():
    """TYPES geometry + fit per type, as the app computes them (node)."""
    global _app
    if _app is None:
        r = subprocess.run(['node', '--no-warnings', '--input-type=module', '-e', NODE_DUMP], cwd=ROOT, capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr)
        _app = json.loads(r.stdout)
    return _app


def features():
    return json.load(open(os.path.join(MD, 'features.json')))


class Envelope:
    """Fuselage section of a model along the body, per station s (m aft of the nose, model units): top and bottom of the
    skin on the centre plane and the maximum half width, measured on the mesh by planar cuts every 0.5 m through the
    body, fin and gear-door zones. The raw cuts also catch the wing (the half width jumps to the semi-span), the
    tailplane and the fin (the top jumps to the fin tip). Those are removed:
      - half width: max |z| of the cut between the corrected top and bottom, bounded by 1.25 x the cabin aspect ratio x
        the local half height (the wing root fillet is counted, the wing is not); isolated outliers (door gaps) are
        replaced by the running median;
      - top: aft of the fin leading edge (first aft station where the top rises > 0.12 m above the cabin top), the tail
        cone top is a straight line from the fin root to the tail tip (last station before the bottom line jumps up to
        the fin, + 10 % of the cabin height), which is how the tail cones of these aircraft are drawn in side view.
    """
    def __init__(self, P, idx, zone, L, dx=0.5):
        sys.path.insert(0, os.path.join(ROOT, 'tools', 'models'))
        from model_features import plane_segments
        tri = idx[np.isin(zone[idx], (0, 1, 4)).all(1)]
        s = np.arange(0, L + dx, dx); n = len(s)
        cuts = []
        top = np.full(n, np.nan); bot = np.full(n, np.nan)
        for i, st in enumerate(s):
            seg = plane_segments(P, tri, -min(max(st, 0.02), L - 0.02))
            pts = seg.reshape(-1, 2) if len(seg) else np.zeros((0, 2))
            cuts.append(pts)
            if not len(pts): continue
            c = pts[np.abs(pts[:, 1]) < 0.3]
            if not len(c): c = pts
            top[i] = c[:, 0].max(); q = pts[np.abs(pts[:, 1]) < max(0.5 * np.abs(pts[:, 1]).max(), 0.3), 0]; bot[i] = q.min() if len(q) else pts[:, 0].min()
        def fill(a):
            ok = ~np.isnan(a)
            return np.interp(s, s[ok], a[ok]) if ok.any() else np.zeros(n)
        top = fill(top); bot = fill(bot)
        m = (s > 0.45 * L) & (s < 0.7 * L)
        self.mainTop = float(np.median(top[m])); self.mainBot = float(np.median(bot[m]))
        H = self.mainTop - self.mainBot
        # tail tip: last station before the bottom line jumps (> 0.25 H within 1 m) onto the fin
        iend = n - 1; k = max(1, int(round(1.0 / dx)))
        for i in range(int(0.7 * n), n - k):
            if bot[i + k] - bot[i] > 0.25 * H: iend = i; break
        ifin = None
        for i in range(int(0.5 * n), iend):
            if top[i] > self.mainTop + 0.12 and top[min(i + 1, n - 1)] >= top[i] - 0.05: ifin = i; break
        topr = top.copy()
        if ifin is not None:
            t0 = min(top[ifin - 1], self.mainTop); t1 = bot[iend] + 0.1 * H
            for i in range(ifin, n):
                f = (s[i] - s[ifin - 1]) / max(s[iend] - s[ifin - 1], 1e-6)
                topr[i] = t0 + (t1 - t0) * min(f, 1.0)
        botr = bot.copy(); botr[iend + 1:] = botr[iend]; topr[iend + 1:] = topr[iend]
        # cabin aspect (half width / half height) from mid-height widths
        mw = []
        for i in np.where(m)[0]:
            pts = cuts[i]; yc = (topr[i] + botr[i]) / 2; hh = (topr[i] - botr[i]) / 2
            q = pts[np.abs(pts[:, 0] - yc) < 0.15 * hh] if len(pts) else pts
            if len(q): mw.append(np.abs(q[:, 1]).max() / hh)
        asp = float(np.median(mw)) if mw else 1.0
        asp = min(asp, 1.2)
        hw = np.full(n, np.nan)
        for i in range(n):
            pts = cuts[i]
            if not len(pts) or s[i] > s[iend] + dx: continue
            hh = max((topr[i] - botr[i]) / 2, 0.05)
            sel = (pts[:, 0] > botr[i] - 0.1) & (pts[:, 0] < topr[i] + 0.1) & (np.abs(pts[:, 1]) < 1.25 * asp * hh + 0.15)
            if sel.any(): hw[i] = np.abs(pts[sel, 1]).max()
        hw = fill(hw)
        from scipy.ndimage import median_filter
        med = median_filter(hw, size=5, mode='nearest')
        bad = (np.abs(hw - med) > 0.25 * np.maximum(med, 0.2)) & (s > 1.5)
        if bad.any(): ok = ~bad; hw = np.interp(s, s[ok], hw[ok])
        hw[iend + 1:] = np.minimum(hw[iend + 1:], hw[iend])
        self.s = s; self.top = topr; self.bot = botr; self.hw = hw; self.L = L; self.sEnd = float(s[iend]); self.iFin = ifin
        self.mainHW = float(np.median(hw[m])); self.asp = asp; self.rawTop = top

    def at(self, st):
        st = np.asarray(st, float)
        return np.interp(st, self.s, self.top), np.interp(st, self.s, self.bot), np.interp(st, self.s, self.hw)


ZONE_NOFIN = (2, 3, 7)


def apply_stretch(P, Z, st):
    """Python port of js/live/models.js applyStretch (wing span fit, fin height fit, fuselage plugs), model units."""
    P = np.array(P, float, copy=True)
    if not st: return P
    W, F = st.get('wing'), st.get('fin')
    if W:
        az = np.abs(P[:, 2]); m = (P[:, 0] >= W['xMin']) & (az > W['z0'])
        add = np.where(az >= W['z1'], W['dz'], (az - W['z0']) * W['dz'] / (W['z1'] - W['z0']))
        P[m, 2] += np.sign(P[m, 2]) * add[m]
    if F:
        m = (P[:, 0] < F['xF']) & (P[:, 1] > F['yF']) & ~np.isin(Z, ZONE_NOFIN)
        P[m, 1] = F['yF'] + (P[m, 1] - F['yF']) * F['k']
    if st.get('cut1') is not None:
        x = P[:, 0].copy()
        P[x < st['cut2'], 0] -= st['d1'] + st['d2']
        P[(x >= st['cut2']) & (x < st['cut1']), 0] -= st['d1']
    return P


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def hex_rgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])
