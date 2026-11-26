"""Minimal glTF 2.0 binary writer for the house model.

World (x right along the street, y into the lot, z up) -> glTF (X = x, Y = z, Z = -y): a proper rotation, so
triangle winding is kept.  One glTF mesh per Part, one primitive per material; float32 positions / UVs,
normals as normalised int16 (KHR_mesh_quantization), uint32 indices.  Materials carry their name and plain
PBR factors; the viewer replaces them by name with its own material library.
"""
from __future__ import annotations

import json
import struct

import numpy as np

FLOAT, SHORT, UINT = 5126, 5122, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


def to_gl(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


class GLB:
    def __init__(self):
        self.bin = bytearray()
        self.views, self.accessors, self.meshes, self.materials, self.nodes = [], [], [], [], []
        self.mat_index = {}

    def _view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {'buffer': 0, 'byteOffset': len(self.bin), 'byteLength': len(data)}
        if target:
            v['target'] = target
        self.bin += data
        self.views.append(v)
        return len(self.views) - 1

    def _acc(self, arr, ctype, typ, target, normalized=False, minmax=False):
        a = {'bufferView': self._view(arr.tobytes(), target), 'componentType': ctype, 'count': int(len(arr)),
             'type': typ}
        if normalized:
            a['normalized'] = True
        if minmax:
            a['min'] = [float(x) for x in arr.min(0)]
            a['max'] = [float(x) for x in arr.max(0)]
        self.accessors.append(a)
        return len(self.accessors) - 1

    def material(self, name, spec):
        if name in self.mat_index:
            return self.mat_index[name]
        c = list(spec.get('color', (0.8, 0.8, 0.8)))
        m = {'name': name, 'pbrMetallicRoughness': {
            'baseColorFactor': [float(c[0]), float(c[1]), float(c[2]), float(spec.get('alpha', 1.0))],
            'metallicFactor': float(spec.get('metallic', 0.0)), 'roughnessFactor': float(spec.get('roughness', 0.7))}}
        if spec.get('emissive'):
            m['emissiveFactor'] = [float(x) for x in spec['emissive']]
        if spec.get('alpha', 1.0) < 1.0:
            m['alphaMode'] = 'BLEND'
        if spec.get('double'):
            m['doubleSided'] = True
        self.materials.append(m)
        self.mat_index[name] = len(self.materials) - 1
        return self.mat_index[name]

    def part(self, part, materials):
        prims = []
        for m in part.geo.meshes():
            V = to_gl(m.V).astype(np.float32)
            N = to_gl(m.N)
            N = np.clip(np.round(N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9) * 32767), -32767,
                        32767).astype(np.int16)
            N = np.concatenate([N, np.zeros((len(N), 1), np.int16)], 1)[:, :3].copy()
            UV = m.UV.astype(np.float32)
            UV = np.stack([UV[:, 0], -UV[:, 1]], -1).astype(np.float32)      # glTF v runs down
            prims.append({
                'attributes': {'POSITION': self._acc(V, FLOAT, 'VEC3', ARRAY_BUFFER, minmax=True),
                               'NORMAL': self._acc(_pad4(N), SHORT, 'VEC3', ARRAY_BUFFER, normalized=True),
                               'TEXCOORD_0': self._acc(UV, FLOAT, 'VEC2', ARRAY_BUFFER)},
                'indices': self._acc(m.F.astype(np.uint32).reshape(-1), UINT, 'SCALAR', ELEMENT_ARRAY_BUFFER),
                'material': self.material(m.mat, materials.get(m.mat, {})), 'mode': 4})
        if not prims:
            return None
        self.meshes.append({'name': part.name, 'primitives': prims})
        node = {'name': part.name, 'mesh': len(self.meshes) - 1}
        ex = dict(part.extras)
        ex['group'] = part.group
        node['extras'] = ex
        self.nodes.append(node)
        return len(self.nodes) - 1

    def write(self, path, extras=None):
        g = {'asset': {'version': '2.0', 'generator': 'house/model/glb.py'},
             'extensionsUsed': ['KHR_mesh_quantization'], 'extensionsRequired': ['KHR_mesh_quantization'],
             'scene': 0, 'scenes': [{'nodes': list(range(len(self.nodes)))}], 'nodes': self.nodes,
             'meshes': self.meshes, 'materials': self.materials, 'accessors': self.accessors,
             'bufferViews': self.views, 'buffers': [{'byteLength': len(self.bin)}]}
        if extras:
            g['asset']['extras'] = extras
        js = json.dumps(g, separators=(',', ':')).encode()
        js += b' ' * ((4 - len(js) % 4) % 4)
        bn = bytes(self.bin) + b'\0' * ((4 - len(self.bin) % 4) % 4)
        g['buffers'][0]['byteLength'] = len(bn)
        js = json.dumps(g, separators=(',', ':')).encode()
        js += b' ' * ((4 - len(js) % 4) % 4)
        with open(path, 'wb') as f:
            f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(bn)))
            f.write(struct.pack('<I4s', len(js), b'JSON'))
            f.write(js)
            f.write(struct.pack('<I4s', len(bn), b'BIN\0'))
            f.write(bn)
        return 12 + 8 + len(js) + 8 + len(bn)


def _pad4(n):
    """int16 VEC3 rows are 6 bytes: accessors must be aligned to the component size, which they are (2)."""
    return n
