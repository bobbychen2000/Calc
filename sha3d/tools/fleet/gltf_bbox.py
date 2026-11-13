"""Print node tree, mesh/material counts and the world-space bounding box of a glTF JSON (no buffers needed: uses accessor min/max).
Usage: python3 -I gltf_bbox.py scene.gltf"""
import json, sys
import numpy as np
g = json.load(open(sys.argv[1], encoding='utf-8'))
print('asset', g.get('asset')); print('meshes', len(g.get('meshes', [])), 'materials', len(g.get('materials', [])), 'nodes', len(g.get('nodes', [])),
      'images', len(g.get('images', [])), 'textures', len(g.get('textures', [])))
print('materials:', [m.get('name') for m in g.get('materials', [])][:40])
def mat(n):
    if 'matrix' in n: return np.array(n['matrix']).reshape(4, 4).T
    T = np.eye(4); t = n.get('translation', [0, 0, 0]); r = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
    x, y, z, w = r
    R = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    T[:3, :3] = R @ np.diag(s); T[:3, 3] = t; return T
lo = np.full(3, np.inf); hi = -lo
def walk(i, M, depth):
    global lo, hi
    n = g['nodes'][i]; M = M @ mat(n)
    if depth < 3: print('  ' * depth, n.get('name'), 'mesh' if 'mesh' in n else '', np.round(np.diag(M)[:3], 4))
    if 'mesh' in n:
        for p in g['meshes'][n['mesh']]['primitives']:
            a = g['accessors'][p['attributes']['POSITION']]
            mn, mx = np.array(a['min']), np.array(a['max'])
            for c in range(8):
                v = np.array([mx[k] if (c >> k) & 1 else mn[k] for k in range(3)] + [1.0])
                w = (M @ v)[:3]; lo = np.minimum(lo, w); hi = np.maximum(hi, w)
    for c in n.get('children', []): walk(c, M, depth + 1)
for r in g['scenes'][g.get('scene', 0)]['nodes']: walk(r, np.eye(4), 0)
print('bbox min', np.round(lo, 3), 'max', np.round(hi, 3), 'size', np.round(hi - lo, 3))
