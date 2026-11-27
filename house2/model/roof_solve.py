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

    def resid(x):
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
                out.append([(np.degrees(np.arctan(np.hypot(*g))) - PITCH) / 6.0])
                if down[i] is not None:
                    gn = -g / max(np.hypot(*g), 1e-6)
                    out.append([(gn[0] * down[i][1] - gn[1] * down[i][0]) / 0.25,
                                min(0.0, gn @ down[i]) / 0.1])
        for k, b in eave_nodes.items():
            out.append([(z[k] - e[bidx[b]]) / 0.04])
        for a, b in ridge_pairs:
            out.append([(z[a] - z[b]) / 0.05])
        out.append((e - eprior[:, 0]) / eprior[:, 1])
        return np.concatenate([np.atleast_1d(np.asarray(v, float)) for v in out])

    sol = least_squares(resid, x0, loss='soft_l1', f_scale=2.0, x_scale='jac', max_nfev=4000)
    x = sol.x
    z = x[:N]
    P = x[N:N + 3 * M].reshape(M, 3)
    e = x[N + 3 * M:]
    X, Y = xy(z)
    res = resid(x)
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


if __name__ == '__main__':
    solve()
