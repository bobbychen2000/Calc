"""Walkway-end gap check (close-out round 4, buildings; the round-3 verifier's walkend probe made a build gate).

Where the app's fixed jet-bridge walkway begins at the building (js/live/gates.js walk[0], read through
tools/blender/app_bridges.json), the 3-D asset must close the walkway end: the facade itself, a vestibule from the facade to
the walkway start, or a door surround. A slot between the walkway end and the asset reads as a strip of daylight between the
bridge and the terminal (an undocked walkway) - the round-3 verifier found 24 of 48 ITB A / G walkway ends 0.3-0.9 m short of
the 3-D facade and 5 domestic ones (E8 / E9 / F8 / B2 / F22 L2).

Probe (per bridge whose walkway starts at this asset, per LOD): horizontal plane slices of the asset at the walkway floor at
its start + 0.3 / 1.5 / 2.7 m (gates.js walkway: floor - 0.3 .. floor + WALK_H 3.0) and rays from the walkway END FACE (the
line through walk[0] across the walkway) along -u (u = the walkway direction away from the building) at OFFSETS across the
full 2.6-m width (gates.js WALK_W; the outer probes 0.05 m inside the edges). The ray's open part starts at the end face, or,
where the app's own rotunda drum (gates.js: centre rot, radius rotR, band Hr - 0.3 .. Hr + 3.3) covers the probe point, at the
ray's exit from the drum (short walkways whose drum closes the walkway end). gap = distance to the first asset face beyond
that start (<= 0: the asset reaches into the walkway end: closed). FAIL: gap > GAP_MAX at any probe, or no asset face within
REACH (reported separately when the walkway starts at no building - e.g. a bridge fed from another bridge's rotunda).
Bridges whose drawn walkway does not start at walk[0] (walkFrom > 0: twin connectors drawn by the other bridge) are skipped.

    python3 tools/blender/walkend_check.py data/buildings3d/itb.glb AG        (stand-alone; the verify scripts import run())
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import app_bridges as AB  # noqa: E402

GROUND_Y = 3.0
GAP_MAX = 0.10                          # the close-out round-4 criterion (verifier: "gap <= 0.1 m over the full width")
HEIGHTS = (0.3, 1.5, 2.7)               # above the walkway floor at its start
OFFSETS = (-1.25, -0.85, -0.45, 0.0, 0.45, 0.85, 1.25)   # across the walkway (gates.js WALK_W 2.6: +-1.3)
BEHIND = 3.0                            # asset faces up to 3 m on the walkway side of the end face count (overlap = closed)
REACH = 15.0                            # no asset face within 15 m: the walkway does not start at this asset


def slice_y(T, y):
    """segments (k, 2, 2) in plan (x, z) of the triangles T (n, 3, 3) crossing the plane y."""
    s = T[:, :, 1] - y
    sg = s > 0
    cnt = sg.sum(1)
    idx = np.nonzero((cnt == 1) | (cnt == 2))[0]
    if not len(idx): return np.zeros((0, 2, 2))
    Ts, ss = T[idx], s[idx]
    cr, pp = [], []
    for (i, k) in ((0, 1), (1, 2), (2, 0)):
        a, b = ss[:, i], ss[:, k]
        c = (a > 0) != (b > 0)
        t = np.where(c, a / np.where(c, a - b, 1.0), 0.0)
        cr.append(c); pp.append(Ts[:, i] + (Ts[:, k] - Ts[:, i]) * t[:, None])
    P0 = np.where(cr[0][:, None], pp[0], np.where(cr[1][:, None], pp[1], pp[2]))
    P1 = np.where(cr[2][:, None], pp[2], np.where(cr[1][:, None], pp[1], pp[0]))
    return np.stack([P0, P1], 1)[:, :, [0, 2]]


def drum_exit(b, q, w, y):
    """distance along the unit direction w from q to where the ray leaves the bridge's own rotunda drum, if q lies inside it
    at the height y (absolute), else 0."""
    if not (GROUND_Y + b['Hr'] - 0.3 <= y <= GROUND_Y + b['Hr'] + 3.3): return 0.0
    c = np.array(b['rot'], float); r = float(b['rotR'])
    d = q - c
    if d @ d >= r * r: return 0.0
    bb = d @ w; cc = d @ d - r * r
    return float(-bb + math.sqrt(max(0.0, bb * bb - cc)))


def bridge_gaps(T, b):
    """per-probe gaps of one bridge against the triangles T (absolute world coordinates): dict(gaps [[h][offset]], max, min,
    none = probes without an asset face within REACH)."""
    w = b['walk']
    p0 = np.array([w[0][0], w[0][2]], float); p1 = np.array([w[1][0], w[1][2]], float)
    u = (p1 - p0) / np.linalg.norm(p1 - p0); v = np.array([-u[1], u[0]])
    R = REACH + 3.0
    lo, hi = T[:, :, [0, 2]].min(1), T[:, :, [0, 2]].max(1)
    m = (hi[:, 0] > p0[0] - R) & (lo[:, 0] < p0[0] + R) & (hi[:, 1] > p0[1] - R) & (lo[:, 1] < p0[1] + R)
    Tn = T[m]
    out = []
    for dh in HEIGHTS:
        y = GROUND_Y + w[0][1] + dh
        S = slice_y(Tn, y)
        row = []
        for o in OFFSETS:
            q = p0 + v * o
            t0 = drum_exit(b, q, -u, y)
            if not len(S): row.append(None); continue
            a = S[:, 0] - q; c = S[:, 1] - q
            ua, uc = a @ (-u), c @ (-u); va, vc = a @ v, c @ v
            cr = (va * vc <= 0) & (np.abs(va - vc) > 1e-9)
            t = np.where(cr, va / np.where(cr, va - vc, 1.0), 0.0)
            uu = ua + t * (uc - ua)
            ok = cr & (uu > -BEHIND) & (uu < REACH)
            row.append(round(float(uu[ok].min()) - t0, 3) if ok.any() else None)
        out.append(row)
    vals = [g for r in out for g in r if g is not None]
    none = sum(1 for r in out for g in r if g is None)
    return dict(gaps=out, max=max(vals) if vals else None, min=min(vals) if vals else None, none=none)


def bridges_at(letters):
    """the app bridges of these piers whose drawn fixed walkway starts at walk[0] (walkFrom 0), upper deck included."""
    return [b for b in AB.bridges(letters) if not b.get('walkFrom') and len(b['walk']) >= 2]


def run(T_by_lod, letters, exempt=None):
    """T_by_lod: {lod: triangles (n, 3, 3), absolute world coordinates}. exempt: {(stand, door, upper): reason} - bridges whose
    walkway does not start at a building (listed, not counted). -> dict per LOD: n, fails [...], worst, rows."""
    exempt = exempt or {}
    res = {}
    for lod, T in sorted(T_by_lod.items(), key=lambda kv: str(kv[0])):
        rows, fails, ex = [], [], []
        for b in bridges_at(letters):
            g = bridge_gaps(T, b)
            key = (b['stand'], b['door'], b['upper'])
            r = dict(stand=b['stand'], door=b['door'], upper=b['upper'], Hb=b['Hb'], max_gap=g['max'], min_gap=g['min'],
                     probes_without_face=g['none'], gaps=g['gaps'])
            bad = g['none'] > 0 or g['max'] is None or g['max'] > GAP_MAX
            if key in exempt:
                r['exempt'] = exempt[key]; ex.append(r)
            elif bad:
                fails.append(r)
            rows.append(r)
        mx = [r['max_gap'] for r in rows if r['max_gap'] is not None and 'exempt' not in r]
        res[lod] = dict(n=len(rows), n_fail=len(fails), n_exempt=len(ex), max_gap=round(max(mx), 3) if mx else None,
                        fails=[dict((k, v) for k, v in r.items() if k != 'gaps') | dict(gaps=r['gaps']) for r in fails],
                        exempt=[dict((k, v) for k, v in r.items() if k != 'gaps') for r in ex],
                        rows=[dict((k, v) for k, v in r.items() if k != 'gaps') for r in rows])
    return res


def tris_from_scene(S, lod, skip=('_lettering',)):
    """triangles (n, 3, 3) of the LOD's nodes of a verify_*.scene_meshes() dict (absolute world coordinates)."""
    T = [p['P'][p['T']] for n, m in S.items() if m['lod'] == lod and not any(k in n for k in skip) for p in m['prims']]
    return np.concatenate(T) if T else np.zeros((0, 3, 3))


if __name__ == '__main__':
    import verify_domestic as V
    path = sys.argv[1]; letters = sys.argv[2] if len(sys.argv) > 2 else 'ABCDEFG'
    S = {}
    for p in path.split('+'):
        j, bb, _ = V.load_glb(p); S.update(V.scene_meshes(j, bb))
    lods = sorted({m['lod'] for m in S.values() if m['lod'] is not None})
    r = run({l: tris_from_scene(S, l) for l in lods}, letters)
    for l, x in r.items():
        print('LOD%d: %d walkway ends, %d with a gap > %.2f m (or no face), max gap %s, exempt %d' % (l, x['n'], x['n_fail'], GAP_MAX, x['max_gap'], x['n_exempt']))
        for f in x['fails']:
            print('   %-5s L%d%s Hb %.2f max %s min %s none %d  %s' % (f['stand'], f['door'], ' U' if f['upper'] else '', f['Hb'], f['max_gap'],
                                                                   f['min_gap'], f['probes_without_face'], f['gaps'][1]))
