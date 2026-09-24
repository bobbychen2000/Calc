"""Minimal AC3D (.ac) reader producing the same primitive dicts as convert_models.glb_primitives."""
import re, math, os
import numpy as np


def parse_ac(path):
    toks = open(path, 'r', errors='replace').read().splitlines()
    i = 0
    mats = []
    assert toks[0].startswith('AC3D')
    i = 1
    objs = []

    def read_object(i, parentM, depth):
        line = toks[i].split()
        assert line[0] == 'OBJECT', (path, i, toks[i])
        otype = line[1]; i += 1
        o = dict(type=otype, name='', tex=None, rot=np.eye(3), loc=np.zeros(3), verts=None, surfs=[], crease=None, texrep=(1, 1), texoff=(0, 0))
        kids = 0
        while True:
            t = toks[i].strip()
            if not t: i += 1; continue
            parts = t.split()
            k = parts[0]
            if k == 'name': o['name'] = t[5:].strip().strip('"'); i += 1
            elif k == 'data':
                n = int(parts[1]); i += 1
                # data may span lines; consume characters
                got = 0
                while got < n and i < len(toks):
                    got += len(toks[i]) + 1; i += 1
            elif k == 'texture': o['tex'] = t[8:].strip().strip('"'); i += 1
            elif k == 'texrep': o['texrep'] = (float(parts[1]), float(parts[2])); i += 1
            elif k == 'texoff': o['texoff'] = (float(parts[1]), float(parts[2])); i += 1
            elif k == 'rot': o['rot'] = np.array([float(x) for x in parts[1:10]]).reshape(3, 3); i += 1
            elif k == 'loc': o['loc'] = np.array([float(x) for x in parts[1:4]]); i += 1
            elif k == 'crease': o['crease'] = float(parts[1]); i += 1
            elif k in ('url', 'hidden', 'locked', 'subdiv', 'folded'): i += 1
            elif k == 'numvert':
                n = int(parts[1]); i += 1
                v = np.array([[float(x) for x in toks[i + j].split()[:3]] for j in range(n)]); i += n
                o['verts'] = v
            elif k == 'numsurf':
                n = int(parts[1]); i += 1
                for _ in range(n):
                    while not toks[i].strip(): i += 1
                    flags = int(toks[i].split()[1], 16); i += 1
                    mat = 0
                    if toks[i].split()[0] == 'mat': mat = int(toks[i].split()[1]); i += 1
                    nr = int(toks[i].split()[1]); i += 1
                    refs = []
                    for j in range(nr):
                        p = toks[i + j].split(); refs.append((int(p[0]), float(p[1]) if len(p) > 1 else 0.0, float(p[2]) if len(p) > 2 else 0.0))
                    i += nr
                    o['surfs'].append((flags, mat, refs))
            elif k == 'kids':
                kids = int(parts[1]); i += 1
                break
            else:
                i += 1
        # world transform: AC3D: child vertices are in child space; loc/rot relative to parent
        M = parentM @ _mat(o['rot'], o['loc'])
        o['M'] = M; o['depth'] = depth
        objs.append(o)
        for _ in range(kids):
            i = read_object(i, M, depth + 1)
        return i

    while i < len(toks):
        t = toks[i].strip()
        if t.startswith('MATERIAL'):
            m = re.match(r'MATERIAL\s+"?([^"]*)"?\s+rgb\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+).*?trans\s+([\d.eE+-]+)', t)
            if m:
                mats.append(dict(name=m.group(1), rgb=[float(m.group(k)) for k in (2, 3, 4)], trans=float(m.group(5))))
            else:
                mats.append(dict(name='?', rgb=[0.8, 0.8, 0.8], trans=0))
            i += 1
        elif t.startswith('OBJECT'):
            i = read_object(i, np.eye(4), 0)
        else:
            i += 1
    return mats, objs


def _mat(rot, loc):
    M = np.eye(4); M[:3, :3] = rot; M[:3, 3] = loc
    return M


def ac_primitives(path, name_prefix='', offset=(0, 0, 0), skip=None):
    """Return prims (dict pos,nrm,uv,idx,mat,node), materials list, textures by object."""
    mats, objs = parse_ac(path)
    prims = []
    base_dir = os.path.dirname(path)
    for o in objs:
        if o['verts'] is None or not o['surfs']: continue
        if skip and re.search(skip, o['name']): continue
        V = (o['M'][:3, :3] @ o['verts'].T).T + o['M'][:3, 3] + np.array(offset)
        crease = math.radians(o['crease'] if o['crease'] is not None else 61)
        # triangulate, keep per-corner (vertex index, uv)
        tri_v = []; tri_uv = []; tri_mat = []; tri_smooth = []
        for flags, mat, refs in o['surfs']:
            if (flags & 0xF) != 0 or len(refs) < 3: continue  # lines
            for k in range(1, len(refs) - 1):
                a, b, c = refs[0], refs[k], refs[k + 1]
                tri_v.append((a[0], b[0], c[0])); tri_uv.append((a[1:], b[1:], c[1:])); tri_mat.append(mat); tri_smooth.append(bool(flags & 0x10))
        if not tri_v: continue
        tv = np.array(tri_v); tuv = np.array(tri_uv, dtype=np.float64)
        if o['texrep'] != (1, 1) or o['texoff'] != (0, 0):
            tuv = tuv * np.array(o['texrep']) + np.array(o['texoff'])
        P0 = V[tv[:, 0]]; P1 = V[tv[:, 1]]; P2 = V[tv[:, 2]]
        fn = np.cross(P1 - P0, P2 - P0); area = np.linalg.norm(fn, axis=1)
        good = area > 1e-12
        fn[good] /= area[good, None]
        # per-corner normals with crease smoothing
        nv = len(V)
        corner_n = np.repeat(fn[:, None, :], 3, axis=1)
        sm = np.array(tri_smooth)
        # accumulate face normals per vertex (area weighted) for smooth faces
        acc = [[] for _ in range(nv)]
        for f in np.where(sm & good)[0]:
            for c in range(3): acc[tv[f, c]].append(f)
        cosc = math.cos(crease)
        for f in np.where(sm & good)[0]:
            for c in range(3):
                vi = tv[f, c]
                fs = acc[vi]
                if len(fs) <= 1: continue
                fnn = fn[fs]
                w = (fnn @ fn[f]) >= cosc
                n = (fnn[w] * area[fs][w, None]).sum(0)
                l = np.linalg.norm(n)
                if l > 0: corner_n[f, c] = n / l
        # build unique corners per material
        for mi in np.unique(tri_mat):
            sel = np.where((np.array(tri_mat) == mi) & good)[0]
            if not len(sel): continue
            pos = V[tv[sel]].reshape(-1, 3)
            nrm = corner_n[sel].reshape(-1, 3)
            uv = tuv[sel].reshape(-1, 2)
            uv = np.stack([uv[:, 0], 1.0 - uv[:, 1]], 1)  # AC3D v is bottom-up; glTF-style top-down
            idx = np.arange(len(pos))
            prims.append(dict(pos=pos, nrm=nrm, uv=uv, idx=idx, mat=('ac', path, int(mi), o['tex']), node=name_prefix + o['name']))
    return prims, mats
