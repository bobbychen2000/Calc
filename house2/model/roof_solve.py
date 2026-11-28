"""The roof in 3-D from its survey on the near-nadir aerial (survey/roof.json) and a few measured heights.

    python3 -I model/roof_solve.py            # -> survey/roof_3d.json (+ a report)

Every roof-plane polygon of roof.json is drawn in p29 pixels.  A vertex lies on its pixel's ray through the registered
aerial camera, so only its height is unknown; each plane is z = a X + b Y + c.  Least squares over all of them:
  * every vertex of a plane lies on that plane (2 cm);
  * planes of the same storey that share a vertex (within 4 px) share its 3-D point; a one-storey roof vanishing under
    a two-storey eave meets that eave in the image but is a different point, so storeys never share;
  * eave vertices sit at their block's eave height, an unknown with a prior (EAVE below);
  * ridges are level; sloped planes have a pitch near PITCH and fall the way the survey says (downhill_img); the deck
    is flat.
Heights are metres above the pool deck (Z = 0).  The measured heights (tools/epi.py: aerial rays drawn into p28 / the
video's rear frames): one-storey eaves 3.1 (north porch) - 3.6 (patio wing PB), two-storey eaves 6.3-6.5, the core's
hip apex ~8.5 (so ~28 deg pitch), the balcony gable's apex ~7.5-8.0.
"""
import json
import os
import sys

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from model import frame  # noqa: E402
from tools import cams as CAMS  # noqa: E402

AERIAL = 'photos/p29_ddf5dc.jpg'
PITCH = 28.0                     # deg, prior for every sloped plane (6.4 / 12)
EAVE = {1: (3.35, 0.35), 2: (6.40, 0.15)}           # storey -> (prior m above the deck, sigma)
EAVE_BLOCK = {'north_porch': (3.10, 0.10), 'patio_1st': (3.60, 0.10)}   # measured
EAVE_KINDS = ('eave', 'eave_over_lower_roof', 'eave_end')
MERGE_PX = 4.5
# ---- corrections from the oblique views (round 2: this file is the single source of the roofs; zones/house.py and
# zones/roof_details.py both read survey/roof_3d.json and apply no height corrections of their own) -------------------
# garage + north wing: the 28 deg prior stood 0.5-0.65 m above the roof's silhouette in p01 (front photo, fitted
# camera); ~19 deg puts the garage ridge at ~4.8 and the north wing's at ~5.1.
PITCH_BLOCK = {'garage_wing': (18.5, 1.0), 'north_wing': (18.0, 1.0)}
# the garage's south gable: 26 deg (the aerial's ridge displacement + p01's apex); the balcony gable ~27.5 deg
PITCH_PLANE = {'gb_w': (26.0, 1.5), 'gb_e': (26.0, 1.5), 'bg_n': (27.5, 2.0), 'bg_s': (27.5, 2.0)}
# measured ridge heights (plane id -> (z, sigma)): the balcony gable's apex (p21: 0.2 m under the first solve; epi 7.5-8.0)
RIDGE_Z = {'bg_n': (7.97, 0.01), 'bg_s': (7.97, 0.01)}
GARAGE_GABLE_PITCH = 26.0        # rebuilt symmetric after the solve (garage_gable below)
# survey corrections (p29 at 3.5x): the diagonal front-porch leg is one shed sloping SW from under the front gable FG's
# eave to the porch eave; the small entry gable over the steps (apex ~(725,1249), ridge NE-SW) stands on it and is built
# in model/zones/house.py.  (The survey's two gable planes put the leg's NW valley vertex on the downhill side of its
# own eave, which forced the solve flat there.)
REPLACE = {
    'roof.swp_nw': {'id': 'roof.swp', 'type': 'roof_plane', 'poly': [[698, 1147], [820, 1264], [809, 1274], [790, 1295],
                                                                       [687, 1192], [707, 1172]],
                    'attrs': {'block': 'porch_1st', 'storey': 1, 'downhill_img': [-0.707, 0.707],
                              'edges': [{'a': [698, 1147], 'b': [820, 1264], 'kind': 'under_upper_eave'},
                                        {'a': [820, 1264], 'b': [809, 1274], 'kind': 'valley'},
                                        {'a': [809, 1274], 'b': [790, 1295], 'kind': 'eave'},
                                        {'a': [790, 1295], 'b': [687, 1192], 'kind': 'eave'},
                                        {'a': [687, 1192], 'b': [707, 1172], 'kind': 'eave'},
                                        {'a': [707, 1172], 'b': [698, 1147], 'kind': 'valley'}]}},
    'roof.swp_se': None,
}


def load():
    r = json.load(open(os.path.join(HERE, 'survey', 'roof.json')))
    planes = []
    for e in r['elements']:
        if e['type'] not in ('roof_plane', 'roof_flat'):
            continue
        if e['id'] in REPLACE:
            if REPLACE[e['id']] is not None:
                planes.append(REPLACE[e['id']])
            continue
        planes.append(e)
    return r, planes


def solve(verbose=True):
    r, planes = load()
    cam = frame.world_cams()[AERIAL]
    # nodes: (storey, pixel) clusters
    nodes, node_st = [], []
    pv = []                                      # per plane: list of node ids (polygon order)
    for p in planes:
        st = p['attrs']['storey']
        ids = []
        for uv in p['poly']:
            uv = np.asarray(uv, float)
            j = None
            for k, (q, s) in enumerate(zip(nodes, node_st)):
                if s == st and np.linalg.norm(q['uv'] - uv) < MERGE_PX:
                    j = k
                    break
            if j is None:
                nodes.append({'uv': uv, 'n': 1})
                node_st.append(st)
                j = len(nodes) - 1
            else:
                q = nodes[j]
                q['uv'] = (q['uv'] * q['n'] + uv) / (q['n'] + 1)
                q['n'] += 1
            if not ids or ids[-1] != j:
                ids.append(j)
        if len(ids) > 1 and ids[0] == ids[-1]:
            ids.pop()
        pv.append(ids)
    N, M = len(nodes), len(planes)
    uv = np.array([q['uv'] for q in nodes])
    o, d = CAMS.ray(cam, uv)
    kx, ky = d[:, 0] / d[:, 2], d[:, 1] / d[:, 2]

    def xy(z, ids=slice(None)):
        return o[0] + kx[ids] * (z - o[2]), o[1] + ky[ids] * (z - o[2])

    # edge kinds per (plane, node pair)
    def nearest(p_uv):
        return int(np.argmin(np.linalg.norm(uv - p_uv, axis=1)))
    eave_nodes = {}                              # node -> block
    ridge_pairs = []
    for p in planes:
        st = p['attrs']['storey']
        for ed in p['attrs'].get('edges', []):
            a = b = None
            for k in range(N):
                if node_st[k] != st:
                    continue
                if np.linalg.norm(uv[k] - ed['a']) < MERGE_PX + 1:
                    a = k
                if np.linalg.norm(uv[k] - ed['b']) < MERGE_PX + 1:
                    b = k
            if a is None or b is None:
                continue
            if ed['kind'] in EAVE_KINDS:
                eave_nodes[a] = eave_nodes.get(a, p['attrs']['block'])
                eave_nodes[b] = eave_nodes.get(b, p['attrs']['block'])
            elif ed['kind'] == 'ridge':
                ridge_pairs.append((a, b))
    blocks = sorted({p['attrs']['block'] for p in planes})
    bidx = {b: i for i, b in enumerate(blocks)}
    bst = {p['attrs']['block']: p['attrs']['storey'] for p in planes}
    eprior = np.array([EAVE_BLOCK.get(b, EAVE[bst[b]]) for b in blocks])
    flat = np.array([p['type'] == 'roof_flat' for p in planes])
    pid = [p['id'].split('.', 1)[1] for p in planes]
    pprior = [PITCH_PLANE.get(pid[i], PITCH_BLOCK.get(p['attrs']['block'], (PITCH, 6.0))) for i, p in enumerate(planes)]
    ridge_z = []                                 # (node, z, sigma)
    for i, p in enumerate(planes):
        if pid[i] not in RIDGE_Z:
            continue
        st = p['attrs']['storey']
        for ed in p['attrs'].get('edges', []):
            if ed['kind'] != 'ridge':
                continue
            for q in (ed['a'], ed['b']):
                for k in range(N):
                    if node_st[k] == st and np.linalg.norm(uv[k] - q) < MERGE_PX + 1:
                        ridge_z.append((k,) + tuple(RIDGE_Z[pid[i]]))
    down = []
    for p in planes:
        dv = p['attrs'].get('downhill_img')
        down.append(None if dv is None else np.array([dv[0], -dv[1]], float) / max(np.hypot(*dv), 1e-9))

    # initial values
    z0 = np.array([eprior[bidx[eave_nodes[k]], 0] if k in eave_nodes else
                   (EAVE[node_st[k]][0] + 1.2) for k in range(N)])
    t = np.tan(np.radians(PITCH))
    P0 = []
    for i, p in enumerate(planes):
        X, Y = xy(z0[pv[i]], pv[i])
        if flat[i] or down[i] is None:
            P0 += [0.0, 0.0, float(np.max(z0[pv[i]]))]
        else:
            g = -down[i] * t
            c = np.mean(z0[pv[i]] - g[0] * X - g[1] * Y)
            P0 += [g[0], g[1], c]
    x0 = np.r_[z0, np.array(P0), eprior[:, 0]]

    def resid(x, pprior=[(PITCH, 6.0)] * M, ridge_z=()):
        z = x[:N]
        P = x[N:N + 3 * M].reshape(M, 3)
        e = x[N + 3 * M:]
        X, Y = xy(z)
        out = []
        for i in range(M):
            ids = pv[i]
            out.append((z[ids] - (P[i, 0] * X[ids] + P[i, 1] * Y[ids] + P[i, 2])) / 0.02)
            g = P[i, :2]
            if flat[i]:
                out.append(g / 0.01)
            else:
                out.append([(np.degrees(np.arctan(np.hypot(*g))) - pprior[i][0]) / pprior[i][1]])
                if down[i] is not None:
                    gn = -g / max(np.hypot(*g), 1e-6)
                    out.append([(gn[0] * down[i][1] - gn[1] * down[i][0]) / 0.25,
                                min(0.0, gn @ down[i]) / 0.1])
        for k, b in eave_nodes.items():
            out.append([(z[k] - e[bidx[b]]) / 0.04])
        for a, b in ridge_pairs:
            out.append([(z[a] - z[b]) / 0.05])
        for k, zr, sg in ridge_z:
            out.append([(z[k] - zr) / sg])
        out.append((e - eprior[:, 0]) / eprior[:, 1])
        return np.concatenate([np.atleast_1d(np.asarray(v, float)) for v in out])

    # stage 1: the survey alone (one pitch prior).  Stage 2: the corrected blocks / planes re-solved with their own
    # priors, everything else held (nodes they share with other planes included), so a correction stays local.
    sol = least_squares(resid, x0, loss='soft_l1', f_scale=2.0, x_scale='jac', max_nfev=4000)
    x = sol.x.copy()
    aff = [i for i in range(M) if pprior[i] != (PITCH, 6.0) or pid[i] in RIDGE_Z]
    if aff:
        other = {k for i in range(M) if i not in aff for k in pv[i]}
        free = np.zeros(len(x), bool)
        for i in aff:
            free[N + 3 * i:N + 3 * i + 3] = True
            for k in pv[i]:
                free[k] = k not in other
        for k, _, _ in ridge_z:              # a measured ridge moves even where it runs into a held roof
            free[k] = True
        for b in blocks:
            if all(i in aff for i, p in enumerate(planes) if p['attrs']['block'] == b):
                free[N + 3 * M + bidx[b]] = True

        def resid2(xf):
            xx = x.copy()
            xx[free] = xf
            return resid(xx, pprior, ridge_z)
        sol = least_squares(resid2, x[free], loss='soft_l1', f_scale=2.0, x_scale='jac', max_nfev=4000)
        x[free] = sol.x
    z = x[:N]
    P = x[N:N + 3 * M].reshape(M, 3)
    e = x[N + 3 * M:]
    X, Y = xy(z)
    res = resid(x, pprior, ridge_z)
    out = {'_note': 'generated by model/roof_solve.py from survey/roof.json + the registered aerial; metres, world frame '
                    '(Z above the pool deck). planes: id, block, storey, plane z = a X + b Y + c, poly = 3-D vertices '
                    '(each on its own plane), edges = the survey kinds per polygon edge.',
           'eaves': {b: round(float(e[i]), 3) for i, b in enumerate(blocks)}, 'planes': []}
    for i, p in enumerate(planes):
        ids = pv[i]
        a_, b_, c_ = P[i]
        # vertex on its own plane: re-intersect the ray with the plane (shared vertices differ by mm)
        zz = (c_ + a_ * (o[0] - kx[ids] * o[2]) + b_ * (o[1] - ky[ids] * o[2])) / (1 - a_ * kx[ids] - b_ * ky[ids])
        Xi, Yi = xy(zz, ids)
        kinds = []
        for j in range(len(ids)):
            ka, kb = uv[ids[j]], uv[ids[(j + 1) % len(ids)]]
            kind = 'edge'
            for ed in p['attrs'].get('edges', []):
                if (np.linalg.norm(np.subtract(ed['a'], ka)) < MERGE_PX + 1 and np.linalg.norm(np.subtract(ed['b'], kb)) < MERGE_PX + 1) or \
                   (np.linalg.norm(np.subtract(ed['b'], ka)) < MERGE_PX + 1 and np.linalg.norm(np.subtract(ed['a'], kb)) < MERGE_PX + 1):
                    kind = ed['kind']
            kinds.append(kind)
        out['planes'].append({'id': p['id'].split('.', 1)[1], 'block': p['attrs']['block'], 'storey': p['attrs']['storey'],
                              'flat': bool(flat[i]), 'plane': [round(float(v), 5) for v in (a_, b_, c_)],
                              'pitch_deg': round(float(np.degrees(np.arctan(np.hypot(a_, b_)))), 2),
                              'poly': [[round(float(a), 3), round(float(b), 3), round(float(c), 3)] for a, b, c in zip(Xi, Yi, zz)],
                              'edges': kinds})
    garage_gable(out)
    json.dump(out, open(os.path.join(HERE, 'survey', 'roof_3d.json'), 'w'), indent=1)
    if verbose:
        print('nodes %d, planes %d, cost %.1f, rms resid %.2f sigma' % (N, M, sol.cost, np.sqrt(np.mean(res ** 2))))
        for b, v in out['eaves'].items():
            print('  eave %-20s %.2f m' % (b, v))
        for q in out['planes']:
            zs = [v[2] for v in q['poly']]
            print('  %-8s %-18s pitch %5.1f  z %.2f..%.2f' % (q['id'], q['block'], q['pitch_deg'], min(zs), max(zs)))
        big = np.argsort(-np.abs(res))[:8]
        print('largest residuals (sigma):', np.round(res[big], 1))
    return out


def garage_gable(out):
    """The garage's south gable rebuilt symmetric about the middle of its two rake feet at GARAGE_GABLE_PITCH (the
    solve leaves its ridge ~0.3 m off centre: the ridge pixel is displaced by its unknown height).  gb_w / gb_e become
    ridge - rake - eave - valley quads whose valleys lie ON g_s's plane, and g_s's notch takes the same three points."""
    Q = {p['id']: p for p in out['planes']}
    gw, ge, gs = Q['gb_w'], Q['gb_e'], Q['g_s']
    fw, fe = np.array(gw['poly'][2]), np.array(ge['poly'][2])       # rake feet
    a, b, c = gs['plane']
    xr, ze, yf = (fw[0] + fe[0]) / 2, (fw[2] + fe[2]) / 2, (fw[1] + fe[1]) / 2
    half = (fe[0] - fw[0]) / 2
    t = np.tan(np.radians(GARAGE_GABLE_PITCH))
    za = ze + half * t
    on_gs = lambda x, z: (z - a * x - c) / b                        # noqa: E731  y where g_s is at height z
    apex = [xr, on_gs(xr, za), za]
    vw, ve = [fw[0], on_gs(fw[0], ze), ze], [fe[0], on_gs(fe[0], ze), ze]
    rnd = lambda P: [[round(float(v), 3) for v in q] for q in P]    # noqa: E731
    gw['poly'] = rnd([apex, [xr, yf, za], [fw[0], yf, ze], vw])     # edges: ridge, rake, eave, valley
    ge['poly'] = rnd([apex, ve, [fe[0], yf, ze], [xr, yf, za]])     # edges: valley, eave, rake, ridge
    gw['plane'] = [round(float(v), 5) for v in (t, 0.0, ze - t * fw[0])]
    ge['plane'] = [round(float(v), 5) for v in (-t, 0.0, ze + t * fe[0])]
    gw['pitch_deg'] = ge['pitch_deg'] = GARAGE_GABLE_PITCH
    # g_s: ['hip', 'hip', 'eave', 'valley', 'valley', 'eave'] -> vertices 3, 4, 5 = east valley foot, apex, west valley foot
    P = [np.array(v) for v in gs['poly']]
    d = [np.linalg.norm(P[3][:2] - np.array(v[:2])) for v in (ve, vw)]
    first, last = (ve, vw) if d[0] < d[1] else (vw, ve)
    gs['poly'] = rnd([P[0], P[1], P[2], first, apex, last])


if __name__ == '__main__':
    solve()
