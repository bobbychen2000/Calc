"""Numeric back-face / see-through QA of a building glb (no bpy, no renderer) - close-out round 3 fix 2 (verifier v2 / v4).

Adopted from the independent verifier's tool of close-out round 3 (scratchpad c3/buildings_ver/bfray.py) so that the build
checks run the same test the verifier ran (verify_landside.py: LOD2 see-through per building).
Orthographic first-hit rays (as the red back-face renders, but over the whole asset):
  horizontal: slice LOD triangles at plane y = GY + h (h = 0.5..H, 1-m steps), 16 azimuths, rays every SP m; the first segment
              hit is a BACK face (ray along the triangle normal) of a single-sided material -> a hit (a hole / open shell /
              wrong winding)
  vertical:   slices x = const every SP m, rays straight down every SP m in z; first hit back face -> hit (a roof hole)
Context assets: join paths with '+' (their faces occlude, only the first file's faces count as hits).
    python3 tools/blender/bf_rays.py <glb>[+<context glb>...] <out.json> [lod=0] [sp=0.5]
Writes per node: hits, materials, and the hit points clustered on a 2-m grid."""
import json
import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_domestic as V  # noqa: E402  (load_glb / accessor / node_mat)

GY = 3.0


def load(path, lod):
    j, b, _ = V.load_glb(path)
    mats = j.get('materials', [])
    dbl = [bool(m.get('doubleSided', False)) for m in mats]
    mname = [m.get('name', '') for m in mats]
    blend = [m.get('alphaMode', 'OPAQUE') for m in mats]
    tris, node, mat = [], [], []
    names = []

    def walk(i, M, lv):
        n = j['nodes'][i]; Mi = M @ V.node_mat(n)
        nm = n.get('name', '')
        mm = __import__('re').match(r'^LOD(\d+)(_|$)', nm)
        if mm: lv = int(mm.group(1))
        if 'mesh' in n and (lv == lod or lv is None) and 'EXT_mesh_gpu_instancing' not in n.get('extensions', {}):
            for p in j['meshes'][n['mesh']]['primitives']:
                if p.get('mode', 4) != 4: continue
                P = V.accessor(j, b, p['attributes']['POSITION']).astype(np.float64)
                P = (Mi[:3, :3] @ P.T).T + Mi[:3, 3]
                idx = V.accessor(j, b, p['indices']).ravel().astype(np.int64) if 'indices' in p else np.arange(len(P))
                T = P[idx.reshape(-1, 3)]
                if np.linalg.det(Mi[:3, :3]) < 0: T = T[:, ::-1]
                tris.append(T); names.append(nm)
                node.append(np.full(len(T), len(names) - 1)); mat.append(np.full(len(T), p.get('material', -1)))
        for c in n.get('children', []):
            walk(c, Mi, lv)
    for r in j['scenes'][j.get('scene', 0)]['nodes']:
        walk(r, np.eye(4), None)
    T = np.concatenate(tris); node = np.concatenate(node); mat = np.concatenate(mat)
    return T, node, mat, names, dbl, mname, blend


def tri_normals(T):
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    L = np.linalg.norm(n, axis=1); ok = L > 1e-9
    n[ok] /= L[ok][:, None]
    return n, ok


def slice_plane(T, axis, c):
    """segments of triangles crossing the plane coord[axis] = c: (k, 2, 3) points + triangle index."""
    s = T[:, :, axis] - c
    sg = s > 0
    cnt = sg.sum(1)
    m = (cnt == 1) | (cnt == 2)
    idx = np.nonzero(m)[0]
    if not len(idx): return np.zeros((0, 2, 3)), idx
    Ts, ss = T[idx], s[idx]
    pts = []
    for (i, k) in ((0, 1), (1, 2), (2, 0)):
        a, b = ss[:, i], ss[:, k]
        cr = (a > 0) != (b > 0)
        t = np.where(cr, a / np.where(cr, a - b, 1.0), 0.0)
        p = Ts[:, i] + (Ts[:, k] - Ts[:, i]) * t[:, None]
        pts.append((cr, p))
    P0 = np.where(pts[0][0][:, None], pts[0][1], np.where(pts[1][0][:, None], pts[1][1], pts[2][1]))
    # second crossing: the last edge that crosses
    P1 = np.where(pts[2][0][:, None], pts[2][1], np.where(pts[1][0][:, None], pts[1][1], pts[0][1]))
    return np.stack([P0, P1], 1), idx


def first_hits(seg2, segid, d, sp):
    """2-D orthographic rays along d (unit), spacing sp, from -inf: per ray the first segment (index into seg2)."""
    dp = np.array([-d[1], d[0]])
    u = seg2 @ d; v = seg2 @ dp                      # (k, 2)
    vlo, vhi = v.min(1), v.max(1)
    k0 = np.ceil(vlo / sp).astype(np.int64); k1 = np.floor(vhi / sp).astype(np.int64)
    nk = np.maximum(k1 - k0 + 1, 0)
    if nk.sum() == 0: return None
    rep = np.repeat(np.arange(len(seg2)), nk)
    kk = np.repeat(k0, nk) + (np.arange(nk.sum()) - np.repeat(np.cumsum(nk) - nk, nk))
    vv = kk * sp
    dv = v[rep, 1] - v[rep, 0]
    t = np.where(np.abs(dv) > 1e-12, (vv - v[rep, 0]) / np.where(np.abs(dv) > 1e-12, dv, 1.0), 0.5)
    uu = u[rep, 0] + t * (u[rep, 1] - u[rep, 0])
    o = np.lexsort((uu, kk))
    kk, uu, rep = kk[o], uu[o], rep[o]
    first = np.r_[True, kk[1:] != kk[:-1]]
    return rep[first], uu[first], kk[first]


def load_multi(path, lod):
    parts = path.split('+')
    T, node, mat, names, dbl, mname, blend = load(parts[0], lod)
    own = np.ones(len(T), bool)
    for p in parts[1:]:
        T2, n2, m2, nm2, d2, mn2, b2 = load(p, lod)
        T = np.concatenate([T, T2]); node = np.concatenate([node, n2 + len(names)]); names = names + [os.path.basename(p) + ':' + x for x in nm2]
        mat = np.concatenate([mat, m2 + len(dbl)]); dbl = dbl + d2; mname = mname + mn2; blend = blend + b2
        own = np.concatenate([own, np.zeros(len(T2), bool)])
    return T, node, mat, names, dbl, mname, blend, own


def run(path, lod=0, sp=0.5, H=45.0, naz=16):
    T, node, mat, names, dbl, mname, blend, own = load_multi(path, lod)
    n, okn = tri_normals(T)
    single = np.array([not dbl[m] if m >= 0 else True for m in mat])
    hits = []   # (node, mat, x, y, z, kind)
    # horizontal
    for h in np.arange(0.5, H, 1.0):
        seg, idx = slice_plane(T, 1, GY + h)
        if not len(idx): continue
        seg2 = seg[:, :, [0, 2]]
        for a in range(naz):
            th = 2 * math.pi * a / naz
            d = np.array([math.cos(th), math.sin(th)])
            r = first_hits(seg2, None, d, sp)
            if r is None: continue
            si, uu, kk = r
            ti = idx[si]
            nd = n[ti][:, [0, 2]] @ d
            back = (nd > 0.05) & single[ti] & okn[ti] & own[ti]
            for s_, ti_ in zip(si[back], ti[back]):
                p = seg[s_].mean(0)
                hits.append((int(node[ti_]), int(mat[ti_]), float(p[0]), float(p[1]), float(p[2]), 'h%d' % a))
    # vertical (down): slices x = const, rays along -y in the (z, y) plane: use first_hits with u = -y
    xs = T[:, :, 0]
    for c in np.arange(math.floor(xs.min()), math.ceil(xs.max()), sp):
        seg, idx = slice_plane(T, 0, c + 0.013)
        if not len(idx): continue
        seg2 = np.stack([-seg[:, :, 1], seg[:, :, 2]], 2)   # u = -y (down), v = z
        r = first_hits(seg2, None, np.array([1.0, 0.0]), sp)
        if r is None: continue
        si, uu, kk = r
        ti = idx[si]
        back = (n[ti][:, 1] < -0.05) & single[ti] & okn[ti] & own[ti]
        for s_, ti_ in zip(si[back], ti[back]):
            p = seg[s_].mean(0)
            hits.append((int(node[ti_]), int(mat[ti_]), float(p[0]), float(p[1]), float(p[2]), 'v'))
    per = {}
    for nd_, m_, x, y, z, k in hits:
        key = names[nd_]
        e = per.setdefault(key, dict(n=0, mats={}, cells={}))
        e['n'] += 1
        mn = mname[m_] if m_ >= 0 else ''
        e['mats'][mn] = e['mats'].get(mn, 0) + 1
        ck = '%d,%d,%d' % (round(x / 2) * 2, round((y - GY) / 2) * 2, round(z / 2) * 2)
        e['cells'][ck] = e['cells'].get(ck, 0) + 1
    return dict(glb=path, lod=lod, sp=sp, total=len(hits), nodes=dict(sorted(per.items(), key=lambda kv: -kv[1]['n'])),
                n_tris=int(len(T)), single_sided_tris=int(single.sum()))


if __name__ == '__main__':
    path, out = sys.argv[1], sys.argv[2]
    lod = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    sp = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    r = run(path, lod, sp)
    json.dump(r, open(out, 'w'), indent=1)
    print(path, 'tris', r['n_tris'], 'single', r['single_sided_tris'], 'back-face hits', r['total'])
    for k, v in list(r['nodes'].items())[:25]:
        print('  %-40s %6d  %s' % (k, v['n'], sorted(v['mats'].items(), key=lambda kv: -kv[1])[:3]))
